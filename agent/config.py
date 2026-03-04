from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = "your-key"
    openai_base_url: str = "https://api.openai.com/v1"
    model_id: str = "gpt-4o"
    max_iterations: int = 20
    max_context_tokens: int = 100000
    allowed_paths: str = "."
    bash_timeout_secs: int = 30

    @property
    def allowed_path_list(self) -> list[str]:
        import os
        return [os.path.abspath(p) for p in self.allowed_paths.split(":")]


config = Config()
