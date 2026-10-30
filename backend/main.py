import hmac
import uuid
import csv
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.datastructures import Headers

from backend import config
from backend.models import ResearchRequest
from backend.job_store import (init_job, get_job, update_job, recover_interrupted_jobs,
                               claim_export, finish_export)
from backend.research_runner import run_research_job
from backend.sheets import append_supplier_row
from backend.master_index import import_reference, list_references, load_reference


@asynccontextmanager
async def lifespan(app):
    recover_interrupted_jobs()
    yield


PUBLIC_PATHS = {"/health"}


class RequireApiKey:
    """Rejects requests without the shared API key before routing or body parsing."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Use the raw ASGI path: request.url is rebuilt from client-controlled headers.
        if scope["type"] != "http" or scope["path"] in PUBLIC_PATHS:
            return await self.app(scope, receive, send)
        expected = config.SUPPLIER_API_KEY
        supplied = Headers(scope=scope).get("x-api-key", "")
        if not expected:
            response = JSONResponse({"detail": "SUPPLIER_API_KEY is not configured on the backend"}, 503)
        elif not hmac.compare_digest(supplied.encode(), expected.encode()):
            response = JSONResponse({"detail": "Missing or invalid API key"}, 401)
        else:
            return await self.app(scope, receive, send)
        await response(scope, receive, send)


app = FastAPI(title="Supplier Research Agent", lifespan=lifespan)
app.add_middleware(RequireApiKey)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    # NaN/Infinity in invalid JSON must not break serialization of the 422 response.
    return JSONResponse(status_code=422, content={"detail": [
        {"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()
    ]})


@app.get("/health")
def health_check():
    return {"openai_key_set": bool(config.OPENAI_API_KEY), "openai_model": config.OPENAI_MODEL,
            "apify_token_set": bool(config.APIFY_TOKEN)}


@app.post("/research/start")
def start_research(req: ResearchRequest, background_tasks: BackgroundTasks):
    if req.master_reference_id:
        try:
            load_reference(req.master_reference_id)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
    job_id = str(uuid.uuid4())
    init_job(job_id, req.model_dump())
    background_tasks.add_task(run_research_job, job_id, req)
    return {"job_id": job_id, "status": "queued", "preview_only": req.preview_only}


@app.get("/research/status/{job_id}")
def research_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    total = job.get("total", 0)
    return {"status": job["status"], "processed": job["processed"], "total": total,
            "progress_pct": round(job["processed"] / total * 100, 1) if total else 0,
            "accepted_count": len(job["accepted"]), "review_count": len(job["review"]),
            "rejected_count": len(job["rejected"]), "observation_count": len(job.get("observations", [])), "target_suppliers": job.get("target_suppliers", 0),
            "error": job.get("error"), "limit_reason": job.get("limit_reason"), "limits": job["limits"]}


@app.post("/research/stop/{job_id}")
def stop_research(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] in {"queued", "running"}:
        update_job(job_id, status="stopped")
    return {"status": get_job(job_id)["status"]}


@app.get("/research/result/{job_id}")
def research_result(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {"job_id": job_id, "status": job["status"], "accepted": job["accepted"],
            "review": job["review"], "rejected": job["rejected"],
            "accepted_count": len(job["accepted"]), "review_count": len(job["review"]),
            "rejected_count": len(job["rejected"]), "preview_only": job["request"].get("preview_only", True),
            "limits": job["limits"], "operations": job["operations"], "exports": job["exports"], "error": job.get("error"),
            "limit_reason": job.get("limit_reason"), "research_mode": job["request"].get("research_mode", "supplier_search"),
            "observations": job.get("observations", []), "directory_coverage": job.get("directory_coverage", []),
            "warnings": job.get("warnings", []), "master_reference": job.get("master_reference"), "catalogues": job.get("catalogues", {})}


class ReferenceRequest(BaseModel):
    filename: str = Field(default="suppliers.csv", max_length=200)
    csv_content: str = Field(min_length=1, max_length=15_000_000)


@app.post("/references/master")
def add_master_reference(req: ReferenceRequest):
    try:
        return import_reference(req.csv_content, req.filename)
    except (ValueError, OverflowError, csv.Error) as exc:
        raise HTTPException(422, str(exc)) from None


@app.get("/references/master")
def master_references():
    return {"references": list_references()}


class ExportRequest(BaseModel):
    selected_urls: list[str] = Field(min_length=1, max_length=100)


@app.post("/research/export/{job_id}")
def export_research(job_id: str, req: ExportRequest):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["request"].get("preview_only", True):
        raise HTTPException(403, "This is a preview-only job; Google Sheets export is disabled")
    if job["status"] in {"queued", "running"}:
        raise HTTPException(409, "Wait until research stops before exporting selected results")
    qualified = {r["url"]: r for r in job["accepted"] if r.get("status") == "qualified"}
    if any(url not in qualified for url in req.selected_urls):
        raise HTTPException(422, "Only qualified results from this job can be exported")
    for url in dict.fromkeys(req.selected_urls):
        if not claim_export(job_id, url):
            continue
        try:
            append_supplier_row(job_id, job["request"]["product"], qualified[url])
            finish_export(job_id, url, "exported")
        except Exception:
            # A timed-out write may have succeeded. Require manual reconciliation.
            finish_export(job_id, url, "uncertain_check_sheet_before_retry")
    return {"exports": get_job(job_id)["exports"]}
