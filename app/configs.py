from pydantic import BaseSettings


class Settings(BaseSettings):
    APP_TITLE: str = "Cool app"
    APP_DESCRIPTION: str = "Still the best."

    KUCOIN_API: str = "https://api.kucoin.com"
    KUCOIN_API_KEY: str
    KUCOIN_API_SECRET: str
    KUCOIN_API_PASSPHRASE: str

    class Config:
        env_file = ".env"
