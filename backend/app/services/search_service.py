"""Full-text + geo search across professionals, designs, and vendor
products. A production implementation would use PostgreSQL's tsvector/GIN
index (or an external search engine) rather than naive ILIKE scans."""
from sqlalchemy.orm import Session


class SearchService:
    def __init__(self, db: Session):
        self.db = db

    def search_professionals(self, *, query: str, latitude: float | None = None, longitude: float | None = None, radius_km: float = 20):
        raise NotImplementedError("Combine tsvector full-text search with an optional PostGIS ST_DWithin filter.")

    def search_designs(self, *, query: str, min_price: float | None = None, max_price: float | None = None):
        raise NotImplementedError("tsvector full-text search over designs.title/description.")

    def search_vendor_products(self, *, query: str, category_id=None):
        raise NotImplementedError("tsvector full-text search over vendor_products.name/description.")
