from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = "your-key"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_no_proxy: bool = False  # 为 True 时绕过系统代理，可修复代理导致的 SSL 错误
    model_id: str = "gpt-4o"
    max_iterations: int = 20
    max_context_tokens: int = 100000
    allowed_paths: str = "."
    bash_timeout_secs: int = 30

    # MCP 相关
    mcp_config_path: str = "mcp_servers.json"
    mcp_enabled: bool = True
    mcp_tool_prefix_on_conflict: bool = True

    @property
    def allowed_path_list(self) -> list[str]:
        import os
        return [os.path.abspath(p) for p in self.allowed_paths.split(":")]


config = Config()
