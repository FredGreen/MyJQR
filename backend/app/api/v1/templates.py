from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db import get_db
from app.models.template import (Bookmark, Category, PromptVersion, Template,
                                 TemplateCategoryRelation, TemplateStat)
from app.models.user import User, UserPref

router = APIRouter(prefix="/template", tags=["template"])


def _tpl_card(t: Template, stat: TemplateStat | None, bookmarked: bool = False) -> dict:
    return {
        "template_id": t.id, "name": t.name, "avatar_url": t.avatar_url,
        "description": t.description, "score": float(t.score or 5.0),
        "joule_price": t.joule_price,
        "enable_web_search": bool(t.enable_web_search), "enable_think": bool(t.enable_think),
        "stats": {"user_cnt": stat.user_cnt if stat else 0,
                  "use_cnt": stat.use_cnt if stat else 0},
        "is_bookmarked": bookmarked,
    }


def _page(q, cursor: int, page_size: int):
    if cursor:
        q = q.filter(Template.id < cursor)
    rows = q.order_by(Template.id.desc()).limit(page_size + 1).all()
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    # rows 是 (Template, TemplateStat) 元组，游标取元组里的 Template.id
    return {"list": rows, "cursor": rows[-1][0].id if has_more else 0, "has_more": has_more}


@router.get("/category/list")
def category_list(user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    cats = db.query(Category).filter_by(status=1).order_by(Category.sort_order).all()
    return {"code": 0, "data": {"list": [
        {"category_id": c.id, "name": c.name, "sort_order": c.sort_order} for c in cats]}}


@router.get("/recommend/list")
def recommend_list(cursor: int = 0, page_size: int = 20,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    page_size = min(page_size, 20)
    q = (db.query(Template, TemplateStat)
         .outerjoin(TemplateStat, TemplateStat.template_id == Template.id)
         .filter(Template.status == 1))
    page = _page(q, cursor, page_size)
    marks = {b.template_id for b in db.query(Bookmark).filter_by(user_id=user.id)}
    return {"code": 0, "data": {
        "list": [_tpl_card(t, s, t.id in marks) for t, s in page["list"]],
        "cursor": page["cursor"], "has_more": page["has_more"]}}


@router.get("/list")
def category_templates(category_id: int, cursor: int = 0, page_size: int = 20,
                       user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    page_size = min(page_size, 20)
    q = (db.query(Template, TemplateStat, TemplateCategoryRelation)
         .outerjoin(TemplateStat, TemplateStat.template_id == Template.id)
         .join(TemplateCategoryRelation,
               TemplateCategoryRelation.template_id == Template.id)
         .filter(Template.status == 1, TemplateCategoryRelation.category_id == category_id))
    if cursor:
        q = q.filter(TemplateCategoryRelation.rank < cursor)
    rows = (q.order_by(TemplateCategoryRelation.rank)
             .limit(page_size + 1).all())
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    marks = {b.template_id for b in db.query(Bookmark).filter_by(user_id=user.id)}
    return {"code": 0, "data": {
        "list": [{**_tpl_card(t, s, t.id in marks), "rank": rel.rank} for t, s, rel in rows],
        "cursor": rows[-1][2].rank if has_more else 0, "has_more": has_more}}


@router.get("/free-creation")
def free_creation(user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """创作页兜底模式：原生大模型自由创作（不存在则自动初始化，幂等）。"""
    from app.seeds import ensure_free_template
    t = ensure_free_template(db)
    return {"code": 0, "data": {
        "template_id": t.id, "name": t.name, "description": t.description,
        "joule_price": t.joule_price, "response_length": t.response_length}}


def _default_template(db: Session) -> Template:
    """从未选过时的默认模板：今日选题，其次任意上线模板。"""
    t = (db.query(Template).filter(Template.status == 1, Template.name == "今日选题")
         .order_by(Template.sort_order, Template.id).first())
    if not t:
        t = (db.query(Template).filter(Template.status == 1)
             .order_by(Template.sort_order, Template.id).first())
    if not t:
        from app.seeds import ensure_free_template
        t = ensure_free_template(db)
    return t


@router.get("/preference")
def get_preference(user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """创作页初始选择：上次选择（仍在线有效）> 默认模板。"""
    pref = db.get(UserPref, user.id)
    last_id = 0
    if pref and pref.last_template_id:
        t = db.get(Template, pref.last_template_id)
        if t and t.status == 1:
            last_id = t.id
    chosen = last_id or _default_template(db).id
    return {"code": 0, "data": {
        "template_id": chosen, "last_template_id": last_id,
        "is_default": last_id == 0}}


class PreferenceIn(BaseModel):
    template_id: int = Field(gt=0)


@router.post("/preference")
def save_preference(body: PreferenceIn, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    t = db.get(Template, body.template_id)
    if not t or t.status != 1:
        raise HTTPException(404, "模板不存在或已下架")
    pref = db.get(UserPref, user.id) or UserPref(user_id=user.id)
    pref.last_template_id = t.id
    db.merge(pref)
    db.commit()
    return {"code": 0, "data": "ok"}


@router.get("/detail")
def template_detail(template_id: int, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    t = db.get(Template, template_id)
    if not t or t.status != 1:
        raise HTTPException(404, "模板不存在或已下架")
    stat = db.get(TemplateStat, t.id)
    cats = (db.query(Category.name)
            .join(TemplateCategoryRelation,
                  TemplateCategoryRelation.category_id == Category.id)
            .filter(TemplateCategoryRelation.template_id == t.id).all())
    # 注意：不返回 system_prompt / user_prompt_template（核心资产不下发）
    return {"code": 0, "data": {
        **_tpl_card(t, stat),
        "categories": [c[0] for c in cats],
        "usage_example": t.usage_example or "",
        "usage_tips": t.usage_tips or "",
        "response_length": t.response_length,
    }}


@router.post("/{template_id}/bookmark")
def add_bookmark(template_id: int, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    if not db.get(Template, template_id):
        raise HTTPException(404, "模板不存在")
    if not db.query(Bookmark).filter_by(user_id=user.id, template_id=template_id).first():
        db.add(Bookmark(user_id=user.id, template_id=template_id))
        stat = db.get(TemplateStat, template_id) or TemplateStat(template_id=template_id)
        stat.bookmark_cnt += 1
        db.merge(stat)
        db.commit()
    return {"code": 0, "data": "ok"}


@router.delete("/{template_id}/bookmark")
def remove_bookmark(template_id: int, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    b = db.query(Bookmark).filter_by(user_id=user.id, template_id=template_id).first()
    if b:
        db.delete(b)
        db.commit()
    return {"code": 0, "data": "ok"}
