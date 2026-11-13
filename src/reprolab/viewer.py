"""Loopback-only, read-only task and experiment viewer."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from reprolab.core import LabError
from reprolab.reporting import build_report
from reprolab.store import Store


def create_app(store: Store) -> FastAPI:
    app = FastAPI(title="ReproLab", docs_url=None, redoc_url=None, openapi_url=None)
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        with store.connect() as db:
            rows = [
                dict(row)
                for row in db.execute(
                    "SELECT id,created,status,request FROM runs ORDER BY created DESC LIMIT 100"
                )
            ]
        return templates.TemplateResponse(request=request, name="index.html", context={"runs": rows})

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    def task(request: Request, run_id: str):
        try:
            report = build_report(store, run_id)
        except LabError as exc:
            raise HTTPException(404, "任务不存在") from exc
        tests = store.directory(run_id) / "tests"
        files = [{"name": path.name, "content": path.read_text()} for path in sorted(tests.glob("test_*.py"))]
        return templates.TemplateResponse(
            request=request,
            name="task.html",
            context={"report": report, "events": store.events(run_id), "tests": files},
        )

    @app.get("/runs/{run_id}/artifacts/{artifact_id}", response_class=PlainTextResponse)
    def artifact(run_id: str, artifact_id: str):
        try:
            return store.read_artifact(run_id, artifact_id)
        except LabError as exc:
            raise HTTPException(404, "资料不存在") from exc

    @app.middleware("http")
    async def headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    return app
