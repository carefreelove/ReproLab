import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from reprolab.cases import SYNTHETIC, prepare_case
from reprolab.core import LabError, Settings, bounded_path, redact
from reprolab.evaluation import new_task
from reprolab.model import ToolModel
from reprolab.sandbox import check_test, parse_result, write_test
from reprolab.sandbox import test_hash as content_hash
from reprolab.skills import Skills, validate
from reprolab.store import Store
from reprolab.tools import Actions
from reprolab.verification import verify
from reprolab.viewer import create_app


@pytest.fixture
def task(tmp_path):
    store = Store(Settings(home=tmp_path / "state"))
    spec = prepare_case(store.home, "empty-mean")
    run_id = new_task(store, spec, {"mode": "test", "namespace": "isolated"})
    return store, run_id


@pytest.mark.parametrize("relative", ["../outside", "/tmp/secret", "a/../b", "a//b", "a\\b", "a/./b", ""])
def test_path_boundary(tmp_path, relative):
    with pytest.raises(LabError):
        bounded_path(tmp_path, relative)


def test_symlink_rejected(tmp_path):
    (tmp_path / "link").symlink_to("/tmp")
    with pytest.raises(LabError):
        bounded_path(tmp_path, "link/secret")


def test_redaction(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "private-value-123456789")
    assert redact("private-value-123456789") == "[REDACTED]"


def test_skill_snapshot_and_progressive_loading(task):
    store, run_id = task
    skills = Skills(store, run_id)
    assert len(skills.catalog()) == 4
    assert store.objects(run_id, "active_skills") == []
    first = skills.activate("iterator-state", "验证迭代器状态")
    second = skills.activate("iterator-state", "重复激活")
    assert first["sha256"] == second["sha256"]
    assert len(store.objects(run_id, "active_skills")) == 1
    assert "TracingIterator" in skills.resource("iterator-state", "assets/tracing_iterator.py")


def test_skill_tampering_and_traversal(task):
    store, run_id = task
    skills = Skills(store, run_id)
    skills.activate("iterator-state", "test")
    with pytest.raises(LabError):
        skills.resource("iterator-state", "../SKILL.md")
    (skills.root / "iterator-state" / "SKILL.md").write_text("tampered")
    with pytest.raises(LabError):
        skills.resource("iterator-state", "SKILL.md")


def test_skill_activation_required(task):
    store, run_id = task
    with pytest.raises(LabError):
        Skills(store, run_id).resource("iterator-state", "SKILL.md")


def test_custom_skill_override_is_pinned(task, tmp_path):
    store, run_id = task
    directory = tmp_path / "custom" / "pytest-reproduction"
    directory.mkdir(parents=True)
    source = "---\nname: pytest-reproduction\ndescription: custom\n---\nCustom immutable procedure\n"
    (directory / "SKILL.md").write_text(source)
    second = new_task(store, store.run(run_id)["spec"], {}, directory.parent)
    (directory / "SKILL.md").write_text("changed later")
    assert (
        "Custom immutable" in Skills(store, second).activate("pytest-reproduction", "custom")["instructions"]
    )


@pytest.mark.parametrize(
    "body", ["invalid", "---\nname: Bad\ndescription: hi\n---\nbody", "---\nname: sample\n---\nbody"]
)
def test_invalid_skills(tmp_path, body):
    root = tmp_path / "sample"
    root.mkdir()
    (root / "SKILL.md").write_text(body)
    with pytest.raises(LabError):
        validate(root)


def test_budget_reservation_is_atomic(task):
    store, run_id = task
    ids = [store.create("budget", store.run(run_id)["spec"]) for _ in range(4)]

    def reserve(run):
        try:
            return store.reserve(run, 6_000_000)
        except LabError:
            return None

    with ThreadPoolExecutor(max_workers=4) as pool:
        tickets = list(pool.map(reserve, ids))
    assert sum(ticket is not None for ticket in tickets) == 3
    assert store.statistics(run_id)["global_accounted_cny"] == 18


