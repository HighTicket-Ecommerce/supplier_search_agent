import os
import csv
import hmac
import time
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from backend.master_index import parse_supplier_csv
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
st.set_page_config(page_title="Supplier Agent", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 1rem; }

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
    tabs = st.tabs(["Qualified candidates", "Needs review", "Excluded", "List / directory observations", "Catalogue products"])
    for tab, key in zip(tabs, ["accepted", "review", "rejected", "observations"]):
        with tab:
            rows = result.get(key, [])
            if not rows:
                st.info("No results in this group.")
                continue
            flattened = []
            for row in rows:
                display = {k: v for k, v in row.items() if k not in {"sources", "discovery", "evidence", "catalogue", "master_match"}}
                display["master_match_status"] = row.get("master_match", {}).get("status", "not_checked")
                display["matched_master_rows"] = ", ".join(str(m["source_row"]) for m in row.get("master_match", {}).get("matches", []))
                display["evidence_urls"] = ", ".join(dict.fromkeys(e["source_url"] for e in row.get("evidence", [])))
                flattened.append(display)
            frame = pd.DataFrame(flattened)
            st.dataframe(frame, width="stretch", hide_index=True)
            st.download_button("Download " + key + " CSV", spreadsheet_csv(frame), file_name=key+"_suppliers.csv", mime="text/csv", key="download_"+key)
    with tabs[4]:
        catalogues = result.get("catalogues", {})
        if not catalogues:
            st.info("No Shopify catalogue samples in this run.")
        for url, catalogue in catalogues.items():
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
            st.caption("Discovered sites already in the master list, and blocked retailers or marketplaces. Supplied websites are still checked.")
            st.dataframe(pd.DataFrame(result["skipped"]), width="stretch", hide_index=True)
    if result.get("discovery_candidates"):
        with st.expander("Discovery selection (" + str(len(result["discovery_candidates"])) + " search results)"):
            st.caption("Search hints set checking order. Selected sites still need product, company-role and location verification.")
            st.dataframe(pd.DataFrame(result["discovery_candidates"]), width="stretch", hide_index=True)
            st.json(result.get("discovery_coverage", []))
    with st.expander("Full evidence and comparison details"):
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
st.caption("Find candidates, verify the requested product, review the evidence, then export.")
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

with st.expander("Load saved research"):
    saved_id = st.text_input("Saved job ID", disabled=is_running)
    if st.button("Load saved results", disabled=is_running or not saved_id.strip()):
        result = api("GET", "/research/result/"+saved_id.strip())
        st.session_state.job_id = saved_id.strip()
        st.session_state.last_result = result
        st.session_state.is_running = result["status"] not in TERMINAL_STATES
        st.rerun()

workflow_labels = {"supplier_search": "Research suppliers", "distributor_brands": "Extract distributor brands",
                   "list_compare": "Compare supplier lists"}
workflow = st.selectbox("Workflow", list(workflow_labels), format_func=workflow_labels.get, disabled=is_running)
st.session_state.setdefault("master_references", [])
with st.expander("Master supplier list"):
    master_file = st.file_uploader("Import master CSV", type=["csv"], disabled=is_running)
    if st.button("Import master list", disabled=is_running or master_file is None):
        try:
            content = master_file.getvalue().decode("utf-8-sig")
        except UnicodeDecodeError:
            st.error("Save the master CSV with UTF-8 encoding.")
            st.stop()
        imported = api("POST", "/references/master", json={"filename": master_file.name, "csv_content": content})
        st.session_state.master_references = [imported] + [r for r in st.session_state.master_references if r["id"] != imported["id"]]
        st.success(str(imported["record_count"]) + " supplier records imported. The original CSV is unchanged.")
    if st.button("Load saved master lists", disabled=is_running):
        st.session_state.master_references = api("GET", "/references/master")["references"]
    master_by_id = {r["id"]: r for r in st.session_state.master_references}
    master_id = st.selectbox("Compare against", [None] + list(master_by_id), disabled=is_running,
        format_func=lambda value: "No master comparison" if value is None else master_by_id[value]["filename"] + " (" + str(master_by_id[value]["record_count"]) + " rows)")

product = (st.text_input("Product", placeholder="e.g., Complete cold plunge systems, sauna heaters", disabled=is_running,
                         help="Describe the product you need. Put exclusions in Excluded products under Research controls.")
           if workflow != "list_compare" else "Supplier list comparison")
selected_countries = st.multiselect("Supplier headquarters", COUNTRY_OPTIONS, default=["United States", "Canada"], disabled=is_running)
selected_roles = st.multiselect("Company roles", ["Manufacturer", "Brand owner", "Distributor", "Retailer"],
                                default=["Manufacturer", "Brand owner"], disabled=is_running,
                                help="Select Distributor alone for an optional distributor review.")
seed_text, directory_text, comparison_rows, verify_brands = "", "", [], False
use_discovery = False
if workflow == "supplier_search":
    seed_text = st.text_area("Supplier websites to research first", placeholder="One website per line", disabled=is_running)
    use_discovery = st.checkbox("Discover additional suppliers", value=True, disabled=is_running)
elif workflow == "distributor_brands":
    directory_text = st.text_area("Distributor brand directories", placeholder="One directory URL per line", disabled=is_running)
    verify_brands = st.checkbox("Find official sites and verify listed brands", value=False, disabled=is_running)
    st.caption("Extraction compares the distributor's labels with your master list. Official-site verification uses additional search and page calls.")
