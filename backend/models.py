from typing import Literal
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, StrictBool, TypeAdapter, field_validator, model_validator
from backend.config import COUNTRY_ALIASES, COUNTRY_OPTIONS


def website_url(value):
    value = value.strip()
    if "://" not in value:
        value = "https://" + value
    TypeAdapter(AnyHttpUrl).validate_python(value)
    url = urlsplit(value)
    if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
        raise ValueError("URLs must be HTTP(S) websites without credentials")
    return value


class ComparisonRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supplier_name: str = Field(default="", max_length=300)
    url: str = Field(default="", max_length=2000)

    @field_validator("url")
    @classmethod
    def normalize_url(cls, value):
        return website_url(value) if value.strip() else ""

    @model_validator(mode="after")
    def has_identity(self):
        self.supplier_name = self.supplier_name.strip()
        if not self.supplier_name and not self.url:
            raise ValueError("A supplier name or website is required")
        return self


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product: str = Field(min_length=2, max_length=300)
    candidate_urls: list[str] = Field(default_factory=list, max_length=200)
    research_mode: Literal["supplier_search", "distributor_brands", "list_compare"] = "supplier_search"
    master_reference_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    comparison_rows: list[ComparisonRow] = Field(default_factory=list, max_length=2000)
    directory_urls: list[str] = Field(default_factory=list, max_length=10)
    verify_directory_brands: bool = False
    max_directory_entries: int = Field(default=200, ge=1, le=1000)
    use_shopify_catalogue: bool = False
    shopify_catalogue_urls: list[str] = Field(default_factory=list, max_length=20)
    max_catalogue_products: int = Field(default=20, ge=1, le=50)
    allow_browser_fallback: bool = False
    # Compatibility name: controls discovery, not fetching supplied sites.
    use_apify: bool = True
    use_shopping: bool = False
    preview_only: bool = True
    target_suppliers: int = Field(default=5, ge=1, le=100)
    max_candidate_domains: int = Field(default=20, ge=1, le=200)
    allowed_countries: list[str] = Field(default_factory=lambda: ["United States", "Canada"])
    excluded_products: list[str] = Field(default_factory=list, max_length=30)
    allowed_supplier_types: list[Literal["Manufacturer", "Brand owner", "Distributor", "Retailer"]] = Field(
        default_factory=lambda: ["Manufacturer", "Brand owner", "Distributor"], min_length=1
    )
    max_pages: int = Field(default=30, ge=1, le=200)
    max_pages_per_supplier: int = Field(default=3, ge=1, le=8)
    max_external_calls: int = Field(default=50, ge=1, le=300)
    max_runtime_seconds: int = Field(default=300, ge=10, le=1800)
    max_execution_cost_usd: float = Field(default=5, ge=0.5, le=100, allow_inf_nan=False)
    max_actor_charge_usd: float = Field(default=0.5, ge=0.5, le=10, allow_inf_nan=False)

    @field_validator("product")
    @classmethod
    def product_not_blank(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Enter a product with at least two characters")
        return value

    @field_validator("candidate_urls", "directory_urls", "shopify_catalogue_urls")
    @classmethod
    def normalize_seeds(cls, values):
        result = []
        for value in values:
            value = website_url(value)
            if value not in result:
                result.append(value)
        return result

    @model_validator(mode="after")
    def mode_inputs(self):
        if self.research_mode == "list_compare" and (not self.master_reference_id or not self.comparison_rows):
            raise ValueError("List comparison requires a master reference and supplier rows")
        if self.research_mode == "distributor_brands" and not self.directory_urls:
            raise ValueError("Distributor research requires a brand-directory URL")
        return self

    @field_validator("allowed_countries")
    @classmethod
    def normalize_countries(cls, values):
        result = []
        for value in values:
            value = COUNTRY_ALIASES.get(value.strip(), value.strip())
            if value not in COUNTRY_OPTIONS:
                raise ValueError("Unsupported supplier country")
            if value not in result:
                result.append(value)
        return result


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: Literal["role", "product_match", "country", "identity"]
    source_url: str
    quote: str = Field(min_length=1, max_length=250)


class SupplierAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_product_company: StrictBool
    company_name: str
    supplier_type: Literal["Manufacturer", "Brand owner", "Distributor", "Retailer", "Marketplace", "Media / Blog", "Unknown"]
    owns_brand: StrictBool | None
    product_match: Literal["supported", "not_established", "explicitly_ruled_out"]
    product_kind: Literal["primary", "bundle_includes_primary", "accessory", "service", "unknown"]
    matched_product_urls: list[str]
    country: str | None
    country_basis: Literal["headquarters", "office", "company_base", "manufacturing", "market", "unknown"]
    identity_match: Literal["supported", "not_established", "contradicted", "not_requested"]
    email: str | None
    phone: str | None
    confidence: float = Field(ge=0, le=1, strict=True, allow_inf_nan=False)
    notes: str
    evidence: list[Evidence]


class CatalogueDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: str
    status: Literal["eligible", "excluded", "review"]
    product_kind: Literal["primary", "bundle_includes_primary", "accessory", "component", "service", "other", "unknown"]
    eligible_variant_ids: list[str]
    quote: str
    reason: str


class CatalogueAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    products: list[CatalogueDecision]
