"""Durable task state and a transactionally reserved, shared CNY budget."""

import fcntl
import json
import math
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from reprolab.core import LabError, Settings, atomic_write, digest, now, redact


class Store:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.home = self.settings.home
        self.home.mkdir(parents=True, exist_ok=True)
        self.home.chmod(0o700)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, created TEXT, status TEXT, request TEXT,
                    spec TEXT, config TEXT, elapsed REAL DEFAULT 0, stop_reason TEXT DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS objects (
                    run_id TEXT, kind TEXT, key TEXT, value TEXT,
                    PRIMARY KEY(run_id,kind,key)
                );
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, at TEXT,
                    kind TEXT, value TEXT
                );
                CREATE TABLE IF NOT EXISTS ledger (
                    id TEXT PRIMARY KEY, run_id TEXT, at TEXT, state TEXT,
                    model TEXT, input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0,
                    cost_micro INTEGER, reserved_micro INTEGER
                );
                CREATE TABLE IF NOT EXISTS experiences (
                    id TEXT PRIMARY KEY, repository TEXT, commit_sha TEXT, namespace TEXT,
                    value TEXT, created TEXT
                );
            """)

    def connect(self):
        db = sqlite3.connect(self.home / "state.sqlite", timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        return db

    def directory(self, run_id: str) -> Path:
        if not run_id.isalnum() or len(run_id) != 12:
            raise LabError("run_id", "任务 ID 无效")
        return self.home / "runs" / run_id

    def create(self, request: str, spec: dict, config: dict | None = None) -> str:
        run_id = uuid.uuid4().hex[:12]
        self.directory(run_id).mkdir(parents=True, mode=0o700)
        with self.connect() as db:
            db.execute(
                "INSERT INTO runs(id,created,status,request,spec,config) VALUES(?,?,?,?,?,?)",
                (run_id, now(), "prepared", redact(request), json.dumps(spec), json.dumps(config or {})),
            )
        self.event(run_id, "created", {"repository": spec["repository"], "commit": spec["buggy"]})
        return run_id

    def run(self, run_id: str) -> dict:
        self.directory(run_id)
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise LabError("not_found", "任务不存在")
        value = dict(row)
        for key in ("spec", "config"):
            value[key] = json.loads(value[key])
        return value

    def update(self, run_id: str, **values):
        if not values or not set(values) <= {"status", "elapsed", "stop_reason"}:
            raise ValueError("unsupported task fields")
        with self.connect() as db:
            db.execute(
                "UPDATE runs SET " + ",".join(key + "=?" for key in values) + " WHERE id=?",
                (*values.values(), run_id),
            )

    def put(self, run_id: str, kind: str, key: str, value):
        serialized = redact(json.dumps(value, ensure_ascii=False))
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO objects VALUES(?,?,?,?)", (run_id, kind, key, serialized))

    def get(self, run_id: str, kind: str, key: str, default=None):
        with self.connect() as db:
            row = db.execute(
                "SELECT value FROM objects WHERE run_id=? AND kind=? AND key=?", (run_id, kind, key)
            ).fetchone()
        return json.loads(row[0]) if row else default

    def objects(self, run_id: str, kind: str) -> list:
        with self.connect() as db:
            rows = db.execute(
                "SELECT value FROM objects WHERE run_id=? AND kind=? ORDER BY key", (run_id, kind)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def event(self, run_id: str, kind: str, value: dict):
        with self.connect() as db:
            db.execute(
                "INSERT INTO events(run_id,at,kind,value) VALUES(?,?,?,?)",
                (run_id, now(), kind, redact(json.dumps(value, ensure_ascii=False))),
            )

    def events(self, run_id: str) -> list:
        with self.connect() as db:
            rows = db.execute("SELECT seq,at,kind,value FROM events WHERE run_id=? ORDER BY seq", (run_id,))
            return [{**dict(row), "value": json.loads(row["value"])} for row in rows]

    @contextmanager
    def lock(self, run_id: str, filename: str = "run.lock"):
        with (self.directory(run_id) / filename).open("w") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise LabError("busy", "该任务已有执行进程") from exc
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def artifact(self, run_id: str, content: str, category: str) -> dict:
        content = redact(content)
        key = "ar-" + digest(category + "\0" + content)[:20]
        atomic_write(self.directory(run_id) / "artifacts" / (key + ".txt"), content)
        metadata = {
            "id": key,
            "category": category,
            "sha256": digest(content),
            "bytes": len(content.encode()),
        }
        self.put(run_id, "artifacts", key, metadata)
        return metadata

    def read_artifact(self, run_id: str, artifact_id: str) -> str:
        if self.get(run_id, "artifacts", artifact_id) is None:
            raise LabError("not_found", "当前任务没有该 artifact")
        return (self.directory(run_id) / "artifacts" / (artifact_id + ".txt")).read_text()

    def reserve(self, run_id: str, amount: int) -> str:
        ticket = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            unknown = db.execute(
                "SELECT COUNT(*) FROM ledger WHERE run_id=? AND state!='settled'", (run_id,)
            ).fetchone()[0]
            if unknown:
                raise LabError("unknown_usage", "该任务仍有用量未确认的调用，请保留费用记录")
            calls = db.execute("SELECT COUNT(*) FROM ledger WHERE run_id=?", (run_id,)).fetchone()[0]
            used = db.execute("SELECT COALESCE(SUM(cost_micro),0) FROM ledger").fetchone()[0]
            if calls >= self.settings.max_calls:
                raise LabError("call_limit", "模型调用次数达到上限")
            if used + amount > self.settings.budget_micro:
                raise LabError("budget", "累计费用与预留额度达到上限")
            db.execute(
                "INSERT INTO ledger(id,run_id,at,state,model,cost_micro,reserved_micro) VALUES(?,?,?,?,?,?,?)",
                (ticket, run_id, now(), "pending", self.settings.model, amount, amount),
            )
        return ticket

    def settle(self, ticket: str, usage: dict | None):
        with self.connect() as db:
            if usage is None:
                db.execute("UPDATE ledger SET state='unknown' WHERE id=?", (ticket,))
                return
            inputs, outputs = usage["input_tokens"], usage["output_tokens"]
            cost = math.ceil(inputs * 2.4 + outputs * 9.6)
            row = db.execute("SELECT reserved_micro FROM ledger WHERE id=?", (ticket,)).fetchone()
            if cost > row[0]:
                db.execute("UPDATE ledger SET state='unknown',cost_micro=? WHERE id=?", (cost, ticket))
            else:
                db.execute(
                    "UPDATE ledger SET state='settled',cost_micro=?,input_tokens=?,output_tokens=? WHERE id=?",
                    (cost, inputs, outputs, ticket),
                )

    def statistics(self, run_id: str) -> dict:
        with self.connect() as db:
            row = db.execute(
                "SELECT COUNT(*) calls,COALESCE(SUM(cost_micro),0) cost,COALESCE(SUM(input_tokens),0) inputs,COALESCE(SUM(output_tokens),0) outputs FROM ledger WHERE run_id=?",
                (run_id,),
            ).fetchone()
            total = db.execute("SELECT COALESCE(SUM(cost_micro),0) FROM ledger").fetchone()[0]
            unknown = db.execute("SELECT COUNT(*) FROM ledger WHERE state!='settled'").fetchone()[0]
        return {
            "model_calls": row["calls"],
            "input_tokens": row["inputs"],
            "output_tokens": row["outputs"],
            "estimated_cost_cny": row["cost"] / 1e6,
            "global_accounted_cny": total / 1e6,
            "global_unconfirmed_calls": unknown,
            "price_date": "2026-11-13",
            "input_cny_per_million": 2.4,
            "output_cny_per_million": 9.6,
            "usd_conversion": 8,
        }

    def remember(self, run_id: str):
        run = self.run(run_id)
        card = {
            "source_run": run_id,
            "skills": self.objects(run_id, "active_skills"),
            "hypotheses": self.objects(run_id, "hypotheses"),
            "actions": [event["value"]["tool"] for event in self.events(run_id) if event["kind"] == "tool"],
            "applicability": "仅适用于相同源码版本；实验仍需重新验证",
        }
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO experiences VALUES(?,?,?,?,?,?)",
                (
                    run_id,
                    run["spec"]["repository"],
                    run["spec"]["buggy"],
                    run["config"].get("namespace", "normal"),
                    json.dumps(card, ensure_ascii=False),
                    now(),
                ),
            )

    def experiences(self, run_id: str) -> list:
        run = self.run(run_id)
        with self.connect() as db:
            rows = db.execute(
                "SELECT value FROM experiences WHERE repository=? AND commit_sha=? AND namespace=? AND id!=? LIMIT 3",
                (
                    run["spec"]["repository"],
                    run["spec"]["buggy"],
                    run["config"].get("namespace", "normal"),
                    run_id,
                ),
            )
            return [json.loads(row[0]) for row in rows]
