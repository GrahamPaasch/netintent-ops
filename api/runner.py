"""Runner integration that wraps ansible-runner with Execution Environment settings."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import ansible_runner
import yaml

from .models import ArtifactMetadata, RunRecord, RunStatus
from .storage import Storage


@dataclass
class RunnerSettings:
    """Settings controlling how ansible-runner is invoked."""

    private_data_dir: Path
    project_dir: Path
    artifact_dir: Path
    ee_image: str
    container_engine: str

    @classmethod
    def from_env(cls) -> "RunnerSettings":
        base_dir = Path(os.getenv("NETINTENT_ROOT", Path(__file__).resolve().parents[1]))
        default_private = base_dir / ".runner"
        default_project = base_dir / "ansible"
        default_artifacts = base_dir / "artifacts"
        private_data_dir = Path(os.getenv("RUNNER_PRIVATE_DATA_DIR", str(default_private)))
        project_dir = Path(os.getenv("RUNNER_PROJECT_DIR", str(default_project)))
        artifact_dir = Path(os.getenv("ARTIFACTS_DIR", str(default_artifacts)))
        ee_image = os.getenv("RUNNER_EE_IMAGE", "netintent-ops-ee:latest")
        container_engine = os.getenv("RUNNER_CONTAINER_ENGINE", "docker")
        private_data_dir.mkdir(parents=True, exist_ok=True)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        project_dir.mkdir(parents=True, exist_ok=True)
        return cls(private_data_dir, project_dir, artifact_dir, ee_image, container_engine)


@dataclass
class RunnerResult:
    """Outcome of a runner invocation."""

    status: RunStatus
    rc: int
    summary: str
    diff: str
    artifacts: List[ArtifactMetadata]


class AnsibleRunnerService:
    """Encapsulates ansible-runner interactions for plan/apply flows."""

    def __init__(self, storage: Storage, settings: RunnerSettings | None = None) -> None:
        self.storage = storage
        self.settings = settings or RunnerSettings.from_env()

    def run_plan(self, record: RunRecord) -> RunnerResult:
        """Execute the plan playbook with --check/--diff enabled."""
        run_dir = self._prepare_run_dir(record)
        ident = str(record.id)
        extravars = self._build_extravars(record, run_dir, mode="plan")
        runner = ansible_runner.run(
            private_data_dir=str(self.settings.private_data_dir),
            project_dir=str(self.settings.project_dir),
            playbook="playbooks/plan.yml",
            inventory=self._inventory_path(record.environment),
            envvars={
                "ANSIBLE_CONFIG": str(self.settings.project_dir / "ansible.cfg"),
                "NETINTENT_RUN_ID": ident,
            },
            extravars=extravars,
            ident=ident,
            artifact_dir=str(self.settings.artifact_dir),
            cmdline="--diff --check",
            process_isolation=True,
            container_engine=self.settings.container_engine,
            container_image=self.settings.ee_image,
        )
        summary, diff = self._collect_summary(ident)
        artifacts = self._collect_artifacts(record.artifacts_dir)
        status = RunStatus.completed if runner.rc == 0 else RunStatus.failed
        return RunnerResult(status=status, rc=runner.rc, summary=summary, diff=diff, artifacts=artifacts)

    def run_apply(self, record: RunRecord) -> RunnerResult:
        """Execute the apply playbook."""
        run_dir = self._prepare_run_dir(record)
        ident = str(record.id)
        extravars = self._build_extravars(record, run_dir, mode="apply")
        runner = ansible_runner.run(
            private_data_dir=str(self.settings.private_data_dir),
            project_dir=str(self.settings.project_dir),
            playbook="playbooks/apply.yml",
            inventory=self._inventory_path(record.environment),
            envvars={
                "ANSIBLE_CONFIG": str(self.settings.project_dir / "ansible.cfg"),
                "NETINTENT_RUN_ID": ident,
            },
            extravars=extravars,
            ident=ident,
            artifact_dir=str(self.settings.artifact_dir),
            process_isolation=True,
            container_engine=self.settings.container_engine,
            container_image=self.settings.ee_image,
        )
        summary, diff = self._collect_summary(ident)
        artifacts = self._collect_artifacts(record.artifacts_dir)
        status = RunStatus.completed if runner.rc == 0 else RunStatus.failed
        return RunnerResult(status=status, rc=runner.rc, summary=summary, diff=diff, artifacts=artifacts)

    def _prepare_run_dir(self, record: RunRecord) -> Path:
        run_dir = Path(record.artifacts_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        intent_path = run_dir / "intent.yaml"
        with intent_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(record.intent, handle, sort_keys=True)
        return run_dir

    def _inventory_path(self, environment: str) -> str:
        inventory = self.settings.project_dir / "inventories" / environment / "hosts.yml"
        if not inventory.exists():
            raise FileNotFoundError(f"Inventory not found for environment '{environment}'")
        return str(inventory)

    def _build_extravars(self, record: RunRecord, run_dir: Path, mode: str) -> Dict[str, object]:
        docs_dir = run_dir / "docs"
        docs_dir.mkdir(exist_ok=True)
        rendered_dir = run_dir / "rendered"
        rendered_dir.mkdir(exist_ok=True)
        evidence_dir = run_dir / "evidence"
        evidence_dir.mkdir(exist_ok=True)
        return {
            "netintent_intent": record.intent,
            "netintent_artifacts_dir": str(run_dir),
            "netintent_run_mode": mode,
            "netintent_render_dir": str(rendered_dir),
            "netintent_docs_dir": str(docs_dir),
            "netintent_evidence_dir": str(evidence_dir),
            "netintent_enable_vault_demo": record.enable_vault,
        }

    def _collect_summary(self, ident: str) -> tuple[str, str]:
        stdout_file = self.settings.artifact_dir / ident / "stdout"
        summary = stdout_file.read_text(encoding="utf-8") if stdout_file.exists() else ""
        stats_file = self.settings.artifact_dir / ident / "job_events" / "summary.json"
        diff_summary = ""
        if stats_file.exists():
            try:
                data = json.loads(stats_file.read_text(encoding="utf-8"))
                diff_summary = json.dumps(data, indent=2)
            except json.JSONDecodeError:
                diff_summary = ""
        return summary, diff_summary

    def _collect_artifacts(self, path: str) -> List[ArtifactMetadata]:
        artifacts: List[ArtifactMetadata] = []
        base = Path(path)
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
