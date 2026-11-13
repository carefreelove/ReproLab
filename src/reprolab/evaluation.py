"""Explicitly labelled scripted replay, live evaluation and one-shot baselines."""

import json
import uuid
from pathlib import Path

from reprolab.cases import REAL, SYNTHETIC, oracle_test, prepare_case
from reprolab.core import atomic_write
from reprolab.model import ToolModel
from reprolab.reporting import build_report
from reprolab.skills import Skills
from reprolab.store import Store


class ScriptedModel(ToolModel):
    """Protocol fixture with an evaluator-provided test; it is not a model quality measurement."""

    def query(self, messages, **kwargs):
        run = self.store.run(self.run_id)
        case = run["spec"]["case"]
        count = sum(message.get("role") == "assistant" for message in messages)
        experiment = self.store.get(self.run_id, "state", "last_experiment")
        steps = [
            (
                "update_plan",
                {"items": [{"task": "验证用户描述的边界行为", "status": "in_progress", "evidence": []}]},
            ),
            ("activate_skill", {"name": "pytest-reproduction", "reason": "构造可运行的目标断言"}),
            ("activate_skill", {"name": "boundary-analysis", "reason": "覆盖用户给出的输入边界"}),
            (
                "run_skill_script",
                {"name": "boundary-analysis", "path": "scripts/boundaries.py", "arguments": {"center": 0}},
            ),
            (
                "read_file",
                {
                    "path": "source.py" if case in SYNTHETIC else "more_itertools/more.py",
                    "start_line": 1,
                    "end_line": 80,
                },
            ),
            (
                "record_hypothesis",
                {
                    "hypothesis": {
                        "id": "h1",
                        "claim": "用户描述的边界在当前源码失败",
                        "expected": "目标断言失败或目标函数抛出异常",
                        "next_action": "编写并运行测试",
                    }
                },
            ),
            ("write_reproducer", {"path": "test_reproducer.py", "content": oracle_test(case)}),
            ("run_tests", {}),
            (
                "record_hypothesis",
                {
                    "hypothesis": {
                        "id": "h1",
                        "claim": "目标行为在实验中复现",
                        "expected": "缺陷版失败，修复版通过",
                        "status": "supported",
                        "evidence": [experiment["log"]] if experiment else [],
                        "next_action": "提交独立验收",
                    }
                },
            ),
            ("submit_reproducer", {"summary": "合成模型协议回放，测试内容由固定夹具提供。"}),
        ]
        if not run["config"].get("skills", True):
            steps = [
                (name, arguments)
                for name, arguments in steps
                if name not in {"activate_skill", "read_skill_resource", "run_skill_script"}
            ]
        name, arguments = steps[min(count, len(steps) - 1)]
        call_id = "scripted-" + str(count)
        return {
            "role": "assistant",
            "content": "offline_synthetic 协议动作",
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(arguments)},
                }
            ],
            "extra": {"actions": [{"id": call_id, "name": name, "arguments": arguments}], "cost": 0.0},
        }


def new_task(store: Store, spec: dict, config: dict, custom_skills: Path | None = None) -> str:
    run_id = store.create(spec["issue"], spec, config)
    Skills(store, run_id).snapshot(custom_skills)
    return run_id


