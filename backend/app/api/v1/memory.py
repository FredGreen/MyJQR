from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db import get_db
from app.models.template import Category, Template
from app.models.user import User, UserMemory
from app.services import memory as memory_svc
from app.services.moderation import check_text

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/overview")
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """记忆管理面板数据：全局 + 全部分类（含空）+ 已有记忆的模板。"""
    rows = db.query(UserMemory).filter_by(user_id=user.id).all()
    by = {(r.scope, r.scope_id): r.content for r in rows}
    cats = (db.query(Category).filter_by(status=1)
            .order_by(Category.sort_order, Category.id).all())
    tpl_ids = sorted({r.scope_id for r in rows if r.scope == "template"})
    tpl_names = {}
    if tpl_ids:
        tpl_names = {t.id: t.name for t in
                     db.query(Template).filter(Template.id.in_(tpl_ids)).all()}
    return {"code": 0, "data": {
        "global": by.get(("global", 0), ""),
        "categories": [{"category_id": c.id, "name": c.name,
                        "content": by.get(("category", c.id), "")} for c in cats],
        "templates": [{"template_id": tid, "name": tpl_names.get(tid, f"模板#{tid}"),
                       "content": by.get(("template", tid), "")} for tid in tpl_ids],
    }}


class MemoryIn(BaseModel):
    scope: str = Field(pattern="^(global|template|category)$")
    scope_id: int = Field(default=0, ge=0)
    content: str = Field(default="", max_length=1000)


@router.put("")
async def save(body: MemoryIn, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    scope_id = 0 if body.scope == "global" else body.scope_id
    if body.scope != "global" and scope_id <= 0:
        raise HTTPException(422, "scope_id 无效")
    if body.scope == "template":
        t = db.get(Template, scope_id)
        if not t or t.status != 1:
            raise HTTPException(404, "模板不存在或已下架")
    if body.scope == "category":
        c = db.get(Category, scope_id)
        if not c or c.status != 1:
            raise HTTPException(404, "分类不存在")
    if body.content.strip():
        verdict = await check_text(db, body.content, "input", user.id)
        if verdict == "block":
            raise HTTPException(422, "记忆内容包含违规信息")
    memory_svc.upsert(db, user.id, body.scope, scope_id, body.content)
    return {"code": 0, "data": {"scope": body.scope, "scope_id": scope_id}}
