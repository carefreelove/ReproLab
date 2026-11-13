"""Portable, credential-free reproduction bundles and deterministic re-validation."""

import json
import shutil
from pathlib import Path

from reprolab.cases import fetch_snapshot, prepare_case
from reprolab.core import LabError
from reprolab.evaluation import new_task
from reprolab.reporting import export
from reprolab.sandbox import test_hash, write_test
from reprolab.store import Store
from reprolab.verification import verify


def publish_bundle(store: Store, run_id: str, destination: Path):
    export(store, run_id)
    root = store.directory(run_id)
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("report.md", "report.json", "trajectory.json", "events.jsonl", "baseline-response.json"):
        if (root / name).exists():
            shutil.copy2(root / name, destination / name)
    for name in ("tests", "artifacts", "skills"):
        if (root / name).exists():
            shutil.copytree(root / name, destination / name, dirs_exist_ok=True)


def replay_bundle(store: Store, directory: Path) -> str:
    report = json.loads((directory / "report.json").read_text())
    if report.get("case"):
        spec = prepare_case(store.home, report["case"])
        if spec["buggy"] != report["buggy_commit"] or spec.get("fixed") != report.get("fixed_commit"):
            raise LabError("bundle_version", "示例版本与固定案例定义不一致")
    else:
        spec = {
            "repository": report["repository"],
            "buggy": report["buggy_commit"],
            "fixed": report.get("fixed_commit"),
            "issue": report["request"],
            "source": report.get("source"),
        }
        for variant in ("buggy", "fixed"):
            if spec.get(variant):
                fetch_snapshot(store.home, spec["repository"], spec[variant])
    run_id = new_task(store, spec, {"mode": "artifact_replay", "namespace": "artifact-replay"})
    tests = store.directory(run_id) / "tests"
    for path in (directory / "tests").glob("test_*.py"):
        if path.is_symlink():
            raise LabError("bundle_path", "示例测试不能为符号链接")
        write_test(tests, path.name, path.read_text())
    expected = (report.get("verification") or report.get("submission") or {}).get("test_sha256")
    if not expected or expected != test_hash(tests):
        raise LabError("bundle_hash", "示例测试与已记录哈希不一致")
    store.put(run_id, "state", "submission", {"summary": "公开产物的独立复现", "test_sha256": expected})
    outcome = verify(store, run_id)
    store.update(run_id, status="completed" if outcome.verdict in ("verified", "candidate") else "partial")
    export(store, run_id)
    return run_id