else:
    comparison_file = st.file_uploader("Supplier list to compare (CSV)", type=["csv"], disabled=is_running)
    comparison_text = st.text_area("Or supplier names, one per line", disabled=is_running)
    if comparison_file is not None:
        try:
            comparison_rows = [{"supplier_name": r["supplier_name"], "url": r["url"]}
                               for r in parse_supplier_csv(comparison_file.getvalue().decode("utf-8-sig"))]
        except (ValueError, UnicodeDecodeError, csv.Error) as exc:
            st.error(str(exc))
            st.stop()
    comparison_rows.extend({"supplier_name": name.strip(), "url": ""} for name in comparison_text.splitlines() if name.strip())
    st.caption("This comparison makes no actor or model calls. Name matches and unmatched names need identity review.")
preview_only = st.checkbox("Preview only — disable Google Sheets export", value=True, disabled=is_running)

with st.expander("Research controls"):
    target = st.number_input("Qualified candidates to find", min_value=1, max_value=100, value=5, disabled=is_running)
    max_candidates = st.number_input("Maximum candidates", min_value=1, max_value=200, value=20, disabled=is_running)
    max_pages = st.number_input("Maximum website pages across the run", min_value=1, max_value=200, value=30, disabled=is_running)
    per_supplier = st.number_input("Maximum pages per supplier", min_value=1, max_value=8, value=3, disabled=is_running,
        help="For distributor-only checks, allow four pages to cover the product range, wholesale policy and company details. Browser fallback also counts toward this limit.")
    max_seconds = st.number_input("Maximum run time (seconds)", min_value=10, max_value=1800, value=300, disabled=is_running)
    max_calls = st.number_input("Maximum service calls", min_value=1, max_value=300, value=50, disabled=is_running)
    budget = st.number_input("Execution budget (USD)", min_value=0.5, max_value=100.0, value=5.0, step=0.5, disabled=is_running,
                             help="Conservatively reserves each actor's maximum charge. Unused actor reservations stay held until the run ends; account/storage fees are separate.")
    excluded = st.text_input("Excluded products (comma separated)", placeholder="e.g., replacement filters, assembly services", disabled=is_running)
    use_shopping = st.checkbox("Add Shopping discovery", value=False, disabled=is_running)
    browser_fallback = st.checkbox("Try a browser when page evidence is empty or thin", value=False, disabled=is_running)
    shopify_catalogue = st.checkbox("Check Shopify product catalogue", value=False, disabled=is_running)
    shopify_text = st.text_area("Known Shopify websites (optional)", placeholder="One website per line; otherwise detected from page evidence", disabled=is_running)
    catalogue_limit = st.number_input("Maximum catalogue products per supplier", min_value=1, max_value=50, value=20, disabled=is_running)
    directory_limit = st.number_input("Maximum directory entries across the run", min_value=1, max_value=1000, value=200, disabled=is_running)

run = st.button("Run research", type="primary", disabled=is_running)
if is_running and st.button("Stop research"):
    api("POST", "/research/stop/"+st.session_state.job_id)

if run:
    if len(product.strip()) < 2:
        st.error("Enter a product.")
        st.stop()
    if not selected_roles:
        st.error("Select at least one company role.")
        st.stop()
    seeds = [line.strip() for line in seed_text.splitlines() if line.strip()]
    if workflow == "supplier_search" and not seeds and not use_discovery:
        st.error("Provide supplier websites or enable discovery.")
        st.stop()
    if workflow == "list_compare" and (not master_id or not comparison_rows):
        st.error("Select a master list and provide suppliers to compare.")
        st.stop()
    if workflow == "distributor_brands" and not directory_text.strip():
        st.error("Provide a distributor brand-directory URL.")
        st.stop()
    payload = {"product": product.strip(), "candidate_urls": seeds, "use_apify": use_discovery,
               "use_shopping": use_shopping, "preview_only": preview_only,
               "target_suppliers": int(target), "max_candidate_domains": int(max_candidates),
               "allowed_countries": selected_countries, "allowed_supplier_types": selected_roles,
               "excluded_products": [p.strip() for p in excluded.split(",") if p.strip()],
               "max_pages": int(max_pages), "max_pages_per_supplier": int(per_supplier),
               "max_runtime_seconds": int(max_seconds), "max_external_calls": int(max_calls), "max_execution_cost_usd": budget,
               "research_mode": workflow, "master_reference_id": master_id, "comparison_rows": comparison_rows,
               "directory_urls": [u.strip() for u in directory_text.splitlines() if u.strip()], "verify_directory_brands": verify_brands,
               "max_directory_entries": int(directory_limit), "use_shopify_catalogue": shopify_catalogue,
               "shopify_catalogue_urls": [u.strip() for u in shopify_text.splitlines() if u.strip()],
               "max_catalogue_products": int(catalogue_limit), "allow_browser_fallback": browser_fallback}
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
            progress.write({"status": status["status"], "qualified": status["accepted_count"],
                            "needs_review": status["review_count"], "processed": status["processed"],
                            "limits": status["limits"]})
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
    st.write(result.get("limits", {}))
    for warning in result.get("warnings", []):
        st.warning(str(warning))
    render_results(result)
