"""Short-lived, non-root Docker experiments with immutable source snapshots."""

import ast
import json
import re
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from reprolab.core import LabError, Settings, atomic_write, bounded_path, digest, redact

RUNNER = """import json
import pathlib
import subprocess
import sys

root = pathlib.Path('/work')
root.mkdir(exist_ok=True)
with (root / 'pytest.log').open('w') as output:
    result = subprocess.run([
        sys.executable, '-m', 'pytest', '-c', '/dev/null', '--rootdir=/work',
        '--import-mode=importlib', '-p', 'no:cacheprovider', '-q',
        '--junitxml=/work/result.xml', '/tests',
    ], cwd=root, stdout=output, stderr=subprocess.STDOUT)
with (root / 'pytest.log').open('rb') as output:
    output.seek(max(0, output.seek(0, 2) - 12000))
    log = output.read(12000).decode('utf-8', errors='replace')
xml = root / 'result.xml'
junit = ''
if xml.exists() and xml.stat().st_size <= 262144:
    junit = xml.read_text()
print('REPROLAB_RESULT_JSON=' + json.dumps({
    'exit_code': result.returncode, 'junit': junit, 'output': log,
}))
"""

SCRIPT_RUNNER = """import json, pathlib, subprocess, sys
with pathlib.Path('/tmp/skill.log').open('w') as output:
    result = subprocess.run([sys.executable, '-c', sys.argv[1]],
                            stdout=output, stderr=subprocess.STDOUT)
with pathlib.Path('/tmp/skill.log').open('rb') as output:
    data = output.read(16001)
print(data[:16000].decode('utf-8', errors='replace'))
if len(data) > 16000:
    print('[output truncated at 16000 bytes]')
sys.exit(result.returncode)
"""


def check_test(content: str, source: Path | None = None) -> list[str]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return ["syntax_error"]
    issues = []
    has_check = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            has_check = True
            if isinstance(node.test, ast.Constant):
                issues.append("constant_assertion")
        if isinstance(node, ast.Call):
            name = ast.unparse(node.func)
            if name.endswith(("raises", "assertEqual", "assertTrue", "assertFalse", "assertRaises")):
                has_check = True
            if name in {
                "open",
                "eval",
                "exec",
                "__import__",
                "compile",
                "getattr",
                "setattr",
            } or name.startswith(("os.", "subprocess.", "inspect.", "importlib.")):
                issues.append("unsafe_or_source_introspection")
            if name.endswith(("skip", "skipif", "xfail", "exit", "_exit")):
                issues.append("skipped_or_terminated")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else [name.name for name in node.names]
            )
            if any(
                name.split(".")[0] in {"os", "subprocess", "inspect", "importlib", "pathlib", "socket"}
                for name in names
            ):
                issues.append("environment_or_source_introspection")
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "sys"
            and node.attr != "maxsize"
        ):
            issues.append("environment_or_source_introspection")
        if isinstance(node, ast.Attribute) and node.attr in {"skip", "skipif", "xfail"}:
            issues.append("skipped_or_terminated")
        if isinstance(node, ast.Attribute) and node.attr in {
            "__version__",
            "__code__",
            "__globals__",
            "__dict__",
        }:
            issues.append("version_or_source_assertion")
    if not has_check:
        issues.append("missing_assertion")
    if source:
        issues.extend(check_call_signatures(tree, source))
    return sorted(set(issues))


