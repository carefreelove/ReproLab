import json
import os

import pytest

from reprolab.agent import execute
from reprolab.cases import SYNTHETIC, prepare_case
from reprolab.core import Settings
from reprolab.evaluation import ScriptedModel, new_task
from reprolab.sandbox import Sandbox, write_test
from reprolab.store import Store

pytestmark = pytest.mark.docker


@pytest.fixture(autouse=True)
def requires_docker():
    if os.getenv("REPROLAB_DOCKER_TESTS") != "1":
        pytest.skip("Set REPROLAB_DOCKER_TESTS=1 after building the image")


def test_real_loop_mcp_skills_and_verification(tmp_path):
    store = Store(Settings(home=tmp_path / "state"))
    run_id = new_task(store, prepare_case(store.home, "empty-mean"), {"mode": "offline_synthetic"})
    path = execute(store, run_id, ScriptedModel)
    report = json.loads((path / "report.json").read_text())
    assert report["verification"]["verdict"] == "verified"
    assert len(report["verification"]["validations"]) == 6
    assert len(report["skills"]) == 2
    assert report["statistics"]["model_calls"] == 0
    assert store.events(run_id)[1]["kind"] == "mcp_connected"
    before = len(store.events(run_id))
    execute(store, run_id, lambda *args: pytest.fail("completed task must not call model"))
    assert len(store.events(run_id)) == before


def test_sandbox_credentials_network_and_read_only(tmp_path, monkeypatch):
    from reprolab.core import atomic_write

    source = tmp_path / "source"
    tests = tmp_path / "tests"
    atomic_write(source / "source.py", "VALUE=1\n")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "host-secret-test-value")
    code = """import os
import socket
import pytest

def test_isolation():
    assert "DEEPSEEK_API_KEY" not in os.environ
    with pytest.raises(OSError):
        open('/workspace/source.py','w')
    with pytest.raises(OSError):
        socket.create_connection(('1.1.1.1',443),timeout=1)
    assert os.getuid() == 65534
"""
    write_test(tests, "test_isolation.py", code)
    result = Sandbox(Settings()).execute(source, tests)
    assert result["kind"] == "passed", result


def test_sandbox_timeout_cleans_container(tmp_path):
    import subprocess

    from reprolab.core import atomic_write

    source = tmp_path / "source"
    tests = tmp_path / "tests"
    atomic_write(source / "source.py", "VALUE=1")
    write_test(tests, "test_hang.py", "def test_hang():\n    while True:\n        pass\n")
    cleaned_names = []

    class RecordingSandbox(Sandbox):
        def cleanup(self):
            if self.current:
                cleaned_names.append(self.current)
            super().cleanup()

    sandbox = RecordingSandbox(Settings(test_seconds=1))
    result = sandbox.execute(source, tests)
    assert result["kind"] == "timeout"
    assert sandbox.current is None
    containers = subprocess.check_output(
        ["docker", "ps", "--filter", "name=reprolab-", "--format", "{{.Names}}"], text=True
    )
    assert cleaned_names and not set(cleaned_names).intersection(containers.splitlines())


def test_resume_paid_response_before_tool_dispatch(tmp_path):
    from reprolab.agent import ReproductionAgent
    from reprolab.bridge import MCPEnvironment

    store = Store(Settings(home=tmp_path / "state"))
    run_id = new_task(store, prepare_case(store.home, "empty-mean"), {"mode": "offline_synthetic"})
    environment = MCPEnvironment(store, run_id)
    try:
        agent = ReproductionAgent(ScriptedModel(store, run_id, environment.tools), environment, store, run_id)
        agent.add_messages(
            {"role": "system", "content": "fixture"}, {"role": "user", "content": "fixture task"}
        )
        agent.query()
        assert store.get(run_id, "state", "plan") is None
    finally:
        environment.close()
    path = execute(store, run_id, ScriptedModel)
    report = json.loads((path / "report.json").read_text())
    assert report["verification"]["verdict"] == "verified"
    assert sum(e["kind"] == "tool" and e["value"]["tool"] == "update_plan" for e in store.events(run_id)) == 1


def test_reflection_gate_and_experiment_operation_replay(tmp_path):
    from reprolab.tools import Actions

    store = Store(Settings(home=tmp_path / "state"))
    run_id = new_task(store, prepare_case(store.home, "empty-mean"), {"mode": "test"})
    actions = Actions(store, run_id)
    actions.invoke(
        "record_hypothesis",
        {
            "hypothesis": {
                "id": "h",
                "claim": "empty input fails",
                "expected": "failure",
                "next_action": "run",
            }
        },
    )
    actions.invoke(
        "write_reproducer", {"path": "test_reproducer.py", "content": SYNTHETIC["empty-mean"]["test"]}
    )
    result = actions.invoke("run_tests", {}, "stable-experiment")
    assert result["ok"]
    # Simulate server reply loss after the experiment was committed.
    store.put(run_id, "operations", "stable-experiment", {"status": "running", "tool": "run_tests"})
    again = actions.invoke("run_tests", {}, "stable-experiment")
    assert again["data"]["id"] == result["data"]["id"]
    assert len(store.objects(run_id, "experiments")) == 1
    rejected = actions.invoke("submit_reproducer", {"summary": "premature"})
    assert rejected["error"]["code"] == "reflection_required"


def test_cancel_and_resume_preserve_budget_and_clear_explicit_stop(tmp_path):
    class InterruptedModel(ScriptedModel):
        def query(self, messages, **kwargs):
            raise KeyboardInterrupt

    store = Store(Settings(home=tmp_path / "state"))
    run_id = new_task(store, prepare_case(store.home, "empty-mean"), {"mode": "offline_synthetic"})
    ticket = store.reserve(run_id, 10000)
    store.settle(ticket, {"input_tokens": 100, "output_tokens": 0})
    execute(store, run_id, InterruptedModel)
    assert store.run(run_id)["status"] == "cancelled"
    store.put(run_id, "runtime", "stop", "no_progress")
    elapsed = store.run(run_id)["elapsed"]
    execute(store, run_id, ScriptedModel)
    assert store.run(run_id)["status"] == "completed"
    assert store.run(run_id)["elapsed"] > elapsed
    assert store.statistics(run_id)["model_calls"] == 1
    assert store.statistics(run_id)["estimated_cost_cny"] == 0.00024
