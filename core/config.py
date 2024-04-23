from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os


env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
env_path = os.path.normpath(env_path)

print(f"Loading .env from: {env_path}")
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

    class Config:
        env_file = env_path

    def __init__(self, **kwargs):
        # TODO: REMOVE LOGS
        super().__init__(**kwargs)
        print(f'SECRET KEY is {self.SECRET_KEY}')
        print(f'ALGORITHM IS {self.ALGORITHM}')
        print(f'ACCESS TOKEN EXPIRES IN {self.ACCESS_TOKEN_EXPIRES_IN}')


settings = Settings()
