"""Immutable, minimal CSV references and conservative website/name comparison."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import time
import unicodedata

from backend.utils import domain_from_url


def name_key(value):
    value = unicodedata.normalize("NFKD", value).casefold()
    return "".join(c for c in value if c.isalnum())


def reference_directory():
    return Path(os.getenv("SUPPLIER_REFERENCE_DIR", str(Path(__file__).resolve().parents[1] / "var" / "references")))


def parse_supplier_csv(content):
    if len(content.encode("utf-8")) > 15_000_000:
        raise ValueError("CSV exceeds the 15 MB limit")
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")), strict=True)
    columns = {str(c).strip().casefold(): c for c in reader.fieldnames or []}
    name_column = next((columns[k] for k in ("supplier", "supplier_name", "suppliers", "name", "brand") if k in columns), None)
    url_column = next((columns[k] for k in ("website", "url") if k in columns), None)
    if not name_column and not url_column:
        raise ValueError("CSV needs a Supplier/name or Website/url column")
    records = []
    def cell(row, column, limit):
        value = row.get(column, "") if column else ""
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ValueError("Invalid CSV cell")
        return value.strip()[:limit]

    for row_number, row in enumerate(reader, 2):
        if row_number > 50_001:
            raise ValueError("CSV exceeds the 50,000-row limit")
        name = cell(row, name_column, 300)
        url = cell(row, url_column, 2000)
        if not name and not url:
            continue
        records.append({"supplier_name": name, "url": url, "domain": domain_from_url(url),
                        "product_types": cell(row, columns.get("product types"), 1000),
                        "country": cell(row, columns.get("country"), 100),
                        "source_row": row_number})
    if not records:
        raise ValueError("CSV has no supplier records")
    return records


def import_reference(content, filename="suppliers.csv"):
    records = parse_supplier_csv(content)
    reference_id = hashlib.sha256(content.encode("utf-8")).hexdigest()
    directory = reference_directory()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (reference_id + ".json")
    if not path.exists():
        reference = {"id": reference_id, "filename": Path(filename).name[:200], "imported_at": time.time(),
                     "record_count": len(records), "records": records}
        with tempfile.NamedTemporaryFile("w", dir=directory, encoding="utf-8", delete=False) as output:
            json.dump(reference, output, ensure_ascii=False)
            temporary = output.name
        os.replace(temporary, path)
    return reference_summary(load_reference(reference_id))


def load_reference(reference_id):
    if not re.fullmatch(r"[a-f0-9]{64}", reference_id or ""):
        raise ValueError("Invalid master reference ID")
    try:
        return json.loads((reference_directory() / (reference_id + ".json")).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError("Master reference not found; import the CSV first") from None


def reference_summary(reference):
    return {k: reference[k] for k in ("id", "filename", "imported_at", "record_count")}


def list_references():
    directory = reference_directory()
    return sorted((reference_summary(load_reference(p.stem)) for p in directory.glob("*.json")),
                  key=lambda r: r["imported_at"], reverse=True)


class MasterIndex:
    def __init__(self, reference):
        self.reference = reference
        self.by_domain, self.by_name = {}, {}
        for row in reference["records"]:
            if row["domain"]:
                self.by_domain.setdefault(row["domain"], []).append(row)
            if name_key(row["supplier_name"]):
                self.by_name.setdefault(name_key(row["supplier_name"]), []).append(row)

    def match(self, name="", url=""):
        domain = domain_from_url(url)
        rows = self.by_domain.get(domain, [])
        if rows:
            status = "existing_domain_match" if len({name_key(r["supplier_name"]) for r in rows}) == 1 else "ambiguous"
            if status == "existing_domain_match" and name_key(name) and name_key(name) not in {name_key(r["supplier_name"]) for r in rows}:
                status = "domain_match_name_conflict"
            basis = "exact_website_host"
        else:
            rows = self.by_name.get(name_key(name), [])
            status = ("name_match_needs_verification" if len({r["domain"] for r in rows}) == 1
                      and any(r["domain"] for r in rows) else "ambiguous") if rows else "unmatched"
            basis = "exact_normalized_name" if rows else "no_exact_match"
        return {"status": status, "basis": basis, "master_reference_id": self.reference["id"],
                "company_identity_verified": False, "confirmed_new_supplier": False,
                "matches": [{"supplier_name": r["supplier_name"], "url": r["url"], "country": r["country"],
                             "source_row": r["source_row"], "master_reference_id": self.reference["id"]} for r in rows]}


def match_without_reference():
    return {"status": "not_checked", "confirmed_new_supplier": False, "matches": []}
