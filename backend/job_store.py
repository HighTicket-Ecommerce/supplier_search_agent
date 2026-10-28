"""Durable jobs for the single-process local backend."""
import json
import os
from pathlib import Path
import sqlite3
import time
from contextlib import contextmanager


@contextmanager
def _connect():
    path = Path(os.getenv("SUPPLIER_JOB_DB", str(Path(__file__).resolve().parents[1] / "var" / "research_jobs.sqlite")))
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, data TEXT NOT NULL, updated REAL NOT NULL)")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_job(job_id, request=None):
    job = {"status": "queued", "accepted": [], "review": [], "rejected": [], "total": 0,
           "processed": 0, "error": None, "request": request or {}, "limits": {},
           "operations": [], "exports": {}, "observations": [], "directory_coverage": [],
           "catalogues": {}, "warnings": [], "skipped": [], "master_reference": None,
           "discovery_candidates": [], "discovery_coverage": [], "created_at": time.time()}
    with _connect() as db:
        db.execute("INSERT INTO jobs VALUES (?, ?, ?)", (job_id, json.dumps(job), time.time()))


def get_job(job_id):
    with _connect() as db:
        row = db.execute("SELECT data FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return json.loads(row[0]) if row else None


def update_job(job_id, **kwargs):
    with _connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT data FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise KeyError(job_id)
        job = json.loads(row[0])
        if job["status"] == "stopped" and kwargs.get("status") in {"running", "completed", "limited", "failed"}:
            kwargs.pop("status")
        job.update(kwargs)
        db.execute("UPDATE jobs SET data = ?, updated = ? WHERE id = ?", (json.dumps(job), time.time(), job_id))


def recover_interrupted_jobs():
    """Run once at startup; use one backend worker with this local store."""
    with _connect() as db:
        for job_id, data in db.execute("SELECT id, data FROM jobs").fetchall():
            job = json.loads(data)
            if job["status"] in {"queued", "running"}:
                job.update(status="interrupted", error="Backend restarted; saved partial results are available.")
                db.execute("UPDATE jobs SET data = ?, updated = ? WHERE id = ?", (json.dumps(job), time.time(), job_id))


def claim_export(job_id, url):
    """Claim before an external write. Uncertain writes are never retried automatically."""
    with _connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT data FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return False
        job = json.loads(row[0])
        if url in job.setdefault("exports", {}):
            return False
        job["exports"][url] = "writing"
        db.execute("UPDATE jobs SET data = ?, updated = ? WHERE id = ?", (json.dumps(job), time.time(), job_id))
        return True


def finish_export(job_id, url, status):
    with _connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT data FROM jobs WHERE id = ?", (job_id,)).fetchone()
        job = json.loads(row[0])
        job["exports"][url] = status
        db.execute("UPDATE jobs SET data = ?, updated = ? WHERE id = ?", (json.dumps(job), time.time(), job_id))