def test_unknown_usage_preserves_reserve(task):
    store, run_id = task
    ticket = store.reserve(run_id, 100000)
    store.settle(ticket, None)
    assert store.statistics(run_id)["estimated_cost_cny"] == 0.1
    with pytest.raises(LabError):
        store.reserve(run_id, 1000)


def test_usage_settlement(task):
    store, run_id = task
    ticket = store.reserve(run_id, 100000)
    store.settle(ticket, {"input_tokens": 100, "output_tokens": 10})
    assert store.statistics(run_id)["estimated_cost_cny"] == 0.000336


def test_task_lock(task):
    store, run_id = task
    with store.lock(run_id):
        with pytest.raises(LabError):
            with store.lock(run_id):
                pass


def test_tool_operation_idempotency(task):
    store, run_id = task
    service = Actions(store, run_id)
    arguments = {"name": "boundary-analysis", "reason": "same call"}
    one = service.invoke("activate_skill", arguments, "stable-id")
    two = service.invoke("activate_skill", arguments, "stable-id")
    assert one == two
    assert len([e for e in store.events(run_id) if e["kind"] == "skill_activation"]) == 1
    with pytest.raises(LabError):
        service.invoke("read_file", {"path": "source.py"}, "stable-id")


def test_repeated_actions_stop(task):
    store, run_id = task
    service = Actions(store, run_id)
    for _ in range(3):
        service.invoke("read_file", {"path": "source.py"})
    assert store.get(run_id, "runtime", "stop") == "no_progress"


def test_source_is_read_only_through_tools(task):
    store, run_id = task
    service = Actions(store, run_id)
    assert service.invoke("write_reproducer", {"path": "source.py", "content": "x=1"})["ok"] is False
    with pytest.raises(LabError):
        write_test(service.tests, "../source.py", "x=1")


@pytest.mark.parametrize(
    "code,rule",
    [
        ("def test_x():\n    assert False", "constant_assertion"),
        ("import pytest\n@pytest.mark.skip\ndef test_x():\n    assert 1==1", "skipped_or_terminated"),
        ("import pathlib\ndef test_x():\n    assert 1==1", "environment_or_source_introspection"),
        ('def test_x():\n    assert package.__version__ == "1"', "version_or_source_assertion"),
        ("def test_x():\n    pass", "missing_assertion"),
        ("def test_x(", "syntax_error"),
    ],
)
def test_oracle_anti_cheating_rules(code, rule):
    assert rule in check_test(code)


@pytest.mark.parametrize(
    "xml,code,expected",
    [
        ('<testsuites><testsuite tests="0"/></testsuites>', 0, "collection_error"),
        ("<testsuites><testcase><skipped/></testcase></testsuites>", 0, "collection_error"),
        (
            '<testsuites><testcase><failure type="AssertionError">assert 0 == 1</failure></testcase></testsuites>',
            1,
            "assertion_failure",
        ),
        (
            '<testsuites><testcase><failure type="OverflowError">OverflowError</failure></testcase></testsuites>',
            1,
            "target_exception",
        ),
        ("<testsuites><testcase/></testsuites>", 0, "passed"),
        ("invalid", 2, "environment_error"),
    ],
)
def test_classify_test_outcomes(xml, code, expected):
    assert parse_result({"junit": xml, "exit_code": code, "output": ""})["kind"] == expected


def test_independent_verification_and_memory(task, monkeypatch):
    store, run_id = task
    tests = store.directory(run_id) / "tests"
    write_test(tests, "test_reproducer.py", SYNTHETIC["empty-mean"]["test"])
    store.put(run_id, "state", "submission", {"test_sha256": content_hash(tests)})

    def execute(self, source, tests):
        buggy = source.name == store.run(run_id)["spec"]["buggy"]
        return {
            "kind": "assertion_failure" if buggy else "passed",
            "collected": 1,
            "failure_signature": "stable",
            "output": "log",
            "junit": "<testsuites/>",
        }

    monkeypatch.setattr("reprolab.sandbox.Sandbox.execute", execute)
    monkeypatch.setattr("reprolab.sandbox.Sandbox.identity", lambda self: "sha256:fixture")
    assert verify(store, run_id).verdict == "verified"
    other = new_task(store, store.run(run_id)["spec"], {"namespace": "another-evaluation"})
    assert store.experiences(other) == []
    same = new_task(store, store.run(run_id)["spec"], {"namespace": "isolated"})
    assert len(store.experiences(same)) == 1
    monkeypatch.setattr(
        "reprolab.sandbox.Sandbox.execute", lambda *args: pytest.fail("cached verification should not rerun")
    )
    assert verify(store, run_id).verdict == "verified"


