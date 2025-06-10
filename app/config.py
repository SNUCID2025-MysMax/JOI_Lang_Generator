from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    deeplAPI: str
    apiKey: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()