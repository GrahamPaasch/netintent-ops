"""Simple polling worker that picks up pending runs and executes them."""
from __future__ import annotations

import logging
import os
import time

from tenacity import Retrying, stop_after_attempt, wait_fixed

from api.models import RunStatus
from api.runner import AnsibleRunnerService
from api.storage import Storage, get_storage

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))


class Worker:
    """Background worker that executes plan/apply jobs."""

    def __init__(self, storage: Storage, runner: AnsibleRunnerService) -> None:
        self.storage = storage
        self.runner = runner

    def run_forever(self) -> None:
        """Main loop; polls for pending runs."""
        logger.info("Worker started with poll interval %ss", POLL_INTERVAL)
        while True:
            record = self.storage.next_pending()
            if not record:
                time.sleep(POLL_INTERVAL)
                continue
            logger.info("Processing run %s (env=%s)", record.id, record.environment)
            try:
                result = self.runner.run_plan(record)
                self.storage.update_status(
                    record.id,
                    result.status,
                    summary=result.summary,
                    diff=result.diff,
                )
                logger.info("Run %s completed rc=%s", record.id, result.rc)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Run %s failed", record.id)
                self.storage.update_status(record.id, RunStatus.failed, error=str(exc))


def _init_components() -> tuple[Storage, AnsibleRunnerService]:
    storage = get_storage()
    runner = AnsibleRunnerService(storage)
    return storage, runner


def main() -> None:
    for attempt in Retrying(stop=stop_after_attempt(5), wait=wait_fixed(3)):
        with attempt:
            storage, runner = _init_components()
    worker = Worker(storage, runner)
    worker.run_forever()


if __name__ == "__main__":
    main()
