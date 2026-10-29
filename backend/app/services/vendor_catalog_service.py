"""Catalog identity/price resolution shared by carts and checkout."""
from decimal import Decimal
from app.core.exceptions import ConflictError
from app.models.inventory import Inventory
from app.models.product_variant import ProductVariant
from app.models.user import User
from app.models.vendor import Vendor
from app.models.vendor_product import VendorProduct

MAX_AMOUNT = Decimal('9999999999.99')


def catalog_rows(db, variant_ids, *, lock=False):
    query = (db.query(ProductVariant, VendorProduct, Vendor, User)
             .join(VendorProduct, VendorProduct.id == ProductVariant.product_id)
             .join(Vendor, Vendor.id == VendorProduct.vendor_id)
             .join(User, User.id == Vendor.user_id)
             .filter(ProductVariant.id.in_(variant_ids)).order_by(ProductVariant.id))
    if lock:
        query = query.with_for_update(read=True, of=[ProductVariant, VendorProduct, Vendor, User]).populate_existing()
    return {str(row[0].id): row for row in query.all()}


def price_of(variant):
    price = Decimal(str(variant.price))
    if not price.is_finite() or price <= 0 or price > MAX_AMOUNT or price != price.quantize(Decimal('0.01')):
        raise ConflictError('This product has an invalid catalog price.')
    return price


def assert_purchasable(row):
    variant, product, vendor, user = row
    if not product.is_active or not vendor.is_verified or not user.is_active or user.role != 'vendor':
        raise ConflictError('This product is not currently available for purchase.')
    if product.currency != 'NGN':
        raise ConflictError('Material checkout currently supports NGN products only.')
    price_of(variant)


def lock_inventory(db, variant_ids):
    return {str(item.product_variant_id): item for item in
            db.query(Inventory).filter(Inventory.product_variant_id.in_(variant_ids))
            .order_by(Inventory.product_variant_id).with_for_update().populate_existing().all()}


class VendorCatalogService:
    def __init__(self, db):
        self.db = db

    def owned_vendor(self, user_id):
        vendor = self.db.query(Vendor).join(User, User.id == Vendor.user_id).filter(
            Vendor.user_id == user_id, User.role == 'vendor', User.is_active.is_(True)).first()
        if not vendor:
            from app.core.exceptions import NotFoundError
            raise NotFoundError('Save a vendor profile before publishing products.')
        return vendor

    def listing(self, product, vendor, variants=None):
        if variants is None:
            variants = (self.db.query(ProductVariant, Inventory).outerjoin(Inventory, Inventory.product_variant_id == ProductVariant.id)
                        .filter(ProductVariant.product_id == product.id).order_by(ProductVariant.sku).all())
        return dict(id=product.id, vendor_id=vendor.id, vendor_name=vendor.business_name, name=product.name,
                    description=product.description, category_id=product.category_id, primary_image_url=product.primary_image_url, image_urls=product.image_urls or [], unit_of_measure=product.unit_of_measure,
                    base_price=float(product.base_price), currency=product.currency, is_active=product.is_active,
                    variants=[dict(id=v.id, product_id=v.product_id, sku=v.sku, attributes=v.attributes,
                                   price=float(v.price), quantity_available=i.quantity_available if i else 0) for v, i in variants])

    def query(self, owner_user_id=None):
        query = self.db.query(VendorProduct, Vendor).join(Vendor, Vendor.id == VendorProduct.vendor_id).join(User, User.id == Vendor.user_id)
        if owner_user_id:
            return query.filter(Vendor.user_id == owner_user_id, User.role == 'vendor', User.is_active.is_(True))
        return query.filter(VendorProduct.is_active.is_(True), Vendor.is_verified.is_(True), User.is_active.is_(True), User.role == 'vendor', VendorProduct.currency == 'NGN')

    def list(self, pagination, *, vendor_id=None, category_id=None, owner_user_id=None):
        query = self.query(owner_user_id)
        if vendor_id:
            query = query.filter(VendorProduct.vendor_id == vendor_id)
        if category_id:
            query = query.filter(VendorProduct.category_id == category_id)
        total = query.count()
        rows = query.order_by(VendorProduct.created_at.desc(), VendorProduct.id).offset(pagination.offset).limit(pagination.page_size).all()
        variants = {}
        for variant, inventory in self.db.query(ProductVariant, Inventory).outerjoin(Inventory, Inventory.product_variant_id == ProductVariant.id).filter(ProductVariant.product_id.in_([p.id for p, _ in rows])).order_by(ProductVariant.sku):
            variants.setdefault(variant.product_id, []).append((variant, inventory))
        return dict(items=[self.listing(p, v, variants.get(p.id, [])) for p, v in rows], total=total, page=pagination.page,
                    page_size=pagination.page_size, total_pages=(total + pagination.page_size - 1) // pagination.page_size)

    def get(self, product_id):
        row = self.query().filter(VendorProduct.id == product_id).first()
        if not row:
            from app.core.exceptions import NotFoundError
            raise NotFoundError('Product not found.')
        return self.listing(*row)

    def create(self, user_id, payload):
        import uuid
        from app.models.inventory import Inventory
        vendor = self.owned_vendor(user_id)
        product = VendorProduct(vendor_id=vendor.id, name=payload.name, description=payload.description,
                                base_price=payload.base_price, currency='NGN', category_id=payload.category_id,
                                image_urls=payload.image_urls, unit_of_measure=payload.unit_of_measure,
                                primary_image_url=payload.image_urls[0])
        try:
            self.db.add(product)
            self.db.flush()
            variant = ProductVariant(product_id=product.id, sku='FH-' + uuid.uuid4().hex, price=payload.base_price)
            self.db.add(variant)
            self.db.flush()
            self.db.add(Inventory(product_variant_id=variant.id, quantity_available=payload.initial_stock, quantity_reserved=0))
            if payload.initial_stock:
                from app.models.inventory_restock import InventoryRestock
                self.db.add(InventoryRestock(product_variant_id=variant.id, actor_user_id=user_id,
                                             quantity=payload.initial_stock, idempotency_key="initial_" + product.id.hex))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self.listing(product, vendor)

    def update(self, user_id, product_id, payload):
        from app.core.exceptions import NotFoundError
        vendor = self.owned_vendor(user_id)
        product = (self.db.query(VendorProduct).filter_by(id=product_id, vendor_id=vendor.id)
                   .with_for_update().populate_existing().first())
        if not product:
            raise NotFoundError('Product not found.')
        # Price/SKU changes need a separate variant-edit contract. Metadata
        # updates cannot silently rewrite an already reserved order's price.
        product.name, product.description, product.is_active = payload.name, payload.description, payload.is_active
        self.db.commit()
        return self.listing(product, vendor)
