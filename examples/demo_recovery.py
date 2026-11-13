"""Controlled live demo. Seeds an import error, then asks the Agent to repair the test.

Uses the current REPROLAB_HOME budget and incurs DeepSeek API charges.
"""

from reprolab.agent import execute
from reprolab.bridge import MCPEnvironment
from reprolab.cases import prepare_case
from reprolab.evaluation import new_task
from reprolab.store import Store


def main():
    from dotenv import load_dotenv

    load_dotenv()
    store = Store()
    spec = prepare_case(store.home, "empty-mean")
    spec["issue"] += (
        "\n这是受控恢复演示：已有 test_reproducer.py 被人为注入导入错误。"
        "请先使用 failure-triage 的 scripts/summarize.py 归纳已有日志，"
        "再覆盖同名测试文件，完成真实缺陷复现。"
    )
    run_id = new_task(
        store, spec, {"mode": "live", "namespace": "controlled-demo", "purpose": "seeded_import_error"}
    )
    environment = MCPEnvironment(store, run_id)
    seed = [
        ("activate_skill", {"name": "failure-triage", "reason": "受控演示中的初始导入错误"}),
        (
            "record_hypothesis",
            {
                "hypothesis": {
                    "id": "initial",
                    "claim": "初始测试导入可能不正确",
                    "expected": "观察导入错误并定位正确函数",
                    "next_action": "运行已有测试",
                }
            },
        ),
        (
            "write_reproducer",
            {
                "path": "test_reproducer.py",
                "content": "from source import average\n\ndef test_empty():\n    assert average([]) == 0\n",
            },
        ),
        ("run_tests", {}),
    ]
    try:
        for index, (name, arguments) in enumerate(seed):
            result = environment.execute({"id": f"seed-{index}", "name": name, "arguments": arguments})
            if not result.get("ok"):
                raise RuntimeError("Controlled demonstration preparation failed")
    finally:
        environment.close()
    print("controlled_demo", run_id, flush=True)
    path = execute(store, run_id)
    print(path / "report.md", flush=True)


if __name__ == "__main__":
    main()
