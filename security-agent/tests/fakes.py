"""A stand-in for anthropic.Anthropic that records requests and replays canned responses."""
from types import SimpleNamespace


def _usage(input_tokens=10, output_tokens=10):
    return SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)


def fake_text(text, input_tokens=10, output_tokens=10):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason="end_turn",
                           usage=_usage(input_tokens, output_tokens))


def tool_use(name, args, id="tu_1"):
    return SimpleNamespace(content=[SimpleNamespace(type="tool_use", id=id, name=name, input=args)],
                           stop_reason="tool_use", usage=_usage())


class FakeClaudeClient:
    def __init__(self, responses: list):
        self.responses = list(responses)
        self.calls: list[dict] = []
        self.messages = self

    def create(self, **kwargs):
        # Snapshot the message list: callers keep appending to the same list
        self.calls.append({**kwargs, "messages": list(kwargs.get("messages", []))})
        if not self.responses:
            raise AssertionError("FakeClaudeClient ran out of responses")
        return self.responses.pop(0)