def test_viewer_escapes_untrusted_content(task):
    store, run_id = task
    store.put(run_id, "state", "plan", [{"task": "<script>alert(1)</script>", "status": "pending"}])
    client = TestClient(create_app(store))
    page = client.get("/runs/" + run_id)
    assert page.status_code == 200
    assert "<script>alert(1)</script>" not in page.text
    assert "&lt;script&gt;" in page.text
    assert client.get("/runs/invalid").status_code == 404
    assert client.get(f"/runs/{run_id}/artifacts/ar-missing").status_code == 404


def test_mcp_real_stdio_and_schema(task):
    from reprolab.bridge import MCPEnvironment

    store, run_id = task
    environment = MCPEnvironment(store, run_id)
    try:
        assert len(environment.tools) == 13
        schema = next(
            t["function"]["parameters"] for t in environment.tools if t["function"]["name"] == "read_file"
        )
        assert "ctx" not in schema["properties"]
        result = environment.execute(
            {"id": "read-one", "name": "read_file", "arguments": {"path": "source.py"}}
        )
        assert result["ok"] and "def mean" in result["data"]["content"]
        invalid = environment.execute(
            {"id": "read-invalid", "name": "read_file", "arguments": {"path": "source.py", "start_line": 0}}
        )
        assert not invalid["ok"]
        duplicate = environment.execute(
            {"id": "read-one", "name": "read_file", "arguments": {"path": "source.py"}}
        )
        assert duplicate == result
    finally:
        environment.close()


def test_metered_model_counts_actual_usage(task):
    from types import SimpleNamespace

    store, run_id = task

    class Message:
        def model_dump(self, **kwargs):
            return {
                "role": "assistant",
                "content": "ok",
                "tool_calls": [
                    {
                        "id": "fake-call",
                        "type": "function",
                        "function": {"name": "read_file", "arguments": '{"path":"source.py"}'},
                    }
                ],
            }

    response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=100, completion_tokens=10),
        choices=[SimpleNamespace(message=Message())],
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: response))
    )
    answer = ToolModel(store, run_id, [], client).query([{"role": "user", "content": "test"}])
    assert answer["extra"]["actions"][0]["name"] == "read_file"
    assert store.statistics(run_id)["estimated_cost_cny"] == 0.000336


def test_model_failure_never_serializes_raw_exception(task):
    from types import SimpleNamespace

    store, run_id = task

    def fail(**kwargs):
        raise RuntimeError("private-failure-value")

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fail)))
    with pytest.raises(LabError):
        ToolModel(store, run_id, [], client).query([{"role": "user", "content": "test"}])
    assert "private-failure-value" not in json.dumps(store.events(run_id))
    assert store.statistics(run_id)["global_unconfirmed_calls"] == 1


def test_context_trimming_preserves_skill_and_tool_groups(task):
    store, run_id = task
    Skills(store, run_id).activate("iterator-state", "retain instructions")
    messages = [{"role": "system", "content": "policy"}, {"role": "user", "content": "original issue"}]
    for i in range(12):
        messages += [
            {
                "role": "assistant",
                "content": "x" * 4000,
                "tool_calls": [
                    {"id": str(i), "type": "function", "function": {"name": "read_file", "arguments": "{}"}}
                ],
            },
            {"role": "tool", "tool_call_id": str(i), "content": "y" * 4000},
        ]
    working = ToolModel(store, run_id, [], client=object()).prepare(messages)
    assert len(json.dumps(working).encode()) < 44000
    assert "iterator-state" in working[2]["content"]
    assert working[0]["role"] == "system" and working[1]["content"] == "original issue"
    assert all(working[i - 1]["role"] == "assistant" for i, m in enumerate(working) if m["role"] == "tool")
    assert any(e["kind"] == "context_trim" for e in store.events(run_id))