def check_call_signatures(test: ast.Module, source: Path) -> list[str]:
    """Conservatively check imported, direct calls against buggy-source AST signatures."""
    imported = {}
    modules = set()
    for node in ast.walk(test):
        if isinstance(node, ast.ImportFrom):
            imported.update({item.asname or item.name: item.name for item in node.names})
        elif isinstance(node, ast.Import):
            modules.update(item.asname or item.name.split(".")[0] for item in node.names)
    definitions = {}
    for path in source.rglob("*.py"):
        if any(part in {"tests", "docs", "__pycache__"} for part in path.relative_to(source).parts):
            continue
        try:
            module = ast.parse(path.read_text())
        except (SyntaxError, UnicodeError):
            continue
        for node in module.body:
            name = getattr(node, "name", None)
            function = node
            if isinstance(node, ast.ClassDef):
                function = next(
                    (
                        item
                        for item in node.body
                        if isinstance(item, ast.FunctionDef) and item.name == "__init__"
                    ),
                    None,
                )
            if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions.setdefault(name, []).append(function.args)
    issues = []
    for call in ast.walk(test):
        if not isinstance(call, ast.Call):
            continue
        name = imported.get(call.func.id) if isinstance(call.func, ast.Name) else None
        if (
            isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id in modules
        ):
            name = call.func.attr
        candidates = definitions.get(name, [])
        for keyword in call.keywords:
            if (
                keyword.arg
                and candidates
                and all(
                    candidate.kwarg is None
                    and keyword.arg not in {arg.arg for arg in [*candidate.args, *candidate.kwonlyargs]}
                    for candidate in candidates
                )
            ):
                issues.append(f"call_signature:{name}:{keyword.arg}")
    return issues


def parse_result(payload: dict) -> dict:
    try:
        root = ET.fromstring(payload["junit"])
    except ET.ParseError:
        return {"kind": "environment_error", "collected": 0, "exit_code": payload["exit_code"]}
    cases = list(root.iter("testcase"))
    failures = [failure for case in cases for failure in case.findall("failure")]
    errors = [error for case in cases for error in case.findall("error")]
    skipped = sum(case.find("skipped") is not None for case in cases)
    output = payload["output"]
    if not cases or skipped:
        kind = "collection_error"
    elif errors or payload["exit_code"] not in (0, 1):
        kind = (
            "import_error"
            if "ImportError" in output or "ModuleNotFoundError" in output
            else "collection_error"
        )
    elif failures and any(
        "unexpected keyword argument" in (item.text or "")
        or "required positional argument" in (item.text or "")
        for item in failures
    ):
        kind = "test_error"
    elif failures:
        kind = (
            "assertion_failure"
            if all(
                re.match(
                    r"(?:AssertionError\b|assert\s|Failed: DID NOT RAISE\b)",
                    item.attrib.get("message") or (item.text or "").strip(),
                )
                for item in failures
            )
            else "target_exception"
        )
    elif payload["exit_code"] == 0:
        kind = "passed"
    else:
        kind = "environment_error"
    signature = digest(
        json.dumps(
            [
                (
                    item.attrib.get("type"),
                    re.sub(r"0x[0-9a-fA-F]+", "0xADDRESS", item.attrib.get("message", "")),
                )
                for item in failures
            ],
            sort_keys=True,
        )
    )
    return {
        "kind": kind,
        "collected": len(cases),
        "skipped": skipped,
        "failed": len(failures),
        "exit_code": payload["exit_code"],
        "failure_signature": signature,
        "failure_details": [
            {
                "test": case.attrib.get("name", ""),
                "message": re.sub(r"0x[0-9a-fA-F]+", "0xADDRESS", failure.attrib.get("message", ""))[:400],
            }
            for case in cases
            for failure in case.findall("failure")
        ][:10],
    }


