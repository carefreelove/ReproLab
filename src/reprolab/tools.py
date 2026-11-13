"""Task-bound tools exposed through a real MCP server."""

import functools
import inspect
import json
import time
import uuid
from typing import Annotated

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from pydantic import Field, ValidationError

from reprolab.cases import source_path
from reprolab.core import Hypothesis, LabError, PlanItem, bounded_path, digest
from reprolab.sandbox import Sandbox, check_test, test_hash, write_test
from reprolab.skills import Skills
from reprolab.store import Store


class Actions:
    def __init__(self, store: Store, run_id: str):
        self.store, self.run_id = store, run_id
        self.run = store.run(run_id)
        self.source = source_path(store.home, self.run["spec"])
        self.tests = store.directory(run_id) / "tests"
        self.tests.mkdir(exist_ok=True)
        self.skills = Skills(store, run_id)
        self.sandbox = Sandbox(store.settings)

    def invoke(self, name: str, arguments: dict, operation: str | None = None) -> dict:
        with self.store.lock(self.run_id, "tools.lock"):
            return self._invoke(name, arguments, operation)

    def _invoke(self, name: str, arguments: dict, operation: str | None) -> dict:
        arguments = json.loads(json.dumps(arguments, default=lambda value: value.model_dump()))
        operation = operation or uuid.uuid4().hex
        self.operation = operation
        previous = self.store.get(self.run_id, "operations", operation)
        if previous and previous["status"] == "completed":
            if previous["tool"] != name or previous.get("arguments_hash") != digest(
                json.dumps(arguments, sort_keys=True)
            ):
                raise LabError("operation_conflict", "操作 ID 与已有调用不一致")
            return previous["result"]
        started = time.monotonic()
        self.store.put(self.run_id, "operations", operation, {"status": "running", "tool": name})
        try:
            if name not in {
                "read_file",
                "read_artifact",
                "list_files",
                "search_code",
                "lookup_experience",
                "read_skill_resource",
            } and self.store.run(self.run_id)["status"] not in {"prepared", "running"}:
                raise LabError("task_state", "任务已结束，请通过 resume 恢复后继续修改")
            result = {"ok": True, "data": getattr(self, name)(**arguments)}
        except (LabError, ValidationError, ValueError) as exc:
            result = {
                "ok": False,
                "error": {"code": getattr(exc, "code", "invalid_arguments"), "message": str(exc)[:500]},
            }
        self.store.put(
            self.run_id,
            "operations",
            operation,
            {
                "status": "completed",
                "tool": name,
                "result": result,
                "arguments_hash": digest(json.dumps(arguments, sort_keys=True)),
            },
        )
        record = {
            "tool": name,
            "arguments": arguments,
            "result": result,
            "operation_id": operation,
            "seconds": round(time.monotonic() - started, 4),
        }
        self.store.event(self.run_id, "tool", record)
        # Stop exact repeated actions only when the generated tests have not changed.
        outcome = result
        if name == "run_tests" and result["ok"]:
            outcome = {key: result["data"]["result"].get(key) for key in ("kind", "failure_signature")}
        signature = digest(json.dumps([name, arguments, outcome, test_hash(self.tests)], sort_keys=True))
        last = self.store.get(self.run_id, "runtime", "progress", {})
        count = last.get("count", 0) + 1 if last.get("signature") == signature else 1
        self.store.put(self.run_id, "runtime", "progress", {"signature": signature, "count": count})
        if count >= 3:
            self.store.put(self.run_id, "runtime", "stop", "no_progress")
        return result

    def update_plan(self, items: Annotated[list[PlanItem], Field(min_length=1, max_length=8)]) -> dict:
        """Persist short research tasks, progress and artifact IDs supporting completed tasks."""
        validated = [PlanItem.model_validate(item).model_dump() for item in items]
        self.store.put(self.run_id, "state", "plan", validated)
        return {"plan": validated}

    def record_hypothesis(self, hypothesis: Hypothesis) -> dict:
        """Record a testable hypothesis, expected observation, outcome and next action."""
        value = Hypothesis.model_validate(hypothesis).model_dump()
        for artifact in value["evidence"]:
            metadata = self.store.get(self.run_id, "artifacts", artifact)
            if not metadata or metadata["category"].startswith("private_"):
                raise LabError(
                    "evidence",
                    "evidence 只填原始 artifact ID，可用ID为 "
                    + ", ".join(item["id"] for item in self.store.objects(self.run_id, "artifacts")[-10:]),
                )
        self.store.put(self.run_id, "hypotheses", value["id"], value)
        self.store.put(self.run_id, "state", "active_hypothesis", value["id"])
        self.store.event(self.run_id, "hypothesis", value)
        self.record_reflection(value)
        return value

    def lookup_experience(self) -> dict:
        """Retrieve verified strategy cards for the same repository, commit and memory namespace."""
        cards = self.store.experiences(self.run_id)
        self.store.event(self.run_id, "memory_lookup", {"hits": len(cards)})
        return {"cards": cards, "scope": "same repository, commit and namespace"}

    def activate_skill(self, name: str, reason: Annotated[str, Field(min_length=1, max_length=500)]) -> dict:
        """Activate a catalog skill and load its pinned instructions and resource inventory."""
        return self.skills.activate(name, reason)

    def read_skill_resource(self, name: str, path: str) -> dict:
        """Read one resource of an already active skill, relative to its immutable snapshot."""
        return {"content": self.skills.resource(name, path)}

    def run_skill_script(self, name: str, path: str, arguments: dict) -> dict:
        """Execute an activated skill's scripts/*.py with bounded JSON input in Docker."""
        if not path.startswith("scripts/") or not path.endswith(".py") or len(json.dumps(arguments)) > 16000:
            raise LabError("skill_script", "脚本须为 scripts/*.py，输入至多16 KB")
        self.skills.resource(name, path)
        output = self.sandbox.script(bounded_path(self.skills.root / name, path), arguments)
        artifact = self.store.artifact(self.run_id, output, "skill_script")
        self.store.event(
            self.run_id, "skill_script", {"name": name, "path": path, "artifact": artifact["id"]}
        )
        return {"output": output, "artifact": artifact["id"]}

    def list_files(
        self, path: str = "", pattern: str = "*", offset: Annotated[int, Field(ge=0, le=5000)] = 0
    ) -> dict:
        """List up to 80 entries in one source directory; use globs to filter names."""
        directory = bounded_path(self.source, path) if path else self.source
        if not directory.is_dir():
            raise LabError("not_found", "源码目录不存在")
        rows = [
            file
            for file in sorted(directory.iterdir())
            if file.match(pattern) and not file.name.startswith(".")
        ]
        items = [
            {"path": file.relative_to(self.source).as_posix(), "directory": file.is_dir()}
            for file in rows[offset : offset + 80]
        ]
        return {
            "items": items,
            "truncated": len(rows) > offset + 80,
            "next_offset": offset + 80 if len(rows) > offset + 80 else None,
        }

    def search_code(self, query: Annotated[str, Field(min_length=1, max_length=160)], path: str = "") -> dict:
        """Search source text for literal identifiers; return up to 20 path and line hits."""
        root = bounded_path(self.source, path) if path else self.source
        hits = []
        files = [root] if root.is_file() else sorted(root.rglob("*.py"))
        for file in files[:3000]:
            if file.is_symlink() or file.stat().st_size > 500000:
                continue
            try:
                lines = file.read_text().splitlines()
            except (UnicodeError, OSError):
                continue
            for number, line in enumerate(lines, 1):
                if query.casefold() in line.casefold():
                    hits.append(
                        {"path": file.relative_to(self.source).as_posix(), "line": number, "text": line[:250]}
                    )
                    if len(hits) >= 20:
                        return {"hits": hits, "truncated": True}
        return {"hits": hits, "truncated": False}

    def read_file(
        self,
        path: str,
        start_line: Annotated[int, Field(ge=1)] = 1,
        end_line: Annotated[int, Field(ge=1)] = 120,
    ) -> dict:
        """Read up to 200 source lines, 16 KB, preserving original line numbers."""
        if not start_line <= end_line < start_line + 200:
            raise LabError("line_range", "每次读取1至200行")
        file = bounded_path(self.source, path)
        if not file.is_file() or file.stat().st_size > 2_000_000:
            raise LabError("not_found", "源码文件不存在或超过大小上限")
        try:
            lines = file.read_text().splitlines()
        except UnicodeError as exc:
            raise LabError("binary", "文件不是 UTF-8 文本") from exc
        selected = []
        for number, line in enumerate(lines[start_line - 1 : end_line], start_line):
            row = f"{number}: {line}"
            if len(("\n".join([*selected, row])).encode()) > 16000:
                break
            selected.append(row)
        content = "\n".join(selected)
        artifact = self.store.artifact(self.run_id, content, "source")
        return {
            "path": path,
            "commit": self.run["spec"]["buggy"],
            "content": content,
            "artifact": artifact["id"],
            "truncated": start_line > 1 or len(selected) < len(lines),
        }

    def write_reproducer(self, path: str, content: Annotated[str, Field(max_length=24000)]) -> dict:
        """Write test_*.py in the generated test directory; production source is read-only."""
        if not self.store.get(self.run_id, "state", "active_hypothesis"):
            raise LabError("hypothesis_required", "编写测试前请记录可检验假设")
        write_test(self.tests, path, content)
        return {"path": path, "sha256": digest(content), "checks": check_test(content, self.source)}

    def run_tests(self) -> dict:
        """Run current generated tests in the buggy source only; inspect evidence and update hypothesis afterward."""
        if not list(self.tests.glob("test_*.py")):
            raise LabError("tests_required", "请先生成测试")
        experiments = self.store.objects(self.run_id, "experiments")
        operation = getattr(self, "operation", None)
        for experiment in experiments:
            if operation and experiment.get("operation_id") == operation:
                if experiment["status"] == "completed":
                    return experiment
                experiment["status"] = "interrupted"
                self.store.put(self.run_id, "experiments", experiment["id"], experiment)
        if len(experiments) >= self.store.settings.max_experiments:
            raise LabError("experiment_limit", "实验次数达到上限，请提交现有证据")
        if self.run["config"].get("reflection", True) and self.store.get(
            self.run_id, "state", "needs_reflection"
        ):
            raise LabError("reflection_required", "请先用上次实验 artifact 更新假设与下一步")
        hypothesis_id = self.store.get(self.run_id, "state", "active_hypothesis")
        hypothesis = self.store.get(self.run_id, "hypotheses", hypothesis_id)
        if not hypothesis or hypothesis["status"] != "active":
            raise LabError("hypothesis_required", "运行实验需要一个 active 假设")
        experiment_id = "ex-" + uuid.uuid4().hex[:12]
        value = {
            "operation_id": operation,
            "id": experiment_id,
            "hypothesis": hypothesis_id,
            "test_sha256": test_hash(self.tests),
            "status": "running",
        }
        self.store.put(self.run_id, "experiments", experiment_id, value)
        result = self.sandbox.execute(self.source, self.tests)
        log = self.store.artifact(self.run_id, result.pop("output", ""), "test_log")
        junit = self.store.artifact(self.run_id, result.pop("junit", ""), "junit")
        value.update(status="completed", result=result, log=log["id"], junit=junit["id"])
        self.store.put(self.run_id, "experiments", experiment_id, value)
        self.store.put(self.run_id, "state", "last_experiment", value)
        self.store.put(self.run_id, "state", "needs_reflection", log["id"])
        self.store.event(self.run_id, "experiment", value)
        return value

    def read_artifact(self, artifact_id: str, start_line: Annotated[int, Field(ge=1)] = 1) -> dict:
        """Recover original evidence/log lines by current-task artifact ID after context trimming."""
        metadata = self.store.get(self.run_id, "artifacts", artifact_id)
        if metadata and metadata["category"].startswith("private_"):
            raise LabError("private_validation", "该资料仅由独立验收器读取")
        lines = self.store.read_artifact(self.run_id, artifact_id).splitlines()
        text = "\n".join(lines[start_line - 1 : start_line + 199])
        self.store.event(self.run_id, "artifact_read", {"artifact": artifact_id})
        return {
            "artifact_id": artifact_id,
            "content": text.encode()[:16000].decode(errors="ignore"),
            "truncated": len(lines) > start_line + 199,
        }

    def submit_reproducer(self, summary: Annotated[str, Field(min_length=1, max_length=1500)]) -> dict:
        """Freeze the current test and experiment for independent verification. Include behavior and remaining uncertainty."""
        if self.run["config"].get("reflection", True) and self.store.get(
            self.run_id, "state", "needs_reflection"
        ):
            raise LabError("reflection_required", "请引用最后实验日志更新假设与下一步，再提交验收")
        experiment = self.store.get(self.run_id, "state", "last_experiment")
        if not experiment or experiment["test_sha256"] != test_hash(self.tests):
            raise LabError("experiment_required", "当前测试需要先运行一次实验")
        if experiment["result"]["kind"] not in {"assertion_failure", "target_exception"}:
            raise LabError("not_reproduced", "当前实验尚未触发目标问题")
        issues = [
            issue
            for file in self.tests.glob("test_*.py")
            for issue in check_test(file.read_text(), self.source)
        ]
        if issues:
            raise LabError("invalid_test", "测试检查发现 " + ", ".join(sorted(set(issues))))
        value = {"summary": summary, "test_sha256": test_hash(self.tests), "experiment": experiment["id"]}
        self.store.put(self.run_id, "state", "submission", value)
        return {"submitted": True, **value}

    def record_reflection(self, hypothesis: dict):
        artifact = self.store.get(self.run_id, "state", "needs_reflection")
        if artifact and artifact in hypothesis.get("evidence", []):
            self.store.put(self.run_id, "state", "needs_reflection", None)


