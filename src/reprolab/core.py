"""Configuration, bounded artifacts and privacy-safe records."""

import hashlib
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class LabError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def now() -> str:
    return datetime.now(UTC).isoformat()


def digest(value: bytes | str) -> str:
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def redact(value: str) -> str:
    for name, secret in os.environ.items():
        if re.search(r"KEY|TOKEN|SECRET|PASSWORD", name) and len(secret) >= 12:
            value = value.replace(secret, "[REDACTED]")
    return re.sub(r"\b(?:sk-[\w-]{20,}|gh[pousr]_[\w]{25,}|github_pat_[\w]{30,})", "[REDACTED]", value)


def atomic_write(path: Path, data: str | bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data.encode() if isinstance(data, str) else data)
    temporary.chmod(0o600)
    temporary.replace(path)


def bounded_path(root: Path, relative: str) -> Path:
    if not relative or "\\" in relative or "\x00" in relative:
        raise LabError("invalid_path", "路径应为非空的相对 POSIX 路径")
    path = Path(relative)
    if path.is_absolute() or any(part in ("", ".", "..") for part in relative.split("/")):
        raise LabError("invalid_path", "路径超出当前工作区")
    candidate = root / path
    for part in [candidate, *candidate.parents]:
        if part == root.parent:
            break
        if part.is_symlink():
            raise LabError("invalid_path", "路径包含符号链接")
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise LabError("invalid_path", "路径超出当前工作区")
    return candidate


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Settings(Record):
    home: Path = Field(default_factory=lambda: Path(os.getenv("REPROLAB_HOME", ".reprolab")).resolve())
    model: Literal["deepseek-flash"] = "deepseek-flash"
    base_url: Literal["https://api.deepseek.com"] = "https://api.deepseek.com"
    image: str = "reprolab-python:0.1.0"
    max_calls: int = Field(default=25, ge=1, le=25)
    max_experiments: int = Field(default=8, ge=1, le=8)
    max_seconds: int = Field(default=600, ge=1, le=600)
    test_seconds: int = Field(default=60, ge=1, le=60)
    max_output: int = Field(default=4096, ge=256, le=4096)
    budget_micro: int = Field(default=20_000_000, ge=1, le=20_000_000)

    def api_key(self) -> str:
        key = (
            os.getenv("DEEPSEEK_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("OPENAI_API_KEY")
        )
        if not key:
            raise LabError("configuration", "请通过环境变量提供 DEEPSEEK_API_KEY")
        return key


class PlanItem(Record):
    task: str = Field(min_length=1, max_length=250)
    status: Literal["pending", "in_progress", "done"] = "pending"
    evidence: list[str] = Field(default_factory=list, max_length=12)


class Hypothesis(Record):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    claim: str = Field(min_length=1, max_length=600)
    expected: str = Field(min_length=1, max_length=600)
    status: Literal["active", "supported", "rejected", "unresolved"] = "active"
    evidence: list[Annotated[str, Field(pattern=r"^ar-[a-f0-9]{20}$")]] = Field(
        default_factory=list,
        max_length=12,
        description="只填写工具返回的原始 artifact ID，例如 ar-0123456789abcdef0123。描述写入 claim 或 next_action。",
    )
    next_action: str = Field(min_length=1, max_length=400)


class Outcome(Record):
    verdict: Literal["verified", "candidate", "not_reproduced", "inconclusive"]
    reason: str
    test_sha256: str
    validations: list[dict] = Field(default_factory=list)
