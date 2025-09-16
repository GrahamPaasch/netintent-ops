# netintent-ops

NetIntent Ops is a lean network-intent automation platform that keeps Git as the source of truth and orchestrates Ansible execution environments through ansible-runner. The first iteration focuses on a self-hosted workflow inspired by _Automate Your Network_: FastAPI for the control plane, a lightweight worker for asynchronous plan/apply jobs, PostgreSQL metadata storage, and deterministic Execution Environments for every Ansible run.

## What is included
- FastAPI service with `/healthz`, `/plans`, and `/runs/{id}` endpoints
- Worker process that consumes pending plan/apply jobs and wraps `ansible_runner`
- Opinionated repository layout for intent YAML, inventories, playbooks, and roles
- Execution Environment definition for `ansible-builder`
- GitLab CI pipeline covering lint, Molecule, plan, review gate, apply, and post-validate stages
- Docker Compose stack with API, worker, and PostgreSQL
- Pre-commit hooks (yamllint, ansible-lint, trailing whitespace, EOF)

## Quick start
```bash
git clone <repo>
cd netintent-ops
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install .[dev]
pre-commit install
make ee  # build the execution environment image via ansible-builder
docker compose up --build -d
```

Once the containers are running, submit a plan for the sample intent:

```bash
curl -X POST "http://localhost:8000/plans"   -H "Content-Type: application/json"   -d @docs/sample_plan_request.json
```

The response includes a `plan_id`. Track its execution:

```bash
curl http://localhost:8000/runs/<plan_id>
```

Artifacts (intent snapshot, rendered configuration, Ansible stdout, documentation) are written to `artifacts/<plan_id>/` and persisted for audit.

## Local tooling
- `make lint`: run pre-commit hooks on the entire tree.
- `make molecule`: execute `molecule test` for `roles/base`.
- `make plan ENV=lab`: execute the plan playbook against the selected inventory via ansible-runner using the EE image.
- `make apply ENV=lab`: run the apply playbook (requires manual approval in CI/CD).

## Repository layout
```
api/                FastAPI application and orchestration helpers
worker/             Worker process that drives ansible-runner jobs
ansible/            Inventories, group/host vars, roles, playbooks, templates
infra/              Container build assets and database bootstrap SQL
docs/               Architecture notes, runbooks, and intent examples
tests/molecule/     Molecule scenarios (base role in v1)
```

## Vault integration
A demonstration Vault lookup is included in `roles/base/tasks/main.yml`. Enable it by setting `base_enable_vault_demo: true` in your inventory and providing `VAULT_ADDR`/`VAULT_TOKEN` at runtime. No secrets are stored in the repository.

## Next steps
- Hook GitLab runner(s) to honor `.gitlab-ci.yml`
- Integrate a message queue (e.g., Redis) for horizontally scaled workers
- Extend validation playbook with device-specific assertions (NAPALM)
- Add S3-compatible artifact offloading once MinIO or similar storage is available
