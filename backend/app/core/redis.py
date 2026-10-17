"""ARQ/Redis 连接设置（统一入口）。

arq 的 RedisSettings 默认 conn_timeout=1s；Docker Desktop(WSL2) 的 localhost
端口代理握手可能超过它，导致 create_pool/worker 启动超时。统一放宽到 10s。
"""
from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import get_settings

CONN_TIMEOUT = 10


def arq_redis_settings() -> RedisSettings:
    """从 .env 的 REDIS_URL 构造 ARQ 连接设置（不经过这里，.env 的地址对 arq 不生效）。"""
    rs = RedisSettings.from_dsn(get_settings().redis_url)
    rs.conn_timeout = CONN_TIMEOUT
    return rs


async def create_arq_pool():
    return await create_pool(arq_redis_settings())
