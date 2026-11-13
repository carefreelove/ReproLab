"""Command-line task lifecycle and loopback viewer."""

import json
import re
from pathlib import Path

import typer
import uvicorn
from dotenv import load_dotenv
from rich.console import Console

from reprolab.cases import REAL, SYNTHETIC, fetch_snapshot, prepare_case
from reprolab.core import LabError
from reprolab.evaluation import evaluate, new_task
from reprolab.reporting import export
from reprolab.skills import BUILTINS, validate
from reprolab.store import Store

app = typer.Typer(
    no_args_is_help=True, pretty_exceptions_enable=False, help="ReproLab｜故障复现与回归测试 Agent"
)
skill_app = typer.Typer(no_args_is_help=True)
app.add_typer(skill_app, name="skills")
console = Console()


@app.callback()
def configure():
    load_dotenv()


def finish(store, run_id):
    path = export(store, run_id)
    report = json.loads((path / "report.json").read_text())
    console.print(f"任务 {run_id} · {report['status']}", markup=False)
    console.print(str(path / "report.md"), markup=False)
    if report["stop_reason"]:
        console.print(report["stop_reason"], markup=False)
    if report["status"] != "completed":
        raise typer.Exit(1)


@app.command()
def run(
    case: str | None = None,
    repo: str | None = None,
    commit: str | None = None,
    issue: Path | None = None,
    skill: str | None = None,
    skills_dir: Path | None = None,
):
    """创建复现任务并执行 Agent 与独立验收。"""
    from reprolab.agent import execute

    store = Store()
    try:
        if case:
            if repo or commit or issue:
                raise LabError("arguments", "--case 与仓库参数互斥")
            spec = prepare_case(store.home, case)
        else:
            if not repo or not commit or not issue or not issue.is_file():
                raise LabError("arguments", "请提供 --case 或 --repo、--commit、--issue")
            repository = re.sub(r"^https://github.com/", "", repo).removesuffix(".git").rstrip("/")
            fetch_snapshot(store.home, repository, commit)
            spec = {
                "repository": repository,
                "buggy": commit,
                "fixed": None,
                "issue": issue.read_text(),
                "source": f"https://github.com/{repository}/tree/{commit}",
            }
        run_id = new_task(store, spec, {"mode": "live", "namespace": "normal"}, skills_dir)
        if skill:
            from reprolab.skills import Skills

            Skills(store, run_id).activate(skill, "用户显式选择")
        console.print("开始任务 " + run_id, markup=False)
        execute(store, run_id)
        finish(store, run_id)
    except LabError as exc:
        console.print(f"{exc.code} · {exc}", markup=False)
        raise typer.Exit(1) from exc


@app.command()
def show(run_id: str):
    """查看已保存报告。"""
    store = Store()
    path = export(store, run_id)
    console.print((path / "report.md").read_text(), markup=False)


@app.command()
def resume(run_id: str):
    """沿用账本、Skill 快照和实验恢复任务。"""
    from reprolab.agent import execute

    store = Store()
    execute(store, run_id)
    finish(store, run_id)


@app.command()
def replay(run_id: str):
    """用已保存测试重新进行独立验收，沿用固定源码版本。"""
    from reprolab.verification import verify

    store = Store()
    if Path(run_id).is_dir():
        from reprolab.bundles import replay_bundle

        run_id = replay_bundle(store, Path(run_id))
        finish(store, run_id)
        return
    with store.lock(run_id):
        outcome = verify(store, run_id)
        console.print(outcome.model_dump_json(indent=2), markup=False)


@app.command()
def serve(port: int = 8765):
    """在127.0.0.1启动只读轨迹页面。"""
    from reprolab.viewer import create_app

    uvicorn.run(create_app(Store()), host="127.0.0.1", port=port)


@app.command("evaluate")
def evaluate_command(
    suite: str = "smoke", live: bool = False, ablations: bool = False, ablations_only: bool = False
):
    """运行固定题集。--live 使用真实模型，计入累计预算。"""
    if suite != "smoke":
        raise typer.BadParameter("当前提供 smoke 题集")
    path = evaluate(Store(), live, ablations, ablations_only)
    console.print(str(path), markup=False)
    if any(item["status"] != "completed" for item in json.loads(path.read_text())["results"]):
        raise typer.Exit(1)


@app.command()
def cases():
    """列出自建及真实历史缺陷。"""
    for name in SYNTHETIC | REAL:
        console.print(name + (" · real_history" if name in REAL else " · self_authored"), markup=False)


@skill_app.command("list")
def skill_list():
    for directory in sorted(BUILTINS.iterdir()):
        if (directory / "SKILL.md").exists():
            value = validate(directory)
            console.print(f"{value['name']} · {value['description']}", markup=False)


@skill_app.command("validate")
def skill_validate(directory: Path):
    directories = (
        [directory]
        if (directory / "SKILL.md").exists()
        else sorted(path for path in directory.iterdir() if path.is_dir())
    )
    for path in directories:
        console.print(validate(path)["name"] + " · valid", markup=False)
