from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ConversationHistory:
    system_prompt: str
    messages: List[Dict[str, Any]] = field(default_factory=list)

    def add_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, message: Any) -> None:
        """Add assistant message from OpenAI response object."""
        msg: Dict[str, Any] = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ]
        self.messages.append(msg)

    def add_assistant_content(self, content: str) -> None:
        """Add assistant content message (e.g., skill context)."""
        self.messages.append({"role": "assistant", "content": content})

    def add_tool_result(self, tool_call_id: str, name: str, content: str) -> None:
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content,
        })

    def get_messages(self) -> list[dict[str, Any]]:
        return [{"role": "system", "content": self.system_prompt}] + self.messages

    def truncate_if_needed(self, max_tokens: int) -> None:
        """Drop oldest tool result messages when context grows too large."""
        # Simple heuristic: 1 token ≈ 4 chars
        while self._estimate_tokens() > max_tokens and len(self.messages) > 2:
            # Find and remove the oldest tool message
            for i, msg in enumerate(self.messages):
                if msg["role"] == "tool":
                    self.messages.pop(i)
                    break
            else:
                # No tool messages left, remove oldest user/assistant pair
                self.messages.pop(0)

    def _estimate_tokens(self) -> int:
        total_chars = sum(len(str(m)) for m in self.messages)
        return total_chars // 4
