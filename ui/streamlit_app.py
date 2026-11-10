import os
import sys
from pathlib import Path
import hmac
import time
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
# Streamlit's console launcher adds ui/, so expose sibling shared helpers too.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.utils import spreadsheet_safe

load_dotenv()

BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.getenv("BACKEND_PORT", "8000")
BACKEND_SCHEME = os.getenv("BACKEND_SCHEME", "http")
BASE_URL = f"{BACKEND_SCHEME}://{BACKEND_HOST}:{BACKEND_PORT}"
SUPPLIER_API_KEY = os.getenv("SUPPLIER_API_KEY", "")
UI_PASSWORD = os.getenv("SUPPLIER_UI_PASSWORD", "")

COUNTRY_OPTIONS = [
    "United States",
    "Canada",
    "United Kingdom",
    "Germany",
    "Australia",
]

STATUS_LABELS = {
    "running": "Searching for suppliers...",
    "completed": "Research complete",
    "stopped": "Research stopped",
    "failed": "Research failed",
    "not_found": "Job not found",
}

# ----------------------------
# PAGE CONFIG & STYLING
# ----------------------------
st.set_page_config(page_title="Supplier Agent", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .block-container { max-width: 60rem; padding-top: 2rem; padding-bottom: 1rem; }

    .supplier-table { overflow-x: auto; }
    .supplier-table table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
    }
    .supplier-table th {
        background: #f1f5f9;
        padding: 10px 12px;
        text-align: left;
        font-weight: 600;
        color: #334155;
        border-bottom: 2px solid #e2e8f0;
    }
    .supplier-table td {
        padding: 8px 12px;
        border-bottom: 1px solid #f1f5f9;
        color: #475569;
    }
    .supplier-table tr:hover td { background: #f8fafc; }
    .supplier-table a { color: #2563eb; text-decoration: none; }
    .supplier-table a:hover { text-decoration: underline; }

    [data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 16px;
    }

    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px 6px 0 0;
        padding: 8px 20px;
    }

    .disclaimer {
        text-align: center;
        color: #94a3b8;
        font-size: 0.75rem;
        padding: 8px 0;
    }

    /* Primary button styling (Run Research) */
    .stButton > button[kind="primary"],
    .run-btn button {
        background: #0ea5e9 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 2rem !important;
        font-weight: 600 !important;
    }
    .stButton > button[kind="primary"]:hover,
    .run-btn button:hover {
        background: #0284c7 !important;
    }

    /* Multiselect tag pills */
    [data-baseweb="tag"] {
        background-color: #e0f2fe !important;
        color: #0369a1 !important;
        border-radius: 6px !important;
    }
    [data-baseweb="tag"] span:first-child {
        color: #0369a1 !important;
    }

    /* Download button styling */
    .stDownloadButton > button {
        background: #059669 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    .stDownloadButton > button:hover {
        background: #047857 !important;
    }

    /* Stop button styling */
    .stop-btn button {
        background: #ef4444 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    .stop-btn button:hover {
        background: #dc2626 !important;
    }

    /* Spinner animation */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    .searching-indicator {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 12px 16px;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .searching-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #2563eb;
        animation: pulse 1.5s ease-in-out infinite;
    }
    .searching-dot:nth-child(2) { animation-delay: 0.3s; }
    .searching-dot:nth-child(3) { animation-delay: 0.6s; }
    .searching-text {
        color: #1e40af;
        font-weight: 500;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

TERMINAL_STATES = {"completed", "stopped", "failed", "limited", "interrupted"}
BACKEND_ERRORS = {
    401: "The backend rejected the API key. Set the same SUPPLIER_API_KEY for the UI and the backend.",
    503: "The backend is unavailable or has no SUPPLIER_API_KEY configured.",
}


def api(method, path, **kwargs):
    try:
        response = requests.request(method, BASE_URL + path, timeout=20,
                                    headers={"X-API-Key": SUPPLIER_API_KEY}, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as exc:
        status = getattr(exc.response, "status_code", None)
        st.error(BACKEND_ERRORS.get(status, "Backend request failed: HTTP " + str(status)))
        st.stop()
    except requests.RequestException as exc:
        st.error("Backend request failed: " + type(exc).__name__)
        st.stop()


def spreadsheet_csv(frame):
    return frame.map(spreadsheet_safe).to_csv(index=False)


def render_results(result):
    groups = [("Qualified candidates", "accepted"), ("Needs review", "review"), ("Excluded", "rejected")]
    # Older saved jobs can contain other research results; show them only when present.
    if result.get("observations"):
        groups.append(("Saved observations", "observations"))
    labels = [label for label, _ in groups]
    if result.get("catalogues"):
        labels.append("Catalogue products")
    tabs = st.tabs(labels)
    for tab, (_, key) in zip(tabs, groups):
        with tab:
            rows = result.get(key, [])
            if not rows:
                st.info("No results in this group.")
                continue
            flattened = []
            for row in rows:
                display = {k: v for k, v in row.items() if k not in {"sources", "discovery", "evidence", "catalogue", "master_match"}}
                if result.get("master_reference"):
                    display["master_match_status"] = row.get("master_match", {}).get("status", "not_checked")
                    display["matched_master_rows"] = ", ".join(str(m["source_row"]) for m in row.get("master_match", {}).get("matches", []))
                display["evidence_urls"] = ", ".join(dict.fromkeys(e["source_url"] for e in row.get("evidence", [])))
                flattened.append(display)
            frame = pd.DataFrame(flattened)
            st.dataframe(frame, width="stretch", hide_index=True)
            st.download_button("Download " + key + " CSV", spreadsheet_csv(frame), file_name=key+"_suppliers.csv", mime="text/csv", key="download_"+key)
    if result.get("catalogues"):
        with tabs[-1]:
            for url, catalogue in result["catalogues"].items():
                st.write(url)
                st.write(catalogue["coverage"])
                st.write(catalogue.get("observed_price_ranges", []))
                products = [{k: v for k, v in p.items() if k != "description"} for p in catalogue["products"]]
                frame = pd.DataFrame(products)
                st.dataframe(frame, width="stretch", hide_index=True)
                st.download_button("Download product sample CSV", spreadsheet_csv(frame), file_name="catalogue_products.csv",
                                   mime="text/csv", key="catalogue_"+url)
    if result.get("master_reference"):
        st.caption("Compared with: " + result["master_reference"]["filename"] + ". Unmatched rows are not confirmed new suppliers.")
    if result.get("directory_coverage"):
        with st.expander("Directory coverage"):
            st.json(result["directory_coverage"])
    if result.get("skipped"):
        with st.expander("Skipped sites (" + str(len(result["skipped"])) + ")"):
            st.caption("Sites skipped before verification.")
            st.dataframe(pd.DataFrame(result["skipped"]), width="stretch", hide_index=True)
    if result.get("discovery_candidates"):
        with st.expander("Discovery selection (" + str(len(result["discovery_candidates"])) + " search results)"):
            st.caption("Search hints set checking order. Selected sites still need product, company-role and location verification.")
            st.dataframe(pd.DataFrame(result["discovery_candidates"]), width="stretch", hide_index=True)
            st.json(result.get("discovery_coverage", []))
    with st.expander("Evidence details"):
        st.json({k: result.get(k, []) for k in ["accepted", "review", "rejected", "observations"]})
    qualified = result.get("accepted", [])
    if qualified and not result.get("preview_only", True):
        by_url = {row["url"]: row for row in qualified if row["url"] not in result.get("exports", {})}
        selected = st.multiselect("Select reviewed candidates to export", list(by_url),
                                 format_func=lambda u: by_url[u].get("supplier_name", u) + " — " + u)
        if st.button("Export selected to Google Sheets", disabled=not selected):
            exported = api("POST", "/research/export/"+result["job_id"], json={"selected_urls": selected})
            result["exports"] = exported["exports"]
            st.write(exported["exports"])
    elif result.get("preview_only", True):
        st.caption("Preview only. Google Sheets export is disabled for this job.")


st.title("Supplier Research Agent")
st.caption("Search the web for manufacturers, brand owners and distributors of your products.")
if UI_PASSWORD and not st.session_state.get("unlocked"):
    password = st.text_input("Password", type="password")
    if password and hmac.compare_digest(password.encode(), UI_PASSWORD.encode()):
        st.session_state.unlocked = True
        st.rerun()
    elif password:
        st.error("Incorrect password.")
    st.stop()
st.session_state.setdefault("job_id", None)
st.session_state.setdefault("is_running", False)
is_running = st.session_state.is_running

with st.sidebar:
    with st.expander("Load saved research"):
        saved_id = st.text_input("Saved job ID", disabled=is_running)
        if st.button("Load saved results", disabled=is_running or not saved_id.strip()):
            result = api("GET", "/research/result/"+saved_id.strip())
            st.session_state.job_id = saved_id.strip()
            st.session_state.last_result = result
            st.session_state.is_running = result["status"] not in TERMINAL_STATES
            st.rerun()

product = st.text_input("Product types", placeholder="e.g., Complete cold plunge systems", disabled=is_running,
                        help="Describe the products you want to find suppliers for. No websites needed.")
country_col, role_col = st.columns(2)
with country_col:
    selected_countries = st.multiselect("Supplier country", COUNTRY_OPTIONS, default=["United States", "Canada"], disabled=is_running)
with role_col:
    selected_roles = st.multiselect("Supplier type", ["Manufacturer", "Brand owner", "Distributor"],
                                    default=["Manufacturer", "Brand owner"], disabled=is_running)
excluded = st.text_input("Exclude products", placeholder="e.g., replacement filters, accessories", disabled=is_running)

with st.expander("More options"):
    target = st.number_input("Suppliers to find", min_value=1, max_value=100, value=5, disabled=is_running)
    budget = st.number_input("Search budget ($)", min_value=0.5, max_value=100.0, value=5.0, step=0.5, disabled=is_running,
                             help="The search may stop at this budget before reaching the supplier target.")
    preview_only = not st.checkbox("Allow Google Sheets export after review", value=False, disabled=is_running,
                                   help="Export still requires selecting results and clicking Export after the search finishes.")
st.caption(f"Up to {target} suppliers · ${budget:.2f} search budget")

run = st.button("Search", type="primary", disabled=is_running)
if is_running and st.button("Stop research"):
    api("POST", "/research/stop/"+st.session_state.job_id)

if run:
    if len(product.strip()) < 2:
        st.error("Enter a product type.")
        st.stop()
    if not selected_roles:
        st.error("Select at least one supplier type.")
        st.stop()
    # Technical page/call/runtime/provider settings use the bounded API defaults.
    payload = {"product": product.strip(), "candidate_urls": [], "use_apify": True,
               "preview_only": preview_only, "target_suppliers": int(target),
               "allowed_countries": selected_countries, "allowed_supplier_types": selected_roles,
               "excluded_products": [p.strip() for p in excluded.split(",") if p.strip()],
               "max_execution_cost_usd": budget, "research_mode": "supplier_search"}
    if selected_roles == ["Distributor"]:
        # Product range, wholesale policy and company context may need four pages.
        payload["max_pages_per_supplier"] = 4
    started = api("POST", "/research/start", json=payload)
    st.session_state.job_id = started["job_id"]
    st.session_state.is_running = True
    st.session_state.pop("last_result", None)
    st.rerun()

job_id = st.session_state.job_id
if job_id:
    st.caption("Saved job ID: " + job_id)
    if st.session_state.is_running:
        progress = st.empty()
        while True:
            status = api("GET", "/research/status/"+job_id)
            progress.info(f"Searching… {status['accepted_count']} suppliers found · {status['review_count']} need review")
            if status["status"] in TERMINAL_STATES:
                break
            time.sleep(2)
        st.session_state.is_running = False
        st.session_state.last_result = api("GET", "/research/result/"+job_id)
        st.rerun()
    result = st.session_state.get("last_result") or api("GET", "/research/result/"+job_id)
    if result["status"] == "limited":
        st.warning("Stopped at a configured limit: " + result.get("limit_reason", "unknown"))
    elif result["status"] in {"failed", "interrupted"}:
        st.warning(result.get("error") or "Research interrupted; partial results are saved.")
    elif result["status"] == "stopped":
        st.info("Research stopped. Partial results are saved.")
    else:
        st.success("Research complete.")
    with st.expander("Search details"):
        st.json(result.get("limits", {}))
    for warning in result.get("warnings", []):
        st.warning(str(warning))
    render_results(result)