def evaluate(store: Store, live: bool = False, ablations: bool = False, ablations_only: bool = False):
    from reprolab.agent import execute

    namespace = "eval-" + uuid.uuid4().hex
    results = []
    configurations = [("full", True, True)]
    if ablations or ablations_only:
        configurations += [("no_skills", False, True), ("no_explicit_reflection", True, False)]
    if ablations_only:
        configurations = configurations[1:]
    for label, skills, reflection in configurations:
        cases = list(SYNTHETIC | REAL) if label == "full" else ["shared-state", "chunked-even"]
        for case in cases:
            spec = prepare_case(store.home, case)
            run_id = new_task(
                store,
                spec,
                {
                    "mode": "live" if live else "offline_synthetic",
                    "namespace": namespace + ":" + label + ":" + case,
                    "skills": skills,
                    "reflection": reflection,
                    "variant": label,
                },
            )
            execute(store, run_id, None if live else ScriptedModel)
            report = build_report(store, run_id)
            entry = {
                "case": case,
                "variant": label,
                "run_id": run_id,
                "status": report["status"],
                "verification": report["verification"],
                "statistics": report["statistics"],
                "experiments": len(report["experiments"]),
                "elapsed_seconds": report["elapsed_seconds"],
            }
            results.append(entry)
            print(case, label, report["status"], flush=True)
            if live and label == "full":
                baseline_id = one_shot(store, spec, namespace + ":baseline:" + case)
                baseline = build_report(store, baseline_id)
                entry["baseline"] = {
                    "run_id": baseline_id,
                    "status": baseline["status"],
                    "verification": baseline["verification"],
                    "statistics": baseline["statistics"],
                    "information_access": "同模型、原始问题及至多12 KB相关源码，一次生成，无工具反馈",
                }
            filename = (
                "ablation-live.json"
                if ablations_only and live
                else ("evaluation-live.json" if live else "evaluation-offline.json")
            )
            path = store.home / filename
            atomic_write(
                path,
                json.dumps(
                    {
                        "results": results,
                        "mode": "live" if live else "offline_synthetic",
                        "note": "offline_synthetic 使用预设测试，仅验证执行协议。真实任务与基线信息访问方式存在差异。",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
    return path


def one_shot(store: Store, spec: dict, namespace: str) -> str:
    from reprolab.cases import source_path
    from reprolab.sandbox import Sandbox, test_hash, write_test
    from reprolab.verification import verify

    run_id = new_task(store, spec, {"mode": "live_baseline", "namespace": namespace, "skills": False})
    function = {
        "type": "function",
        "function": {
            "name": "deliver_test",
            "description": "Return one pytest reproduction test.",
            "parameters": {
                "type": "object",
                "properties": {"content": {"type": "string"}},
                "required": ["content"],
            },
        },
    }
    model = ToolModel(store, run_id, [function])
    source = source_path(store.home, spec)
    if spec["case"] in SYNTHETIC:
        text = (source / "source.py").read_text()
    else:
        lines = (source / "more_itertools/more.py").read_text().splitlines()
        marker = "def chunked_even" if spec["case"] == "chunked-even" else "class numeric_range"
        start = next(i for i, line in enumerate(lines) if line.startswith(marker))
        text = "\n".join(lines[start : start + 400])[:12000]
    try:
        answer = model.query(
            [
                {
                    "role": "system",
                    "content": "根据问题和固定版本源码生成一个最小pytest复现测试，使用正确期望行为，使缺陷自然暴露。通过deliver_test返回完整测试代码。",
                },
                {"role": "user", "content": spec["issue"] + "\n源码片段\n" + text},
            ]
        )
        atomic_write(
            store.directory(run_id) / "baseline-response.json",
            json.dumps(answer, ensure_ascii=False, indent=2),
        )
        test = answer["extra"]["actions"][0]["arguments"]["content"]
        tests = store.directory(run_id) / "tests"
        write_test(tests, "test_reproducer.py", test)
        result = Sandbox(store.settings).execute(source, tests)
        store.artifact(run_id, result.pop("output", ""), "baseline_log")
        result.pop("junit", None)
        store.put(
            run_id,
            "state",
            "submission",
            {"summary": "单次生成对照", "test_sha256": test_hash(tests), "experiment": "baseline"},
        )
        verdict = verify(store, run_id)
        store.update(run_id, status="completed" if verdict.verdict == "verified" else "partial")
    except Exception as exc:
        store.update(run_id, status="partial", stop_reason="baseline " + type(exc).__name__)
    from reprolab.reporting import export

    export(store, run_id)
    return run_id