TOOL_NAMES = [
    "update_plan",
    "record_hypothesis",
    "lookup_experience",
    "activate_skill",
    "read_skill_resource",
    "run_skill_script",
    "list_files",
    "search_code",
    "read_file",
    "write_reproducer",
    "run_tests",
    "read_artifact",
    "submit_reproducer",
]


def create_server(store: Store, run_id: str) -> MCPServer:
    actions = Actions(store, run_id)
    server = MCPServer(
        "ReproLab", instructions="Tools are restricted to one reproduction task and its snapshots."
    )
    for name in TOOL_NAMES:
        method = getattr(actions, name)

        def make_wrapper(method, name):
            @functools.wraps(method)
            def wrapper(*args, ctx=None, **kwargs):
                meta = ctx.request_context.meta if ctx else {}
                result = actions.invoke(name, kwargs, (meta or {}).get("reprolab/operation"))
                if name == "record_hypothesis" and result["ok"]:
                    actions.record_reflection(result["data"])
                return result

            wrapper.__signature__ = inspect.signature(method).replace(
                parameters=[
                    *inspect.signature(method).parameters.values(),
                    inspect.Parameter(
                        "ctx", inspect.Parameter.KEYWORD_ONLY, default=None, annotation=Context
                    ),
                ]
            )
            wrapper.__annotations__ = {**method.__annotations__, "ctx": Context}
            return wrapper

        server.tool(name=name)(make_wrapper(method, name))
    return server
