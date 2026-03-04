import subprocess
from typing import Optional
from .base import BaseTool, ToolResult
from safety.guardrails import PathSanitizer


class SearchFilesTool(BaseTool):
    name = "search_files"
    description = "在文件中搜索内容（正则表达式）或按文件名模式搜索（glob）"
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "搜索模式"},
            "path": {"type": "string", "description": "搜索路径，默认当前目录", "default": "."},
            "search_type": {
                "type": "string",
                "enum": ["regex", "glob"],
                "description": "regex: 在文件内容中搜索；glob: 按文件名模式搜索",
                "default": "regex",
            },
            "file_glob": {"type": "string", "description": "仅对 regex 模式有效，过滤文件类型，如 *.py"},
        },
        "required": ["pattern"],
    }

    def __init__(self, sanitizer: PathSanitizer):
        self.sanitizer = sanitizer

    def execute(
        self,
        pattern: str,
        path: str = ".",
        search_type: str = "regex",
        file_glob: Optional[str] = None,
    ) -> ToolResult:
        try:
            safe_path = self.sanitizer.check(path)
            if search_type == "glob":
                import glob as glob_mod
                matches = glob_mod.glob(f"{safe_path}/**/{pattern}", recursive=True)
                return ToolResult(content="\n".join(matches[:100]) or "(no matches)")
            else:
                cmd = ["grep", "-rn", "--include", file_glob or "*", pattern, safe_path]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                output = result.stdout[:8000]  # cap large outputs
                return ToolResult(content=output or "(no matches)")
        except subprocess.TimeoutExpired:
            return ToolResult(content="搜索超时", error=True)
        except Exception as e:
            return ToolResult(content=str(e), error=True)
