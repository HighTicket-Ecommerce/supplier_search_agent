import time

from backend.job_store import get_job, update_job


class JobStopped(Exception):
    pass


class LimitReached(Exception):
    pass


class ResearchContext:
    def __init__(self, job_id, request):
        self.job_id = job_id
        self.request = request
        self.started = time.monotonic()
        self.pages = 0
        self.calls = 0
        self.exposure = 0.0
        self.operations = []
        self.catalogues = {}
        self.website_pages = {}
        self.fetch_failures = []

    def checkpoint(self):
        job = get_job(self.job_id)
        if job and job["status"] == "stopped":
            raise JobStopped("Stopped by user")
        if self.remaining_seconds() <= 0:
            raise LimitReached("runtime_limit")

    def remaining_seconds(self):
        return self.request.max_runtime_seconds - (time.monotonic() - self.started)

    def snapshot(self):
        update_job(self.job_id, limits={"pages": self.pages, "external_calls": self.calls,
                   "reserved_execution_usd": round(self.exposure, 6),
                   "max_execution_cost_usd": self.request.max_execution_cost_usd}, operations=self.operations)

    def take_page(self):
        self.checkpoint()
        if self.pages >= self.request.max_pages:
            raise LimitReached("page_limit")
        self.pages += 1
        self.snapshot()

    def reserve(self, kind, maximum_usd, **metadata):
        self.checkpoint()
        if self.calls >= self.request.max_external_calls:
            raise LimitReached("external_call_limit")
        if self.exposure + maximum_usd > self.request.max_execution_cost_usd + 1e-9:
            raise LimitReached("execution_budget_limit")
        self.calls += 1
        self.exposure += maximum_usd
        operation = {"kind": kind, "reserved_usd": maximum_usd, "status": "reserved", **metadata}
        self.operations.append(operation)
        self.snapshot()
        return operation

    def record(self, operation, **metadata):
        operation.update(metadata)
        self.snapshot()

    def save_catalogue(self, url, catalogue):
        self.catalogues[url] = catalogue
        update_job(self.job_id, catalogues=self.catalogues)

    def settle_model(self, operation, cost_usd):
        # Actor billing may lag, so its maximum remains reserved throughout a job.
        self.exposure += cost_usd - operation["reserved_usd"]
        self.record(operation, estimated_cost_usd=cost_usd, status="completed")
