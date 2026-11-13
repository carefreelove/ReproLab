"""Agent Skills discovery, immutable snapshots and progressive disclosure."""

import re
import shutil
from pathlib import Path

import yaml

from reprolab.core import LabError, bounded_path, digest
from reprolab.store import Store

BUILTINS = Path(__file__).parent / "skills"


def validate(root: Path) -> dict:
    path = root / "SKILL.md"
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 16000:
        raise LabError("skill_format", "Skill 需要至多 16 KB 的 SKILL.md")
    text = path.read_text()
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise LabError("skill_format", "SKILL.md 需要 YAML frontmatter")
    front, body = text[4:].split("\n---\n", 1)
    try:
        data = yaml.safe_load(front)
    except yaml.YAMLError as exc:
        raise LabError("skill_format", "Skill YAML 无法解析") from exc
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("name"), str)
        or not isinstance(data.get("description"), str)
    ):
        raise LabError("skill_format", "Skill 需要 name 与 description")
    if (
        not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", data["name"])
        or len(data["name"]) > 64
        or data["name"] != root.name
    ):
        raise LabError("skill_format", "Skill 名称须与目录名一致，使用小写字母、数字和连字符")
    if not 1 <= len(data["description"]) <= 1024 or not body.strip():
        raise LabError("skill_format", "Skill 描述或正文为空或过长")
    files = []
    total = 0
    for file in sorted(root.rglob("*")):
        if file.is_symlink():
            raise LabError("skill_path", "Skill 中包含符号链接")
        if file.is_file():
            if len(file.relative_to(root).parts) > 4:
                raise LabError("skill_path", "Skill 资源目录过深")
            total += file.stat().st_size
            if file.stat().st_size > 32000 or total > 128000:
                raise LabError("skill_size", "Skill 资源超过体积上限")
            files.append({"path": file.relative_to(root).as_posix(), "sha256": digest(file.read_bytes())})
    return {
        "name": data["name"],
        "description": data["description"],
        "sha256": digest(str(files)),
        "files": files,
    }


class Skills:
    def __init__(self, store: Store, run_id: str):
        self.store, self.run_id = store, run_id
        self.root = store.directory(run_id) / "skills"

    def snapshot(self, custom: Path | None = None):
        if self.store.get(self.run_id, "skills", "catalog") is not None:
            return
        candidates = {}
        for location in filter(None, (BUILTINS, custom)):
            if not location.is_dir() or location.is_symlink():
                raise LabError("skills_directory", "Skills 目录不存在或为符号链接")
            for folder in sorted(location.iterdir()):
                if folder.is_dir() and (folder / "SKILL.md").exists():
                    metadata = validate(folder)
                    metadata["source"] = "custom" if location == custom else "builtin"
                    if metadata["name"] in candidates:
                        self.store.event(self.run_id, "skill_override", {"name": metadata["name"]})
                    candidates[metadata["name"]] = (folder, metadata)
        if len(candidates) > 20:
            raise LabError("skills_limit", "当前任务最多加载 20 个 Skill 的目录元数据")
        catalog = []
        for name, (folder, metadata) in candidates.items():
            shutil.copytree(folder, self.root / name, dirs_exist_ok=True)
            catalog.append(metadata)
        self.store.put(self.run_id, "skills", "catalog", catalog)

    def catalog(self) -> list:
        if self.store.run(self.run_id)["config"].get("skills", True) is False:
            return []
        return self.store.get(self.run_id, "skills", "catalog", [])

    def activate(self, name: str, reason: str) -> dict:
        entry = next((item for item in self.catalog() if item["name"] == name), None)
        if not entry:
            raise LabError("skill_not_found", "当前任务没有该 Skill")
        metadata = validate(self.root / name)
        if metadata["sha256"] != entry["sha256"]:
            raise LabError("skill_changed", "任务 Skill 快照内容已变化")
        active = {**entry, "reason": reason[:500]}
        self.store.put(self.run_id, "active_skills", name, active)
        self.store.event(
            self.run_id, "skill_activation", {"name": name, "sha256": entry["sha256"], "reason": reason[:500]}
        )
        return {**active, "instructions": (self.root / name / "SKILL.md").read_text()}

    def resource(self, name: str, path: str) -> str:
        if not self.store.get(self.run_id, "active_skills", name):
            raise LabError("skill_inactive", "请先激活 Skill")
        entry = next(item for item in self.catalog() if item["name"] == name)
        if validate(self.root / name)["sha256"] != entry["sha256"]:
            raise LabError("skill_changed", "任务 Skill 快照内容已变化")
        file = bounded_path(self.root / name, path)
        if not file.is_file():
            raise LabError("not_found", "Skill 资源不存在")
        return file.read_text()
