from pydantic_settings import BaseSettings, SettingsConfigDict

# API 호출을 위한 키를 포함하는 설정 클래스
class Settings(BaseSettings):
    deeplAPI: str
    apiKey: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()