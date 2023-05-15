from pydantic import BaseSettings


class Settings(BaseSettings):
    APP_DEBUG: bool = False
    APP_TITLE: str = "[KMD] Kucoin Mazafakers Detector"
    APP_DESCRIPTION: str = "Still the best."
    APP_SECRET_KEY: str = "wowthatissupersecretwow"
    APP_EXPIRE_TOKEN: int = 60 * 60 * 24 * 7 * 2  # two weeks in seconds

    KUCOIN_API: str = "https://api.kucoin.com"
    KUCOIN_API_KEY: str
    KUCOIN_API_SECRET: str
    KUCOIN_API_PASSPHRASE: str

    TELEGRAM_BOT_ENABLED: bool
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_ADMIN_CHAT_ID: int

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    @property
    def POSTGRES_URL(self) -> str:
        return "postgresql+asyncpg://{}:{}@{}:{}/{}".format(
            self.POSTGRES_USER,
            self.POSTGRES_PASSWORD,
            self.POSTGRES_HOST,
            self.POSTGRES_PORT,
            self.POSTGRES_DB,
        )

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: str

    @property
    def REDIS_URL(self) -> str:
        return "redis://{}:{}/{}".format(
            self.REDIS_HOST,
            self.REDIS_PORT,
            self.REDIS_DB,
        )

    class Config:
        env_file = ".env"
