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

from backend.utils import domain_from_url, registrable_domain

LEGAL_SUFFIXES = {
    "incorporated", "corporation", "company", "limited", "gmbh", "llc", "ltd",
    "inc", "corp", "plc", "llp", "lp", "sas", "pty", "co", "sa", "bv", "nv", "ag",
}


def name_key(value):
    value = unicodedata.normalize("NFKD", value).casefold()
    return "".join(c for c in value if c.isalnum())


def core_name_key(value):
    tokens = re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKD", value).casefold())
    while tokens and tokens[-1] in LEGAL_SUFFIXES:
        tokens.pop()
    return "".join(tokens)


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
        self.by_domain, self.by_name, self.by_registrable = {}, {}, {}
        for row in reference["records"]:
            if row["domain"]:
                self.by_domain.setdefault(row["domain"], []).append(row)
                parent = registrable_domain(row["domain"])
                if parent:
                    self.by_registrable.setdefault(parent, []).append(row)
            if name_key(row["supplier_name"]):
                self.by_name.setdefault(name_key(row["supplier_name"]), []).append(row)

    def has_exact_host(self, host):
        return bool(host and host in self.by_domain)

    def _payload(self, status, basis, rows, *, name_relation="", matched_url=""):
        return {"status": status, "basis": basis, "name_relation": name_relation, "matched_url": matched_url,
                "master_reference_id": self.reference["id"],
                "company_identity_verified": False, "confirmed_new_supplier": False,
                "matches": [{"supplier_name": r["supplier_name"], "url": r["url"], "country": r["country"],
                             "source_row": r["source_row"], "master_reference_id": self.reference["id"]} for r in rows]}

    def _hosts(self, url, alternate_urls):
        hosts = []
        for candidate in (url, *alternate_urls):
            host = domain_from_url(candidate)
            if host and host not in {h[0] for h in hosts}:
                hosts.append((host, candidate))
        return hosts

    def match(self, name="", url="", *, alternate_urls=()):
        hosts = self._hosts(url, alternate_urls)
        for host, matched_url in hosts:
            rows = self.by_domain.get(host, [])
            if not rows:
                continue
            names = {name_key(r["supplier_name"]) for r in rows}
            if len(names) != 1:
                return self._payload("ambiguous", "exact_website_host", rows, matched_url=matched_url)
            relation = "exact" if not name_key(name) or name_key(name) in names else (
                "legal_suffix" if core_name_key(name) and core_name_key(name) == core_name_key(rows[0]["supplier_name"])
                else "different")
            status = "existing_domain_match" if relation != "different" else "domain_match_name_conflict"
            return self._payload(status, "exact_website_host", rows, name_relation=relation, matched_url=matched_url)
        for host, matched_url in hosts:
            parent = registrable_domain(host)
            related = [r for r in self.by_registrable.get(parent, []) if r["domain"] != host]
            if related:
                return self._payload("related_domain_needs_verification", "related_registrable_domain", related,
                                     matched_url=matched_url)
        rows = self.by_name.get(name_key(name), [])
        if not rows:
            return self._payload("unmatched", "no_exact_match", [])
        domains = {r["domain"] for r in rows}
        if len(domains) != 1 or not any(domains):
            return self._payload("ambiguous", "exact_normalized_name", rows)
        if hosts and hosts[0][0] != next(iter(domains)):
            return self._payload("name_match_different_website", "exact_normalized_name", rows,
                                 matched_url=hosts[0][1])
        return self._payload("name_match_needs_verification", "exact_normalized_name", rows)


def match_without_reference():
    return {"status": "not_checked", "confirmed_new_supplier": False, "matches": []}
