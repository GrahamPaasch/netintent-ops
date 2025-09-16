# Architecture Overview

NetIntent Ops separates intent management, execution, and validation into discrete components:

- **API** (`api/app.py`) accepts plan requests, captures metadata, and exposes artifact locations. FastAPI provides type-checked request/response models through Pydantic.
- **Worker** (`worker/worker.py`) polls for pending runs, drives ansible-runner using container process isolation, and updates run status.
- **Execution Environment** (`infra/ansible-builder/execution-environment.yml`) guarantees a deterministic Ansible runtime aligned with AWX/AAP best practices.
- **Infrastructure services** run via Docker Compose: PostgreSQL for metadata and API/worker containers that share the repository content.
- **Ansible control content** lives under `ansible/`, following the Git-as-source-of-truth model with inventories, group/host variables, roles, and playbooks.
- **Artifacts** (intent snapshot, rendered configs, documentation, evidence) are written per run under `artifacts/<run_id>/` and surfaced through the API for audit.

The GitLab CI pipeline builds the execution environment, enforces linting/testing gates, and structures plan/apply stages with manual approvals and evidence capture.
