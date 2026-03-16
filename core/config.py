from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "BoFire++ API"
    app_version: str = "0.1.0"
    app_description: str = (
        "A REST API built on top of BoFire, providing Bayesian optimization "
        "capabilities over HTTP with Swagger UI documentation."
    )
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
