"""Claude as the security analyst: it reasons over stored facts, never collects them."""
import logging
from datetime import date

import config
from budget import Budget, Job

logger = logging.getLogger("analyst")


class Claude:
    """Budget-gated access to the Messages API. Returns None instead of calling when it can't spend."""

    def __init__(self, client, budget: Budget, *, today=date.today):
        self.client, self.budget, self.today = client, budget, today

    @classmethod
    def from_config(cls, conn) -> "Claude":
        client = None
        if config.ANTHROPIC_API_KEY:
            import anthropic
            client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        return cls(client, Budget(conn))

    @property
    def available(self) -> bool:
        return self.client is not None

    def ask(self, job: Job, *, model: str, system: str, messages: list, tools=None, max_tokens: int = 1024):
        if self.client is None or not self.budget.can_spend(job, self.today()):
            return None
        kwargs = dict(model=model, max_tokens=max_tokens, system=system, messages=messages)
        if tools:
            kwargs["tools"] = tools
        try:
            response = self.client.messages.create(**kwargs)
        except Exception as exc:
            logger.warning("Claude call failed (%s): %s", job, type(exc).__name__)
            return None
        self.budget.record(job, model, response.usage.input_tokens, response.usage.output_tokens, self.today())
        return response


def text_of(response) -> str:
    return "".join(b.text for b in response.content if getattr(b, "type", "") == "text").strip()
