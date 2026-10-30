"""Bounded public API calls; the pinned Apify SDK lacks charge-cap support."""
import time
from urllib.parse import quote

import requests

from backend.config import APIFY_TOKEN
from backend.research_context import JobStopped, LimitReached

API = "https://api.apify.com/v2"
TERMINAL = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}


class ActorError(RuntimeError):
    """Safe diagnostic generated locally, without raw provider response content."""


def run_actor(actor, run_input, context, *, result_limit=100, timeout_seconds=90, memory_mb=1024):
    if not APIFY_TOKEN:
        raise RuntimeError("Apify credential is not configured")
    if memory_mb not in {1024, 2048}:
        raise ActorError("Unsupported bounded actor memory setting")
    session = requests.Session()
    session.headers.update({"Authorization": "Bearer " + APIFY_TOKEN})
    actor_path = quote(actor.replace("/", "~"), safe="~")
    run_id = None
    run = None
    operation = None

    def request(method, path, **kwargs):
        context.checkpoint()
        response = session.request(method, API + path, timeout=max(1, min(15, context.remaining_seconds())), **kwargs)
        if not response.ok:
            raise ActorError(f"Apify HTTP {response.status_code}")
        return response.json()

    def abort():
        if run_id and run and run["status"] not in TERMINAL:
            try:
                response = session.post(API + f"/actor-runs/{run_id}/abort", timeout=10)
                response.raise_for_status()
                context.record(operation, abort_requested=True, abort_status=response.json().get("data", {}).get("status"))
            except Exception:
                context.record(operation, abort_requested=False, needs_manual_abort=True)

    try:
        info = request("GET", "/acts/" + actor_path)["data"]
        pricing = info.get("pricingInfos", [])
        current = info.get("currentPricingInfo") or (pricing[-1] if pricing else {})
        if current.get("pricingModel") != "PAY_PER_EVENT":
            raise ActorError("Actor needs pay-per-event pricing for the configured charge cap")
        cap = context.request.max_actor_charge_usd
        operation = context.reserve("apify", cap, actor=actor, memory_mb=memory_mb)
        run = request("POST", f"/acts/{actor_path}/runs", params={
            "maxTotalChargeUsd": cap, "memory": memory_mb,
            "timeout": max(1, min(timeout_seconds, int(context.remaining_seconds()))),
        }, json=run_input)["data"]
        run_id = run["id"]
        context.record(operation, run_id=run_id, dataset_id=run.get("defaultDatasetId"),
                       build_id=run.get("buildId"), status=run["status"])
        while run["status"] not in TERMINAL:
            context.checkpoint()
            time.sleep(min(1, max(0, context.remaining_seconds())))
            run = request("GET", f"/actor-runs/{run_id}")["data"]
        context.record(operation, status=run["status"], reported_usage_usd=run.get("usageTotalUsd"))
        if run["status"] != "SUCCEEDED":
            raise ActorError("Apify run ended with " + run["status"])
        return request("GET", f"/datasets/{run['defaultDatasetId']}/items", params={"limit": result_limit, "clean": "false"})
    except (JobStopped, LimitReached):
        abort()
        raise
    except Exception as exc:
        if operation:
            context.record(operation, status="error", charge_uncertain=True,
                           error=str(exc) if isinstance(exc, ActorError) else type(exc).__name__)
        abort()
        raise
    finally:
        session.close()
