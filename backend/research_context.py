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
        self.catalogue_results = {}
        self.catalogue_errors = {}
        self.website_pages = {}
        self.website_failures = {}
        self.fetch_failures = []
        self.discovery_candidates = []
        self.discovery_coverage = []

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

    def save_discovery_selection(self, records, coverage):
        batch_id = str(len(self.discovery_coverage) + 1)
        for entry in records:
            entry["record_id"] = batch_id + ":" + entry["record_id"]
            if "duplicate_of" in entry:
                entry["duplicate_of"] = batch_id + ":" + entry["duplicate_of"]
        self.discovery_candidates.extend(records)
        self.discovery_coverage.append(dict(coverage, batch_id=batch_id))
        self._save_discovery()

    def record_discovery_verification(self, item, status):
        record_id = item.get("record_id")
        if not record_id:
            return
        for entry in self.discovery_candidates:
            if entry["record_id"] == record_id:
                entry["verification_status"] = status
                self._save_discovery()
                break

    def finish_discovery(self, reason):
        for entry in self.discovery_candidates:
            if entry.get("verification_status") == "pending":
                entry.update(verification_status="not_checked", verification_stop_reason=reason)
        self._save_discovery()

    def _save_discovery(self):
        update_job(self.job_id, discovery_candidates=self.discovery_candidates,
                   discovery_coverage=self.discovery_coverage)

    def settle_model(self, operation, cost_usd):
        # Actor billing may lag, so its maximum remains reserved throughout a job.
        self.exposure += cost_usd - operation["reserved_usd"]
        self.record(operation, estimated_cost_usd=cost_usd, status="completed")
