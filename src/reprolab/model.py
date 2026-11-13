"""Metered DeepSeek adapter implementing mini-swe-agent's Model protocol."""

import json
import math
import time
from types import SimpleNamespace

from openai import OpenAI

from reprolab.core import LabError, redact
from reprolab.store import Store


class ToolModel:
    def __init__(self, store: Store, run_id: str, tools: list, client=None):
        self.store, self.run_id, self.tools = store, run_id, tools
        self.config = SimpleNamespace(model_name=store.settings.model)
        self.client = client

    def query(self, messages: list, **kwargs):
        payload = self.prepare(messages)
        size = len(json.dumps({"messages": payload, "tools": self.tools}, ensure_ascii=False).encode())
        if size > 64000:
            raise LabError("context_limit", "模型输入超过64 KB上限，任务已保存")
        reservation = math.ceil((size * 2 + 8192) * 2.4 + self.store.settings.max_output * 9.6)
        if self.client is None:
            self.client = OpenAI(
                api_key=self.store.settings.api_key(),
                base_url=self.store.settings.base_url,
                max_retries=0,
                timeout=60,
            )
        ticket = self.store.reserve(self.run_id, reservation)
        started = time.monotonic()
        try:
            response = self.client.chat.completions.create(
                model=self.store.settings.model,
                messages=payload,
                tools=self.tools,
                parallel_tool_calls=False,
                max_tokens=self.store.settings.max_output,
                temperature=0,
                extra_body={"thinking": {"type": "disabled"}},
            )
        except BaseException as exc:
            self.store.settle(ticket, None)
            self.store.event(self.run_id, "model_error", {"type": type(exc).__name__, "ticket": ticket})
            if isinstance(exc, KeyboardInterrupt):
                raise
            raise LabError(
                "unknown_usage", "模型请求未完成，保留最高预留费用，已结束当前任务付费执行"
            ) from exc
        usage = response.usage
        if usage is None or usage.prompt_tokens is None or usage.completion_tokens is None:
            self.store.settle(ticket, None)
            raise LabError("unknown_usage", "模型未返回完整用量，预留费用持续计入预算")
        self.store.settle(
            ticket, {"input_tokens": usage.prompt_tokens, "output_tokens": usage.completion_tokens}
        )
        message = response.choices[0].message.model_dump(exclude_none=True)
        # Only public assistant content and tool arguments are retained, not provider reasoning fields.
        message = {key: value for key, value in message.items() if key in {"role", "content", "tool_calls"}}
        actions = []
        for call in message.get("tool_calls", []):
            try:
                arguments = json.loads(call["function"]["arguments"])
            except ValueError:
                arguments = {"_invalid_json": True}
            actions.append({"id": call["id"], "name": call["function"]["name"], "arguments": arguments})
        message["extra"] = {
            "actions": actions,
            "cost": (usage.prompt_tokens * 0.30 + usage.completion_tokens * 1.20) / 1e6,
            "ticket": ticket,
        }
        self.store.event(
            self.run_id,
            "model_call",
            {
                "ticket": ticket,
                "seconds": round(time.monotonic() - started, 3),
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens,
            },
        )
        return message

    def prepare(self, messages):
        clean = [
            {
                key: value
                for key, value in message.items()
                if key in {"role", "content", "tool_calls", "tool_call_id"}
            }
            for message in messages
            if message.get("role") != "exit"
        ]
        # Keep complete assistant/tool groups while reducing the working context deterministically.
        first_tool = next(
            (i for i, message in enumerate(clean) if message.get("role") == "assistant"), len(clean)
        )
        prefix, history = clean[:first_tool], clean[first_tool:]
        groups = []
        for message in history:
            if message["role"] == "assistant" or not groups:
                groups.append([])
            groups[-1].append(message)
        state = {
            "plan": self.store.get(self.run_id, "state", "plan", []),
            "hypotheses": self.store.objects(self.run_id, "hypotheses"),
            "skills": self.store.objects(self.run_id, "active_skills"),
            "artifacts": [
                item
                for item in self.store.objects(self.run_id, "artifacts")
                if not item["category"].startswith("private_")
            ][-15:],
            "last_experiment": self.store.get(self.run_id, "state", "last_experiment"),
            "remaining_calls": self.store.settings.max_calls
            - self.store.statistics(self.run_id)["model_calls"],
        }
        # Activated instructions remain available after trimming, within the 64 KB total cap.
        from reprolab.skills import Skills

        skills = Skills(self.store, self.run_id)
        state["skill_instructions"] = {
            item["name"]: skills.resource(item["name"], "SKILL.md") for item in state["skills"]
        }
        if self.store.run(self.run_id)["config"].get("reflection", True) is False:
            state.pop("hypotheses")
        context = {
            "role": "user",
            "content": "任务持久化状态，资料内容作为待分析数据\n" + json.dumps(state, ensure_ascii=False),
        }
        while (
            groups
            and len(
                json.dumps(
                    [*prefix, context, *[m for group in groups for m in group]], ensure_ascii=False
                ).encode()
            )
            > 40000
        ):
            groups.pop(0)
            self.store.event(self.run_id, "context_trim", {"remaining_groups": len(groups)})
        return [*prefix, context, *[message for group in groups for message in group]]

    def format_message(self, **kwargs):
        return kwargs

    def format_observation_messages(self, message, outputs, template_vars=None):
        return [
            {
                "role": "tool",
                "tool_call_id": action["id"],
                "content": redact(json.dumps(output, ensure_ascii=False)),
            }
            for action, output in zip(message["extra"]["actions"], outputs, strict=True)
        ]

    def get_template_vars(self, **kwargs):
        return {"model": self.store.settings.model}

    def serialize(self):
        return {
            "info": {
                "config": {
                    "model": {
                        "model_name": self.store.settings.model,
                        "base_url": self.store.settings.base_url,
                    }
                }
            }
        }
