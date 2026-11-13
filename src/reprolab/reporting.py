"""One structured report drives Markdown export and the local viewer."""

import difflib
import json

from reprolab.core import atomic_write, now, redact
from reprolab.store import Store


def build_report(store: Store, run_id: str) -> dict:
    run = store.run(run_id)
    previous_tests, changes = {}, []
    for event in store.events(run_id):
        value = event["value"]
        if event["kind"] == "tool" and value.get("tool") == "write_reproducer" and value["result"]["ok"]:
            path = value["arguments"]["path"]
            content = value["arguments"]["content"]
            difference = "".join(
                difflib.unified_diff(
                    previous_tests.get(path, "").splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile="before/" + path,
                    tofile="after/" + path,
                )
            )
            changes.append({"path": path, "at": event["at"], "diff": difference})
            previous_tests[path] = content
    return {
        "schema_version": "1.0",
        "case": run["spec"].get("case"),
        "run_id": run_id,
        "generated_at": now(),
        "status": run["status"],
        "mode": run["config"].get("mode", "live"),
        "configuration": run["config"],
        "request": run["request"],
        "repository": run["spec"]["repository"],
        "buggy_commit": run["spec"]["buggy"],
        "fixed_commit": run["spec"].get("fixed"),
        "source": run["spec"].get("source"),
        "stop_reason": run["stop_reason"],
        "elapsed_seconds": round(run["elapsed"], 3),
        "plan": store.get(run_id, "state", "plan", []),
        "test_changes": changes,
        "prior_verifications": store.objects(run_id, "verification_history"),
        "hypotheses": store.objects(run_id, "hypotheses"),
        "skills": store.objects(run_id, "active_skills"),
        "experiments": store.objects(run_id, "experiments"),
        "submission": store.get(run_id, "state", "submission"),
        "verification": store.get(run_id, "state", "verification"),
        "artifacts": store.objects(run_id, "artifacts"),
        "statistics": store.statistics(run_id),
        "limitations": [
            "双版本差异及静态规则提供复现依据，测试语义仍需结合原始问题审查。",
            "普通容器提供受约束执行，适用范围为受控的纯 Python 项目。",
        ],
    }


def markdown(report: dict) -> str:
    lines = [
        "# ReproLab 复现报告",
        "",
        report["request"],
        "",
        f"任务 `{report['run_id']}` · 状态 `{report['status']}` · 模式 `{report['mode']}`",
        "",
        f"仓库 `{report['repository']}` · 缺陷版本 `{report['buggy_commit']}`",
        "",
    ]
    if report["fixed_commit"]:
        lines += [f"验收修复版本 `{report['fixed_commit']}`", ""]
    if report["verification"]:
        value = report["verification"]
        lines += [
            "## 验收结果",
            "",
            f"**{value['verdict']}**。{value['reason']}",
            "",
            f"测试 SHA256 `{value['test_sha256']}`",
            "",
        ]
    if report["stop_reason"]:
        lines += ["## 停止原因", "", report["stop_reason"], ""]
    lines += ["## 使用的 Skills", ""]
    for skill in report["skills"]:
        lines += [f"- `{skill['name']}` · {skill['reason']} · 内容 `{skill['sha256']}`"]
    lines += [
        "",
        "## 计划与假设",
        "",
        "```json",
        json.dumps(
            {"plan": report["plan"], "hypotheses": report["hypotheses"]}, ensure_ascii=False, indent=2
        ),
        "```",
        "",
        "## 实验",
        "",
    ]
    for experiment in report["experiments"]:
        lines += [
            f"- `{experiment['id']}` · 假设 `{experiment['hypothesis']}` · {experiment.get('result', {}).get('kind', experiment['status'])} · 日志 `{experiment.get('log', '')}`"
        ]
    lines += [
        "",
        "## 调用统计",
        "",
        "```json",
        json.dumps(report["statistics"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## 验证边界",
        "",
        *["- " + item for item in report["limitations"]],
        "",
    ]
    return "\n".join(lines)


def export(store: Store, run_id: str):
    directory = store.directory(run_id)
    report = build_report(store, run_id)
    atomic_write(directory / "report.json", redact(json.dumps(report, ensure_ascii=False, indent=2)))
    atomic_write(directory / "report.md", redact(markdown(report)))
    atomic_write(
        directory / "events.jsonl",
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in store.events(run_id)),
    )
    atomic_write(
        directory / "reproduce.sh",
        "# Run from the ReproLab project root with the original REPROLAB_HOME.\nuv run reprolab replay "
        + run_id
        + "\n",
    )
    return directory
