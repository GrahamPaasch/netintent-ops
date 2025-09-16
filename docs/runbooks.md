# Runbooks

## Submit a plan locally
1. Build or pull the execution environment image: `make ee` (requires ansible-builder).
2. Start local services: `docker compose up --build -d`.
3. Post the sample plan request: `curl -X POST http://localhost:8000/plans -d @docs/sample_plan_request.json -H 'Content-Type: application/json'`.
4. Poll the status until `status` becomes `completed`: `curl http://localhost:8000/runs/<plan_id>`.
5. Review artifacts under `artifacts/<plan_id>/` for rendered templates, documentation, and evidence.

## Run Molecule tests
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .[dev]
molecule test -s base
```

## Trigger plan/apply via Makefile
- `make plan ENV=lab`
- `make apply ENV=lab`

Both commands rely on ansible-runner and the execution environment image. Set `EE_IMAGE` if the image tag differs.

## Enable Vault demo
1. Export `VAULT_ADDR` and `VAULT_TOKEN` for a dev instance.
2. Set `base_enable_vault_demo: true` inside the desired inventory or use `--extra-vars`.
3. Re-run the plan or apply; Vault-derived values will replace the banner footer.

## CI/CD expectations
- Merge requests must pass lint, tests, and plan stages before the manual review gate.
- Apply stage is protected and requires explicit approval.
- Validation playbook runs after apply and must succeed before the pipeline completes.
