"""内容安全：敏感词本地库（必过） + 阿里云文本审核（可选，无 key 放行记日志）。

verdict: pass | review | block。先审后显：block 不落库。
"""
import logging

from sqlalchemy.orm import Session

from app.models.system import SensitiveWord, ContentModeration

log = logging.getLogger(__name__)


def _local_words(db: Session) -> list[tuple[str, int]]:
    return [(w.word, w.level) for w in db.query(SensitiveWord).all()]


async def check_text(db: Session, text: str, biz_type: str, biz_id: int) -> str:
    verdict = "pass"
    for word, level in _local_words(db):
        if word and word in text:
            verdict = "block" if level == 1 else ("review" if verdict == "pass" else verdict)

    aliyun_verdict = await _aliyun_text(text)
    if aliyun_verdict == "block" or (aliyun_verdict == "review" and verdict == "pass"):
        verdict = aliyun_verdict

    db.add(ContentModeration(biz_type=biz_type, biz_id=biz_id,
                             provider="aliyun" if aliyun_verdict else "local",
                             verdict=verdict,
                             raw={"aliyun": aliyun_verdict, "local": verdict != "pass"}))
    db.commit()
    return verdict


async def _aliyun_text(text: str) -> str | None:
    """M3 接阿里云内容安全 v2；骨架期未配置则跳过。"""
    from app.core.config import get_settings
    s = get_settings()
    if not (s.aliyun_access_key_id and s.aliyun_access_key_secret):
        return None
    # TODO(M3): alibabacloud-green20220302 SDK 文本检测，此处留接口
    return None
