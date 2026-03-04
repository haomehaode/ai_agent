import os
from .base import BaseTool, ToolResult
from safety.guardrails import PathSanitizer


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "读取本地文件内容，可指定起始行和读取行数"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"},
            "offset": {"type": "integer", "description": "起始行号（1-indexed），默认1", "default": 1},
            "limit": {"type": "integer", "description": "最多读取行数，默认200", "default": 200},
        },
        "required": ["path"],
    }

    def __init__(self, sanitizer: PathSanitizer):
        self.sanitizer = sanitizer

    def execute(self, path: str, offset: int = 1, limit: int = 200) -> ToolResult:
        try:
            safe_path = self.sanitizer.check(path)
            with open(safe_path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            start = max(0, offset - 1)
            selected = lines[start: start + limit]
            numbered = "".join(f"{start + i + 1:4d}\t{line}" for i, line in enumerate(selected))
            return ToolResult(content=numbered or "(empty file)")
        except PermissionError as e:
            return ToolResult(content=str(e), error=True)
        except FileNotFoundError:
            return ToolResult(content=f"File not found: {path}", error=True)
        except Exception as e:
            return ToolResult(content=str(e), error=True)


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "将内容写入本地文件（覆盖已有内容）"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"},
            "content": {"type": "string", "description": "要写入的内容"},
        },
        "required": ["path", "content"],
    }

    def __init__(self, sanitizer: PathSanitizer):
        self.sanitizer = sanitizer

    def execute(self, path: str, content: str) -> ToolResult:
        try:
            safe_path = self.sanitizer.check(path)
            os.makedirs(os.path.dirname(safe_path) or ".", exist_ok=True)
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(content=f"Written {len(content)} chars to {safe_path}")
        except PermissionError as e:
            return ToolResult(content=str(e), error=True)
        except Exception as e:
            return ToolResult(content=str(e), error=True)


class ListDirTool(BaseTool):
    name = "list_dir"
    description = "列出目录内容"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "目录路径，默认当前目录", "default": "."},
        },
        "required": [],
    }

    def __init__(self, sanitizer: PathSanitizer):
        self.sanitizer = sanitizer

    def execute(self, path: str = ".") -> ToolResult:
        try:
            safe_path = self.sanitizer.check(path)
            entries = sorted(os.scandir(safe_path), key=lambda e: (not e.is_dir(), e.name))
            lines = []
            for e in entries[:200]:
                kind = "/" if e.is_dir() else ""
                lines.append(f"{'d' if e.is_dir() else 'f'}  {e.name}{kind}")
            return ToolResult(content="\n".join(lines) or "(empty directory)")
        except PermissionError as e:
            return ToolResult(content=str(e), error=True)
        except Exception as e:
            return ToolResult(content=str(e), error=True)