def test_finished_task_rejects_mutating_tools(task):
    store, run_id = task
    store.update(run_id, status="completed")
    result = Actions(store, run_id).invoke(
        "activate_skill", {"name": "boundary-analysis", "reason": "late mutation"}
    )
    assert result["error"]["code"] == "task_state"


def test_failure_signature_ignores_only_process_addresses():
    first = '<testsuites><testcase><failure type="AssertionError" message="object at 0xabc123">assert value</failure></testcase></testsuites>'
    second = first.replace("0xabc123", "0xdef456")
    assert (
        parse_result({"junit": first, "exit_code": 1, "output": ""})["failure_signature"]
        == parse_result({"junit": second, "exit_code": 1, "output": ""})["failure_signature"]
    )


def test_hypothesis_requires_exact_artifact_ids():
    from pydantic import ValidationError

    from reprolab.core import Hypothesis

    with pytest.raises(ValidationError):
        Hypothesis(
            id="h",
            claim="claim",
            expected="expected",
            next_action="next",
            evidence=["ar-0123456789abcdef0123: description"],
        )


def test_sys_maxsize_is_an_allowed_boundary_constant():
    code = "import sys\nfrom source import value\ndef test_bound():\n    assert value(sys.maxsize) == 1\n"
    assert check_test(code) == []


def test_keyword_signature_uses_buggy_source(tmp_path):
    (tmp_path / "source.py").write_text("class numeric_range:\n    def __init__(self, *args): pass\n")
    invalid = "from source import numeric_range\ndef test_range():\n    assert numeric_range(10, step=2)\n"
    assert "call_signature:numeric_range:step" in check_test(invalid, tmp_path)
    assert not check_test(invalid.replace("10, step=2", "0, 10, 2"), tmp_path)


def test_fixed_verification_artifacts_are_not_agent_context(task):
    store, run_id = task
    private = store.artifact(run_id, "fixed-revision-private-value", "private_validation_log")
    public = store.artifact(run_id, "public-buggy-log", "experiment_log")
    result = Actions(store, run_id).invoke("read_artifact", {"artifact_id": private["id"]})
    assert result["error"]["code"] == "private_validation"
    context = ToolModel(store, run_id, [], client=object()).prepare(
        [{"role": "system", "content": "policy"}, {"role": "user", "content": "issue"}]
    )
    encoded = json.dumps(context)
    assert private["id"] not in encoded and "fixed-revision-private-value" not in encoded
    assert public["id"] in encoded


def test_artifact_categories_cannot_alias(task):
    store, run_id = task
    public = store.artifact(run_id, "identical content", "experiment_log")
    private = store.artifact(run_id, "identical content", "private_validation_log")
    assert public["id"] != private["id"]


def test_portable_bundle_checks_test_hash(task, tmp_path, monkeypatch):
    from reprolab.bundles import publish_bundle, replay_bundle
    from reprolab.core import Outcome

    store, run_id = task
    tests = store.directory(run_id) / "tests"
    write_test(tests, "test_reproducer.py", SYNTHETIC["empty-mean"]["test"])
    store.put(run_id, "state", "submission", {"test_sha256": content_hash(tests)})
    destination = tmp_path / "public-bundle"
    publish_bundle(store, run_id, destination)
    monkeypatch.setattr(
        "reprolab.bundles.verify",
        lambda s, r: Outcome(
            verdict="verified", reason="fixture", test_sha256=content_hash(s.directory(r) / "tests")
        ),
    )
    replayed = replay_bundle(store, destination)
    assert store.run(replayed)["status"] == "completed"
    (destination / "tests/test_reproducer.py").write_text("def test_tampered():\n    assert False\n")
    with pytest.raises(LabError, match="哈希"):
        replay_bundle(store, destination)


def test_traceback_assertion_line_does_not_hide_target_exception():
    xml = '<testsuites><testcase><failure message="ZeroDivisionError: division by zero">assert mean([]) == 0</failure></testcase></testsuites>'
    assert parse_result({"junit": xml, "exit_code": 1, "output": ""})["kind"] == "target_exception"
