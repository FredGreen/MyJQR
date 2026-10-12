from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    mysql_dsn: str = "mysql+pymysql://root:myjqr_root@localhost:3306/writing?charset=utf8mb4"
    redis_url: str = "redis://localhost:6379/0"

    # JWT：RS256 密钥对（不存在时自动生成到 keys/ 目录）
    jwt_private_pem: str = "keys/jwt.key"
    jwt_public_pem: str = "keys/jwt.pub"

    # 模型
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    zhipu_api_key: str = ""
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    zhipu_model: str = "glm-4-flash"

    bocha_api_key: str = ""
    aliyun_access_key_id: str = ""
    aliyun_access_key_secret: str = ""

    admin_username: str = "admin"
    admin_password: str = "admin123456"
    signup_gift_joule: int = 100

    @property
    def llm_providers(self) -> dict:
        return {
            "deepseek": {"base_url": self.deepseek_base_url, "api_key": self.deepseek_api_key},
            "zhipu": {"base_url": self.zhipu_base_url, "api_key": self.zhipu_api_key},
        }

    # 路由键 → (provider, model, fallback_provider, fallback_model)
    MODEL_ROUTES: dict = {
        "default_chat": ("deepseek", "deepseek-chat", "zhipu", "glm-4-flash"),
        "think": ("deepseek", "deepseek-reasoner", "zhipu", "glm-4-flash"),
        "title_gen": ("zhipu", "glm-4-flash", "deepseek", "deepseek-chat"),
        "de_ai_rewrite": ("deepseek", "deepseek-chat", "zhipu", "glm-4-flash"),
        "embedding": ("zhipu", "embedding-2", "zhipu", "embedding-2"),
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
