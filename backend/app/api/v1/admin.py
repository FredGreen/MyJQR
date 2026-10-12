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


@router.get("/templates")
def list_templates(cursor: int = 0, page_size: int = 20,
                   admin: AdminUser = Depends(get_current_admin),
                   db: Session = Depends(get_db)):
    q = db.query(Template)
    if cursor:
        q = q.filter(Template.id < cursor)
    rows = q.order_by(Template.id.desc()).limit(page_size).all()
    ids = [t.id for t in rows]
    stats = {s.template_id: s for s in db.query(TemplateStat).filter(
        TemplateStat.template_id.in_(ids))} if ids else {}
    return {"code": 0, "data": {"list": [{
        "id": t.id, "name": t.name, "description": t.description, "status": t.status,
        "joule_price": t.joule_price, "workflow_type": t.workflow_type,
        "use_cnt": stats[t.id].use_cnt if t.id in stats else 0,
        "updated_at": str(t.updated_at)} for t in rows],
        "cursor": rows[-1].id if len(rows) == page_size else 0}}


@router.post("/templates")
def create_template(body: TemplateIn, admin: AdminUser = Depends(get_current_admin),
                    db: Session = Depends(get_db)):
    from app.models.template import TemplateCategoryRelation
    t = Template(**body.model_dump(exclude={"category_ids"}))
    db.add(t)
    db.flush()
    for rank, cid in enumerate(body.category_ids):
        db.add(TemplateCategoryRelation(template_id=t.id, category_id=cid, rank=rank))
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
    for k, v in body.model_dump(exclude={"category_ids"}).items():
        setattr(t, k, v)
    from app.models.template import TemplateCategoryRelation
    db.query(TemplateCategoryRelation).filter_by(template_id=t.id).delete()
    for rank, cid in enumerate(body.category_ids):
        db.add(TemplateCategoryRelation(template_id=t.id, category_id=cid, rank=rank))
    db.add(AuditLog(admin_id=admin.id, action="template.update", target=str(t.id)))
    db.commit()
    return {"code": 0, "data": "ok"}


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
def review_queue(admin: AdminUser = Depends(get_current_admin),
                 db: Session = Depends(get_db)):
    rows = (db.query(ContentModeration).filter_by(verdict="review")
            .order_by(ContentModeration.id.desc()).limit(50).all())
    return {"code": 0, "data": {"list": [{
        "id": m.id, "biz_type": m.biz_type, "biz_id": m.biz_id,
        "created_at": str(m.created_at)} for m in rows]}}


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
def list_users(q: str = "", cursor: int = 0,
               admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    query = db.query(User)
    if q:
        query = query.filter(User.email.contains(q))
    if cursor:
        query = query.filter(User.id < cursor)
    rows = query.order_by(User.id.desc()).limit(20).all()
    return {"code": 0, "data": {"list": [{
        "id": u.id, "email": u.email, "nickname": u.nickname, "status": u.status,
        "created_at": str(u.created_at)} for u in rows],
        "cursor": rows[-1].id if len(rows) == 20 else 0}}


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
