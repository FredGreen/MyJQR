"""三层记忆：全局偏好 / 分类通用 / 模板专属（个性化 Skill）。

隔离铁律：记忆块只含偏好文本，永不包含历史文章正文；
新创作不加载任何历史文章上下文，每次创作都是独立新篇章。
"""
from sqlalchemy.orm import Session

from app.models.template import Category, Template, TemplateCategoryRelation
from app.models.user import UserMemory

MAX_TIER_CHARS = 1000   # 每层上限（API 侧同样校验）
MAX_BLOCK_CHARS = 2000  # 注入 system prompt 的整块上限，保护 token 预算


def _get(db: Session, user_id: int, scope: str, scope_id: int) -> UserMemory | None:
    return db.query(UserMemory).filter_by(
        user_id=user_id, scope=scope, scope_id=scope_id).first()


def upsert(db: Session, user_id: int, scope: str, scope_id: int, content: str) -> str:
    """整层覆写保存；content 为空即删除该层。返回保存后的内容。"""
    row = _get(db, user_id, scope, scope_id)
    content = (content or "").strip()[:MAX_TIER_CHARS]
    if not content:
        if row:
            db.delete(row)
            db.commit()
        return ""
    if row:
        row.content = content
    else:
        row = UserMemory(user_id=user_id, scope=scope, scope_id=scope_id, content=content)
        db.add(row)
    db.commit()
    return row.content


def append(db: Session, user_id: int, scope: str, scope_id: int, text: str) -> bool:
    """追问「记住要求」：把一条指令追加进指定层（已包含则跳过，超长截断）。"""
    text = (text or "").strip()
    if not text:
        return False
    row = _get(db, user_id, scope, scope_id)
    if row and text in row.content:
        return False
    old = row.content if row else ""
    merged = (old + ("\n" if old else "") + text)[:MAX_TIER_CHARS]
    upsert(db, user_id, scope, scope_id, merged)
    return True


def build_memory_block(db: Session, user_id: int, template: Template) -> str:
    """拼装注入 system prompt 末尾的记忆块；用户无任何记忆时返回 ''。"""
    lines: list[str] = []
    g = _get(db, user_id, "global", 0)
    if g and g.content:
        lines.append(f"- 全局写作偏好：{g.content}")
    cat_ids = [r.category_id for r in db.query(TemplateCategoryRelation)
               .filter_by(template_id=template.id).all()]
    if cat_ids:
        cats = (db.query(Category)
                .filter(Category.id.in_(cat_ids), Category.status == 1)
                .order_by(Category.id).all())
        for c in cats:
            m = _get(db, user_id, "category", c.id)
            if m and m.content:
                lines.append(f"- 分类偏好（{c.name}）：{m.content}")
    t = _get(db, user_id, "template", template.id)
    if t and t.content:
        lines.append(f"- 本模板专属要求：{t.content}")
    if not lines:
        return ""
    block = "\n".join(lines)[:MAX_BLOCK_CHARS]
    return ("\n\n【作者个人风格档案（长期记忆；在不违背平台安全、事实性与输出格式要求"
            "的前提下优先满足）】\n" + block)
