https://github.com/GrahamPaasch/automate_your_network/blob/main/Automate%20Your%20Network%20-%20John%20Capobianco%20-%20Paperback.pdf

Why (evidence): This matches the textbook’s core principles—Git as the gatekeeper, YAML/Jinja for intent, CI gates with approvals, dry‑run+diff, and auditable evidence—while replacing TFS with a modern, free stack.

Best‑option choices (I choose for you)
1) SCM + CI/CD (replace TFS/Azure DevOps)

GitLab Community Edition (self‑managed): mature, integrated CI/CD via .gitlab-ci.yml, merge‑request gating, environments, and protected variables—all in the Free tier and for self‑hosted installs. 
GitLab Docs

Rationale vs TFS: The book uses TFS/Azure DevOps for PRs/builds; GitLab CE gives those capabilities without licensing complexity and keeps everything on‑prem.

Pipeline gates you will enforce:

Lint (YAML + Ansible), unit/Molecule tests.

Plan: ansible-runner check + diff with device‑safe scoping.

Manual approval (MR gate) → Apply stage → Post‑validate with show‑command parsing/NAPALM facts.

Artifacts: diffs, evidence, run logs, intent docs.

2) Execution engine for Ansible

ansible-runner as the programmatic interface to run Ansible jobs; it’s designed as a stable abstraction and underpins AWX’s execution. 
PyPI
+1

Execution Environments (EEs) to guarantee reproducible runs (the same containerized env you’d use in AWX), built with ansible‑builder and invoked by Runner. 
ansible.readthedocs.io

3) Secrets management

HashiCorp Vault via the community.hashi_vault lookups (vault_kv2_get / vault_read) for pulling credentials/keys at runtime—no secrets in Git. 
Ansible Documentation
+2
Ansible Documentation
+2

Book alignment: central secrets store (Vault/KeyVault) was recommended.

4) Network automation content

Ansible network collections as first choice (idempotent modules, network_cli/netconf): ansible.netcommon + vendor collections (Cisco/Arista/Juniper, etc.). 
Ansible Documentation

Evidence capture: ansible.netcommon.cli_command for “show” commands; parse with cli_parse/TextFSM/TTP; store before/after in artifacts. 
Ansible Documentation

Optional state validation: NAPALM for multi‑vendor facts/state checks. 
PyPI

5) Dry‑run and diffs (non‑negotiable)

Check mode + diff as default for “Plan” stage; only after approval do we “Apply”. (Core Ansible guidance.) 
Ansible Documentation

Mirrors the book’s “idempotency + check/diff” requirement.

6) Testing, linting, and quality gates

molecule for role/playbook/collection testing; ansible‑lint for best‑practice enforcement; yamllint for YAML hygiene; pre‑commit to block bad commits locally. 
GitHub
+3
ansible.readthedocs.io
+3
ansible.readthedocs.io
+3

Book mandates automated checks and reproducibility; this stack institutionalizes it.

7) API, worker, and UI

Backend: Python FastAPI + Pydantic for schemas (intent models & validation). 
FastAPI

Workers: a simple queue that launches ansible‑runner with EE (containerized), capturing event streams and artifacts. (Runner is designed for embedding into CI/other systems.) 
PyPI

UI: thin React view later; start with GitLab MR UI for reviews and diffs to reduce initial surface area.

Storage: Git as SoT (YAML + Jinja), Postgres for run metadata, and (optional) S3‑compatible object storage (e.g., MinIO) for large artifacts.

8) Data model, inventories, docs

YAML source‑of‑truth under group_vars/ & host_vars/, with environment overlays (lab/staging/prod). Templates in Jinja2. Generate intent documentation (Markdown) from the same data.

Branching: main = prod; feature branches → MRs; tags for releases.

RBAC: reviewers/approvers distinct from authors; approvals required; protected branches/runners.

How this maps 1:1 to the textbook

Git as Source‑of‑Truth; YAML + Jinja templates → rendered configs; desired state defined in data; runbooks generate configs and push via controlled pipeline.

PR review + CI gates in MR (lint/tests/plan) with approvals → Apply only after sign‑off.

Check + Diff and pre/post evidence captured for auditability.

Avoid ad‑hoc scripts; use standard modules/collections.

Repository name

Use netintent-ops (lowercase, hyphenated). Purpose‑revealing and unlikely to conflict.
