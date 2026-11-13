"""Independent, same-test verification on immutable buggy and fixed revisions."""

from reprolab.cases import source_path
from reprolab.core import Outcome
from reprolab.sandbox import Sandbox, check_test, test_hash
from reprolab.store import Store


def verify(store: Store, run_id: str, repeats: int = 3) -> Outcome:
    run = store.run(run_id)
    tests = store.directory(run_id) / "tests"
    submission = store.get(run_id, "state", "submission")
    current_hash = test_hash(tests)
    issues = [
        issue
        for file in tests.glob("test_*.py")
        for issue in check_test(file.read_text(), source_path(store.home, run["spec"]))
    ]
    if not submission or submission["test_sha256"] != current_hash or issues:
        return Outcome(
            verdict="inconclusive", reason="提交缺失、测试内容变化或静态检查未通过", test_sha256=current_hash
        )
    validations = []
    sandbox = Sandbox(store.settings)
    try:
        variants = ["buggy", "fixed"] if run["spec"].get("fixed") else ["buggy"]
        for variant in variants:
            for attempt in range(repeats):
                key = f"signature-v5:{sandbox.identity()}:{current_hash}:{variant}:{attempt}"
                result = store.get(run_id, "validations", key)
                if result is None:
                    result = sandbox.execute(source_path(store.home, run["spec"], variant), tests)
                    category = "private_validation" if variant == "fixed" else "validation"
                    log = store.artifact(run_id, result.pop("output", ""), category + "_log")
                    junit = store.artifact(run_id, result.pop("junit", ""), category + "_junit")
                    result.update(variant=variant, attempt=attempt + 1, log=log["id"], junit=junit["id"])
                    store.put(run_id, "validations", key, result)
                    store.event(run_id, "validation", result)
                validations.append(result)
    finally:
        sandbox.cleanup()
    buggy = [result for result in validations if result["variant"] == "buggy"]
    fixed = [result for result in validations if result["variant"] == "fixed"]
    reproduced = all(
        result["kind"] in {"assertion_failure", "target_exception"} and result["collected"] > 0
        for result in buggy
    )
    stable = len({result.get("failure_signature") for result in buggy}) == 1
    unchanged = test_hash(tests) == current_hash
    if reproduced and stable and unchanged and fixed and all(result["kind"] == "passed" for result in fixed):
        outcome = Outcome(
            verdict="verified",
            reason="同一测试在缺陷版稳定失败，在修复版全部通过",
            test_sha256=current_hash,
            validations=validations,
        )
        store.remember(run_id)
    elif reproduced and stable and unchanged and not fixed:
        outcome = Outcome(
            verdict="candidate",
            reason="缺陷版稳定复现，尚无修复版本可进行双版本验收",
            test_sha256=current_hash,
            validations=validations,
        )
    else:
        outcome = Outcome(
            verdict="not_reproduced"
            if buggy and all(r["kind"] == "passed" for r in buggy)
            else "inconclusive",
            reason="双版本验证或重复稳定性检查未满足，需结合实验日志复核",
            test_sha256=current_hash,
            validations=validations,
        )
    store.put(run_id, "state", "verification", outcome.model_dump())
    return outcome
