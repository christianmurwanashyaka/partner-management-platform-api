from typing import List

from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os


env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
env_path = os.path.normpath(env_path)

load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRES_IN: int
    DATABASE_URL: str
    EMAIL: str
    PASSWORD: str
    FIRST_NAME: str
    LAST_NAME: str
    ROLE: str

    # email configuration
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_STARTTLS: bool = True  # Changed from MAIL_TLS
    MAIL_SSL_TLS: bool = False  # Changed from MAIL_SSL
    USE_CREDENTIALS: bool = True

    # CORS configuration
    CORS_ORIGINS: List[str]

    class Config:
        env_file = env_path

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


settings = Settings()
