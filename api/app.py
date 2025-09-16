"""FastAPI application exposing plan submission and run status endpoints."""
from __future__ import annotations

import logging
import os
from typing import Dict
from uuid import UUID

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import PlanRequest, PlanResponse, RunStatusResponse
from .runner import RunnerSettings
from .storage import Storage, get_storage

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(title="NetIntent Ops API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
)

storage: Storage = get_storage()


@app.on_event("startup")
def startup() -> None:
    storage.initialize()
    RunnerSettings.from_env()
    logger.info("Storage initialized")


@app.get("/healthz", response_model=Dict[str, str])
def healthcheck() -> Dict[str, str]:
    """Health endpoint for liveness probes."""
    return {"status": "ok"}


@app.post("/plans", response_model=PlanResponse, status_code=202)
def submit_plan(request: PlanRequest, background_tasks: BackgroundTasks) -> PlanResponse:
    """Accept an intent payload and enqueue a plan run."""
    artifacts_root = os.getenv("ARTIFACTS_DIR", "/app/artifacts")
    run_id = storage.create_run(request, artifacts_root)
    logger.info(
        "Plan %s created for env=%s template=%s",
        run_id,
        request.environment,
        request.template_set,
    )
    background_tasks.add_task(_trigger_worker_handoff)
    return PlanResponse(plan_id=run_id)


@app.get("/runs/{run_id}", response_model=RunStatusResponse)
def get_run(run_id: UUID) -> RunStatusResponse:
    """Return current state of a plan/apply run."""
    data = storage.describe_run(run_id)
    if not data:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunStatusResponse(
        id=data["id"],
        run_type=data["run_type"],
        status=data["status"],
        environment=data["environment"],
        template_set=data["template_set"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        summary=data["summary"],
        artifacts=data["artifacts"],
        intent_path=data["intent_path"],
    )


def _trigger_worker_handoff() -> None:
    """No-op hook to ensure the worker is nudged."""
    logger.debug("Worker handoff triggered")