class Sandbox:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.current: str | None = None
        self._identity: str | None = None

    def identity(self) -> str:
        if self._identity is None:
            result = subprocess.run(
                ["docker", "image", "inspect", "--format", "{{.Id}}", self.settings.image],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode or not result.stdout.strip().startswith("sha256:"):
                raise LabError("sandbox_image", "请先按 README 构建测试镜像并启动 Docker")
            self._identity = result.stdout.strip()
        return self._identity

    def execute(self, source: Path, tests: Path, seconds: int | None = None) -> dict:
        for root in (source, tests):
            for file in root.rglob("*"):
                if file.is_symlink():
                    raise LabError("invalid_path", "工作区包含符号链接")
        # Docker bind mounts preserve host permissions; artifacts contain no credentials.
        for root in (source, tests):
            root.chmod(0o755)
            for file in root.rglob("*"):
                file.chmod(0o755 if file.is_dir() else 0o644)
        name = "reprolab-" + uuid.uuid4().hex[:12]
        self.current = name
        command = [
            "docker",
            "run",
            "--rm",
            "--name",
            name,
            "--network",
            "none",
            "--read-only",
            "--user",
            "65534:65534",
            "--cpus",
            "1",
            "--memory",
            "512m",
            "--pids-limit",
            "64",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--tmpfs",
            "/tmp:rw,nosuid,size=64m",
            "--tmpfs",
            "/work:rw,nosuid,size=64m",
            "--mount",
            f"type=bind,src={source.resolve()},dst=/workspace,readonly",
            "--mount",
            f"type=bind,src={tests.resolve()},dst=/tests,readonly",
            "-e",
            "PYTHONPATH=/workspace",
            "-e",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
            self.identity(),
            "timeout",
            str(seconds or self.settings.test_seconds),
            "python",
            "-c",
            RUNNER,
        ]
        started = time.monotonic()
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=seconds or self.settings.test_seconds,
            )
            marker = "REPROLAB_RESULT_JSON="
            lines = [line[len(marker) :] for line in result.stdout.splitlines() if line.startswith(marker)]
            if result.returncode == 124:
                return {"kind": "timeout", "collected": 0, "output": "测试超时"}
            if result.returncode != 0 or len(lines) != 1:
                return {
                    "kind": "environment_error",
                    "collected": 0,
                    "output": redact(result.stdout[-12000:]),
                    "seconds": round(time.monotonic() - started, 3),
                }
            payload = json.loads(lines[0])
            return {
                **parse_result(payload),
                "output": redact(payload["output"]),
                "junit": payload["junit"],
                "seconds": round(time.monotonic() - started, 3),
                "image_id": self.identity(),
            }
        except subprocess.TimeoutExpired:
            return {
                "kind": "timeout",
                "collected": 0,
                "output": "测试超时，容器已清理",
                "seconds": round(time.monotonic() - started, 3),
            }
        finally:
            self.cleanup()

    def script(self, script: Path, arguments: dict) -> str:
        name = "reprolab-skill-" + uuid.uuid4().hex[:10]
        self.current = name
        try:
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--name",
                    name,
                    "--network",
                    "none",
                    "--read-only",
                    "--user",
                    "65534:65534",
                    "--memory",
                    "128m",
                    "--cpus",
                    "1",
                    "--pids-limit",
                    "32",
                    "--cap-drop",
                    "ALL",
                    "--security-opt",
                    "no-new-privileges",
                    "--tmpfs",
                    "/tmp:rw,nosuid,size=16m",
                    "-i",
                    self.identity(),
                    "python",
                    "-c",
                    SCRIPT_RUNNER,
                    script.read_text(),
                ],
                input=json.dumps(arguments),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=10,
            )
            if result.returncode:
                raise LabError("skill_script", "Skill 脚本执行失败")
            return redact(result.stdout[:16000])
        finally:
            self.cleanup()

    def cleanup(self):
        if self.current:
            subprocess.run(
                ["docker", "rm", "-f", self.current],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
            )
            self.current = None


def write_test(root: Path, path: str, content: str):
    if (
        not path.startswith("test_")
        or not path.endswith(".py")
        or "/" in path
        or len(content.encode()) > 24000
    ):
        raise LabError("test_path", "测试应为 test_*.py，至多 24 KB")
    atomic_write(bounded_path(root, path), content)


def test_hash(root: Path) -> str:
    return digest(
        "".join(path.name + ":" + digest(path.read_bytes()) for path in sorted(root.glob("test_*.py")))
    )
