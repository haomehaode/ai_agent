import os
import re


BASH_DENYLIST = [
    (r"rm\s+-rf\s+/", "禁止删除根目录"),
    (r"dd\s+if=", "禁止 dd 命令"),
    (r"mkfs", "禁止格式化磁盘"),
    (r":\(\)\s*\{.*\|.*:.*\}", "禁止 fork bomb"),
    (r"curl\s+.*\|\s*(bash|sh)", "禁止 curl pipe shell"),
    (r"wget\s+.*\|\s*(bash|sh)", "禁止 wget pipe shell"),
    (r">\s*/dev/sda", "禁止写入块设备"),
]


class PathSanitizer:
    def __init__(self, allowed_paths: list[str]):
        self.allowed_paths = [os.path.abspath(p) for p in allowed_paths]

    def check(self, path: str) -> str:
        abs_path = os.path.abspath(path)
        for allowed in self.allowed_paths:
            if abs_path.startswith(allowed):
                return abs_path
        raise PermissionError(
            f"路径 '{abs_path}' 不在允许范围内 {self.allowed_paths}"
        )


class CommandFilter:
    def check(self, command: str) -> tuple[bool, str]:
        for pattern, reason in BASH_DENYLIST:
            if re.search(pattern, command, re.IGNORECASE):
                return True, reason
        return False, ""
