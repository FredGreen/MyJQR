import secrets
import string
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.core.security import hash_password, issue_tokens, verify_password
from app.db import get_db
from app.models.joule import JouleTransaction, RedeemCode
from app.models.system import AuditLog, ContentModeration
from app.models.template import Category, PromptVersion, Template, TemplateStat
from app.models.user import AdminUser, User
from app.models.work import Work
from app.services import joule

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------- 分类（后台用，admin token 域） ----------
@router.get("/categories")
def admin_categories(admin: AdminUser = Depends(get_current_admin),
                     db: Session = Depends(get_db)):
    cats = db.query(Category).order_by(Category.sort_order).all()
    return {"code": 0, "data": {"list": [
        {"category_id": c.id, "name": c.name} for c in cats]}}


# ---------- 登录 ----------
class AdminLoginIn(BaseModel):
    username: str
    password: str


@router.post("/login")
def admin_login(body: AdminLoginIn, db: Session = Depends(get_db)):
    admin = db.query(AdminUser).filter_by(username=body.username).first()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    return {"code": 0, "data": issue_tokens(str(admin.id), kind="admin")}


# ---------- 看板 ----------
@router.get("/dashboard/overview")
def overview(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    return {"code": 0, "data": {
        "users": db.query(func.count(User.id)).scalar(),
        "works_total": db.query(func.count(Work.id)).scalar(),
        "works_done": db.query(func.count(Work.id)).filter(Work.status == "done").scalar(),
        "works_failed": db.query(func.count(Work.id)).filter(Work.status == "failed").scalar(),
        "templates_online": db.query(func.count(Template.id)).filter(Template.status == 1).scalar(),
        "joule_sold": db.query(func.coalesce(func.sum(JouleTransaction.amount), 0))
            .filter(JouleTransaction.biz_type == "redeem").scalar(),
        "pending_review": db.query(func.count(ContentModeration.id))
            .filter(ContentModeration.verdict == "review").scalar(),
    }}


# ---------- 模板管理 ----------
class TemplateIn(BaseModel):
    name: str
    description: str = ""
    category_ids: list[int] = []
    workflow_type: str = "single"
    model_route: str = "default_chat"
    enable_web_search: bool = True
    enable_think: bool = True
    temperature: float = 0.95
    response_length: int = 2
    joule_price: int = 1000
    usage_example: str = ""
    usage_tips: str = ""
    status: int = 0
    # 提示词（可选）：留空不动；与当前发布版不同则自动生成新版本并发布（同 xlsx 导入语义）
    system_prompt: str = ""
    user_prompt_template: str = ""


DEFAULT_UPT = "主题：{topic}\n素材：{material}\n字数：约{length}字"


def _upsert_prompt(db: Session, template_id: int, system_prompt: str,
                   user_prompt_template: str, admin_id: int):
    """新建/更新模板时同步提示词：内容相同跳过，不同则新版本并发布。"""
    if not system_prompt or len(system_prompt) < 10:
        return
    new_upt = user_prompt_template or DEFAULT_UPT
    cur = (db.query(PromptVersion).filter_by(template_id=template_id, published=1)
           .order_by(PromptVersion.version.desc()).first())
    if cur and cur.system_prompt == system_prompt and \
            (cur.user_prompt_template or DEFAULT_UPT) == new_upt:
        return
    latest = (db.query(PromptVersion).filter_by(template_id=template_id)
              .order_by(PromptVersion.version.desc()).first())
    pv = PromptVersion(template_id=template_id, version=(latest.version + 1) if latest else 1,
                       system_prompt=system_prompt, user_prompt_template=new_upt)
    db.add(pv)
    db.flush()
    db.query(PromptVersion).filter_by(template_id=template_id).update({"published": 0})
    pv.published = 1
    db.add(AuditLog(admin_id=admin_id, action="prompt.add",
                    target=f"{template_id}:v{pv.version}"))


@router.get("/templates")
def list_templates(page: int = 1, page_size: int = 20,
                   admin: AdminUser = Depends(get_current_admin),
                   db: Session = Depends(get_db)):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    q = db.query(Template)
    total = q.count()
    rows = (q.order_by(Template.id.desc())
             .offset((page - 1) * page_size).limit(page_size).all())
    ids = [t.id for t in rows]
    stats = {s.template_id: s for s in db.query(TemplateStat).filter(
        TemplateStat.template_id.in_(ids))} if ids else {}
    return {"code": 0, "data": {
        "list": [{
            "id": t.id, "name": t.name, "description": t.description, "status": t.status,
            "joule_price": t.joule_price, "workflow_type": t.workflow_type,
            "use_cnt": stats[t.id].use_cnt if t.id in stats else 0,
            "updated_at": str(t.updated_at)} for t in rows],
        "total": total, "page": page, "page_size": page_size}}


@router.post("/templates")
def create_template(body: TemplateIn, admin: AdminUser = Depends(get_current_admin),
                    db: Session = Depends(get_db)):
    from app.models.template import TemplateCategoryRelation
    fields = body.model_dump(exclude={"category_ids", "system_prompt", "user_prompt_template"})
    t = Template(**fields)
    db.add(t)
    db.flush()
    for rank, cid in enumerate(body.category_ids):
        db.add(TemplateCategoryRelation(template_id=t.id, category_id=cid, rank=rank))
    _upsert_prompt(db, t.id, body.system_prompt, body.user_prompt_template, admin.id)
    db.commit()
    db.add(AuditLog(admin_id=admin.id, action="template.create", target=str(t.id)))
    db.commit()
    return {"code": 0, "data": {"id": t.id}}


@router.put("/templates/{template_id}")
def update_template(template_id: int, body: TemplateIn,
                    admin: AdminUser = Depends(get_current_admin),
                    db: Session = Depends(get_db)):
    t = db.get(Template, template_id)
    if not t:
        raise HTTPException(404, "not found")
    fields = body.model_dump(exclude={"category_ids", "system_prompt", "user_prompt_template"})
    for k, v in fields.items():
        setattr(t, k, v)
    from app.models.template import TemplateCategoryRelation
    db.query(TemplateCategoryRelation).filter_by(template_id=t.id).delete()
    for rank, cid in enumerate(body.category_ids):
        db.add(TemplateCategoryRelation(template_id=t.id, category_id=cid, rank=rank))
    _upsert_prompt(db, t.id, body.system_prompt, body.user_prompt_template, admin.id)
    db.add(AuditLog(admin_id=admin.id, action="template.update", target=str(t.id)))
    db.commit()
    return {"code": 0, "data": "ok"}


@router.get("/templates/{template_id}")
def template_detail(template_id: int, admin: AdminUser = Depends(get_current_admin),
                    db: Session = Depends(get_db)):
    """后台模板详情：完整字段 + 分类 + 统计 + 当前提示词（运营可看，与用户端不同）。"""
    from app.models.template import TemplateCategoryRelation
    t = db.get(Template, template_id)
    if not t:
        raise HTTPException(404, "not found")
    cat_ids = [r.category_id for r in db.query(TemplateCategoryRelation)
               .filter_by(template_id=t.id).order_by(TemplateCategoryRelation.rank)]
    stat = db.get(TemplateStat, t.id)
    pv = (db.query(PromptVersion).filter_by(template_id=t.id, published=1)
          .order_by(PromptVersion.version.desc()).first())
    versions = (db.query(PromptVersion).filter_by(template_id=t.id)
                .order_by(PromptVersion.version.desc()).limit(20).all())
    return {"code": 0, "data": {
        "id": t.id, "name": t.name, "description": t.description, "status": t.status,
        "joule_price": t.joule_price, "workflow_type": t.workflow_type,
        "model_route": t.model_route, "temperature": t.temperature,
        "response_length": t.response_length,
        "enable_web_search": bool(t.enable_web_search), "enable_think": bool(t.enable_think),
        "usage_example": t.usage_example, "usage_tips": t.usage_tips,
        "category_ids": cat_ids, "updated_at": str(t.updated_at),
        "stats": {"use_cnt": stat.use_cnt if stat else 0,
                  "user_cnt": stat.user_cnt if stat else 0},
        "prompt": ({"version": pv.version, "system_prompt": pv.system_prompt,
                    "user_prompt_template": pv.user_prompt_template} if pv else None),
        "prompt_versions": [{"version": v.version, "published": v.published,
                             "created_at": str(v.created_at)} for v in versions],
    }}


# ---------- 作品（后台全量视角，可按用户/模板筛选） ----------
@router.get("/works")
def admin_works(user_id: int = 0, template_id: int = 0, status: str = "",
                page: int = 1, page_size: int = 20,
                admin: AdminUser = Depends(get_current_admin),
                db: Session = Depends(get_db)):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    q = (db.query(Work, User, Template)
         .outerjoin(User, User.id == Work.user_id)
         .outerjoin(Template, Template.id == Work.template_id))
    if user_id:
        q = q.filter(Work.user_id == user_id)
    if template_id:
        q = q.filter(Work.template_id == template_id)
    if status:
        q = q.filter(Work.status == status)
    total = q.count()
    rows = (q.order_by(Work.id.desc())
             .offset((page - 1) * page_size).limit(page_size).all())
    return {"code": 0, "data": {
        "list": [{"work_id": w.id, "user_id": w.user_id,
                  "user_email": u.email if u else "", "user_nickname": u.nickname if u else "",
                  "template_id": w.template_id, "template_name": t.name if t else "",
                  "title": w.title, "topic": w.topic[:80], "status": w.status,
                  "word_cnt": w.word_cnt, "joule_cost": w.joule_cost,
                  "model_used": w.model_used, "created_at": str(w.created_at)}
                 for w, u, t in rows],
        "total": total, "page": page, "page_size": page_size}}


@router.get("/works/{work_id}")
def admin_work_detail(work_id: int, admin: AdminUser = Depends(get_current_admin),
                      db: Session = Depends(get_db)):
    w = db.get(Work, work_id)
    if not w:
        raise HTTPException(404, "not found")
    u = db.get(User, w.user_id)
    t = db.get(Template, w.template_id)
    from app.models.work import AiRateCheck, SearchReference
    refs = db.query(SearchReference).filter_by(work_id=work_id).order_by(
        SearchReference.idx).all()
    check = (db.query(AiRateCheck).filter_by(work_id=work_id)
             .order_by(AiRateCheck.id.desc()).first())
    return {"code": 0, "data": {
        "work_id": w.id, "user_id": w.user_id,
        "user_email": u.email if u else "", "user_nickname": u.nickname if u else "",
        "template_name": t.name if t else "",
        "title": w.title, "topic": w.topic, "status": w.status,
        "content_md": w.content_md or "", "word_cnt": w.word_cnt,
        "joule_cost": w.joule_cost, "model_used": w.model_used,
        "tokens_in": w.tokens_in, "tokens_out": w.tokens_out,
        "created_at": str(w.created_at),
        "references": [{"idx": r.idx, "title": r.title, "url": r.url,
                        "site_name": r.site_name} for r in refs],
        "report": ({"ai_rate": check.ai_rate, "level": check.level} if check else None),
    }}


# ---------- 提示词版本 ----------
class PromptIn(BaseModel):
    system_prompt: str = Field(min_length=10)
    user_prompt_template: str = "主题：{topic}\n素材：{material}\n字数：约{length}字"
    ai_word_blacklist: list[str] = []


@router.post("/templates/{template_id}/prompt-versions")
def add_prompt(template_id: int, body: PromptIn,
               admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    latest = (db.query(PromptVersion).filter_by(template_id=template_id)
              .order_by(PromptVersion.version.desc()).first())
    pv = PromptVersion(template_id=template_id, version=(latest.version + 1) if latest else 1,
                       system_prompt=body.system_prompt,
                       user_prompt_template=body.user_prompt_template,
                       ai_word_blacklist=body.ai_word_blacklist)
    db.add(pv)
    db.commit()
    db.add(AuditLog(admin_id=admin.id, action="prompt.add",
                    target=f"{template_id}:v{pv.version}"))
    db.commit()
    return {"code": 0, "data": {"version": pv.version}}


@router.post("/prompt-versions/{pv_id}/publish")
def publish_prompt(pv_id: int, admin: AdminUser = Depends(get_current_admin),
                   db: Session = Depends(get_db)):
    pv = db.get(PromptVersion, pv_id)
    if not pv:
        raise HTTPException(404, "not found")
    db.query(PromptVersion).filter_by(template_id=pv.template_id).update({"published": 0})
    pv.published = 1
    db.add(AuditLog(admin_id=admin.id, action="prompt.publish", target=str(pv_id)))
    db.commit()
    return {"code": 0, "data": "ok"}


# ---------- 兑换码 ----------
class RedeemBatchIn(BaseModel):
    amount: int = Field(gt=0, le=100000)
    count: int = Field(gt=0, le=500)


@router.post("/redeem-codes/batch")
def gen_redeem_codes(body: RedeemBatchIn,
                     admin: AdminUser = Depends(get_current_admin),
                     db: Session = Depends(get_db)):
    alphabet = string.ascii_uppercase + string.digits
    batch_no = datetime.now().strftime("%Y%m%d%H%M%S")
    codes = []
    for _ in range(body.count):
        code = "J" + "".join(secrets.choice(alphabet) for _ in range(11))
        codes.append(code)
        db.add(RedeemCode(code=code, amount=body.amount, batch_no=batch_no))
    db.add(AuditLog(admin_id=admin.id, action="redeem.batch",
                    target=batch_no, diff={"amount": body.amount, "count": body.count}))
    db.commit()
    return {"code": 0, "data": {"batch_no": batch_no, "codes": codes}}


# ---------- 审核 ----------
@router.get("/review/queue")
def review_queue(page: int = 1, page_size: int = 20,
                 admin: AdminUser = Depends(get_current_admin),
                 db: Session = Depends(get_db)):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    q = db.query(ContentModeration).filter_by(verdict="review")
    total = q.count()
    rows = (q.order_by(ContentModeration.id.desc())
             .offset((page - 1) * page_size).limit(page_size).all())
    return {"code": 0, "data": {
        "list": [{
            "id": m.id, "biz_type": m.biz_type, "biz_id": m.biz_id,
            "created_at": str(m.created_at)} for m in rows],
        "total": total, "page": page, "page_size": page_size}}


@router.post("/review/{mid}")
def review_decide(mid: int, verdict: str = "pass",
                  admin: AdminUser = Depends(get_current_admin),
                  db: Session = Depends(get_db)):
    m = db.get(ContentModeration, mid)
    if not m:
        raise HTTPException(404, "not found")
    m.verdict, m.reviewer_id, m.reviewed_at = verdict, admin.id, datetime.now()
    if verdict == "block" and m.biz_type == "work":
        w = db.get(Work, m.biz_id)
        if w:
            w.status = "banned"
    db.commit()
    return {"code": 0, "data": "ok"}


# ---------- 用户 ----------
@router.get("/users")
def list_users(q: str = "", page: int = 1, page_size: int = 20,
               admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app.models.joule import JouleAccount
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    query = db.query(User)
    if q:
        query = query.filter(User.email.contains(q))
    total = query.count()
    rows = (query.order_by(User.id.desc())
                 .offset((page - 1) * page_size).limit(page_size).all())
    ids = [u.id for u in rows]
    accs = {a.user_id: a for a in db.query(JouleAccount).filter(
        JouleAccount.user_id.in_(ids))} if ids else {}
    work_cnts = dict(db.query(Work.user_id, func.count(Work.id))
                     .filter(Work.user_id.in_(ids)).group_by(Work.user_id)) if ids else {}
    return {"code": 0, "data": {"list": [{
        "id": u.id, "email": u.email, "nickname": u.nickname, "status": u.status,
        "balance": accs[u.id].balance if u.id in accs else 0,
        "frozen": accs[u.id].frozen if u.id in accs else 0,
        "work_cnt": work_cnts.get(u.id, 0),
        "created_at": str(u.created_at)} for u in rows],
        "total": total, "page": page, "page_size": page_size}}


class AdjustIn(BaseModel):
    amount: int
    remark: str = ""


@router.post("/users/{user_id}/joule/adjust")
def adjust_joule(user_id: int, body: AdjustIn,
                 admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    joule.credit(db, user_id, body.amount, "adjust",
                 idem_key=f"adjust:{admin.id}:{datetime.now().isoformat()}",
                 remark=body.remark or "后台调账")
    db.add(AuditLog(admin_id=admin.id, action="joule.adjust", target=str(user_id),
                    diff={"amount": body.amount}))
    db.commit()
    return {"code": 0, "data": "ok"}
