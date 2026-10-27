"""Verified, published, bounded marketplace search. Never expose drafts or unverified sellers."""
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.design import Design
from app.models.professional import Professional
from app.models.user import User
from app.models.vendor_product import VendorProduct
from app.repositories.professional_repository import ProfessionalRepository
from app.services.vendor_catalog_service import VendorCatalogService


def _contains(term: str) -> str:
    return "%" + term.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


class SearchService:
    def __init__(self, db: Session):
        self.db = db

    def search_professionals(self, *, query: str, latitude: float | None = None,
                             longitude: float | None = None, radius_km: float = 20):
        return (ProfessionalRepository(self.db).verified_query(
            query=query, latitude=latitude, longitude=longitude, radius_km=radius_km,
        ).order_by(Professional.id).limit(50).all())

    def search_designs(self, *, query: str, min_price: float | None = None,
                       max_price: float | None = None):
        results = (self.db.query(Design)
                   .join(Professional, Professional.id == Design.professional_id)
                   .join(User, User.id == Professional.user_id)
                   .filter(Design.is_published.is_(True), Professional.is_verified.is_(True),
                           User.is_active.is_(True), Professional.accepts_new_orders.is_(True)))
        pattern = _contains(query)
        results = results.filter(or_(Design.title.ilike(pattern, escape="\\"),
                                     Design.description.ilike(pattern, escape="\\")))
        if min_price is not None:
            results = results.filter(Design.base_price >= min_price)
        if max_price is not None:
            results = results.filter(Design.base_price <= max_price)
        return results.order_by(Design.id).limit(50).all()

    def search_vendor_products(self, *, query: str, category_id=None):
        catalog = VendorCatalogService(self.db)
        pattern = _contains(query)
        results = catalog.query().filter(or_(
            VendorProduct.name.ilike(pattern, escape="\\"),
            VendorProduct.description.ilike(pattern, escape="\\"),
        ))
        if category_id is not None:
            results = results.filter(VendorProduct.category_id == category_id)
        return [catalog.listing(product, vendor) for product, vendor in
                results.order_by(VendorProduct.id).limit(50).all()]
