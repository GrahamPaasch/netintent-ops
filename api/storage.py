"""Minimal persistence layer for plan/apply metadata."""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, String, Text, create_engine
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .models import ArtifactMetadata, IntentFormat, PlanRequest, RunRecord, RunStatus, RunSummary, RunType

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://netintent:netintent@localhost:5432/netintent",
)

Base = declarative_base()


class RunModel(Base):
    """SQLAlchemy ORM model for tracked runs."""

    __tablename__ = "runs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_type = Column(Enum(RunType), nullable=False, default=RunType.plan)
    status = Column(Enum(RunStatus), nullable=False, default=RunStatus.pending)
    environment = Column(String, nullable=False)
    template_set = Column(String, nullable=False)
    intent = Column(JSON, nullable=False)
    intent_format = Column(Enum(IntentFormat), nullable=False)
    artifacts_dir = Column(String, nullable=False)
    summary = Column(Text)
    diff = Column(Text)
    last_error = Column(Text)
    enable_vault = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


@dataclass
class Storage:
    """Simple storage helper wrapping SQLAlchemy sessions."""

    engine_url: str = DATABASE_URL

    def __post_init__(self) -> None:
        self.engine = create_engine(self.engine_url, future=True)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    def initialize(self) -> None:
        """Create database tables if they do not exist."""
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session_scope(self) -> Session:
        session: Session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def create_run(self, request: PlanRequest, artifacts_dir: str) -> UUID:
        """Persist a run entry and return its identifier."""
        run_id = uuid4()
        model = RunModel(
            id=run_id,
            run_type=RunType.plan,
            status=RunStatus.pending,
            environment=request.environment,
            template_set=request.template_set,
            intent=_normalize_intent(request.intent, request.intent_format),
            intent_format=request.intent_format,
            artifacts_dir=str(Path(artifacts_dir) / str(run_id)),
            enable_vault=request.enable_vault,
        )
        with self.session_scope() as session:
            session.add(model)
        return run_id

    def update_status(
        self,
        run_id: UUID,
        status: RunStatus,
        summary: Optional[str] = None,
        diff: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update lifecycle metadata for a run."""
        with self.session_scope() as session:
            run = session.get(RunModel, run_id)
            if not run:
                raise KeyError(f"Run {run_id} not found")
            run.status = status
            run.summary = summary
            run.diff = diff
            run.last_error = error

    def get_run(self, run_id: UUID) -> Optional[RunRecord]:
        """Fetch a stored run."""
        with self.session_scope() as session:
            run = session.get(RunModel, run_id)
            if not run:
                return None
            return RunRecord(
                id=run.id,
                run_type=run.run_type,
                status=run.status,
                environment=run.environment,
                template_set=run.template_set,
                intent=run.intent,
                artifacts_dir=run.artifacts_dir,
                created_at=run.created_at,
                updated_at=run.updated_at,
                enable_vault=bool(run.enable_vault),
            )

    def describe_run(self, run_id: UUID) -> Optional[Dict[str, object]]:
        """Return API-friendly details for the requested run."""
        with self.session_scope() as session:
            run = session.get(RunModel, run_id)
            if not run:
                return None
            artifacts = _artifact_listing(run.artifacts_dir)
            summary = RunSummary(
                status=run.status,
                message=run.summary,
                diff=run.diff,
            )
            return {
                "id": run.id,
                "run_type": run.run_type,
                "status": run.status,
                "environment": run.environment,
                "template_set": run.template_set,
                "created_at": run.created_at,
                "updated_at": run.updated_at,
                "summary": summary,
                "artifacts": artifacts,
                "intent_path": str(Path(run.artifacts_dir) / "intent.yaml"),
            }

    def next_pending(self) -> Optional[RunRecord]:
        """Return the next pending plan run (FIFO order)."""
        with self.session_scope() as session:
            run = (
                session.query(RunModel)
                .filter(RunModel.status == RunStatus.pending)
                .order_by(RunModel.created_at.asc())
                .first()
            )
            if not run:
                return None
            run.status = RunStatus.running
            session.add(run)
            return RunRecord(
                id=run.id,
                run_type=run.run_type,
                status=RunStatus.running,
                environment=run.environment,
                template_set=run.template_set,
                intent=run.intent,
                artifacts_dir=run.artifacts_dir,
                created_at=run.created_at,
                updated_at=run.updated_at,
                enable_vault=bool(run.enable_vault),
            )


def _normalize_intent(intent: object, fmt: IntentFormat) -> Dict[str, object]:
    """Convert the provided intent payload into a dictionary."""
    if isinstance(intent, dict):
        return intent
    if isinstance(intent, str):
        if fmt == IntentFormat.yaml:
            import yaml

            return yaml.safe_load(intent) or {}
        return json.loads(intent)
    raise TypeError("Intent payload must be a dict or YAML/JSON string")


def _artifact_listing(path: str) -> List[ArtifactMetadata]:
    base = Path(path)
    artifacts: List[ArtifactMetadata] = []
    if not base.exists():
        return artifacts
    for item in base.rglob("*"):
        if item.is_file():
            artifacts.append(
                ArtifactMetadata(
                    name=item.name,
                    path=str(item),
                    description=None,
                )
            )
    return artifacts


def get_storage() -> Storage:
    """Factory used by API and worker modules."""
    storage = Storage()
    storage.initialize()
    return storage
