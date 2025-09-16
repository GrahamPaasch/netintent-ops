"""Pydantic models and enums used by the API and worker components."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class IntentFormat(str, Enum):
    """Supported formats for incoming intent payloads."""

    json = "json"
    yaml = "yaml"


class RunType(str, Enum):
    """Run types tracked by the platform."""

    plan = "plan"
    apply = "apply"


class RunStatus(str, Enum):
    """Lifecycle of a run entry."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class ArtifactMetadata(BaseModel):
    """Lightweight reference to an artifact produced by runner jobs."""

    name: str
    path: str
    description: Optional[str] = None


class PlanRequest(BaseModel):
    """Incoming request payload for the /plans endpoint."""

    intent: Union[Dict[str, Any], str] = Field(
        ..., description="Desired state in JSON object form or serialized YAML"
    )
    intent_format: IntentFormat = Field(
        default=IntentFormat.yaml,
        description="Format hint when intent is provided as a string",
    )
    environment: str = Field(default="lab", description="Inventory environment key")
    template_set: str = Field(
        default="base", description="Template/role bundle to render and execute"
    )
    run_tags: Optional[List[str]] = Field(
        default=None, description="Optional Ansible --tags to narrow execution"
    )
    enable_vault: bool = Field(
        default=False,
        description="Toggle community.hashi_vault demo lookup inside the role",
    )


class PlanResponse(BaseModel):
    """Response body for plan submission."""

    plan_id: UUID


class RunSummary(BaseModel):
    """Aggregated details of a run."""

    status: RunStatus
    message: Optional[str] = None
    diff: Optional[str] = None


class RunStatusResponse(BaseModel):
    """Response model for run status lookups."""

    id: UUID
    run_type: RunType
    status: RunStatus
    environment: str
    template_set: str
    created_at: datetime
    updated_at: datetime
    summary: Optional[RunSummary] = None
    artifacts: List[ArtifactMetadata] = Field(default_factory=list)
    intent_path: Optional[str] = None


class RunRecord(BaseModel):
    """Internal representation of persisted runs."""

    id: UUID
    run_type: RunType
    status: RunStatus
    environment: str
    template_set: str
    intent: Dict[str, Any]
    artifacts_dir: str
    created_at: datetime
    updated_at: datetime
    enable_vault: bool = False
