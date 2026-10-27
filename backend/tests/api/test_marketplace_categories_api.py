"""Public taxonomy and RBAC checks against a real transactional PostgreSQL fixture."""
from fastapi.testclient import TestClient
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.main import app
from app.models.category import Category
from app.models.vendor_category import VendorCategory


def test_public_categories_are_frontend_compatible_and_admin_owned(db, make_user):
    def override_db():
        yield db
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as http:
            result = http.get("/api/v1/categories")
            assert result.status_code == 200
            assert isinstance(result.json(), list)
            assert any(row["slug"] == "native-wear" for row in result.json())
            item = {"name": "Formal Wear Test", "slug": "formal-wear-test"}
            assert http.post("/api/v1/categories", json=item).status_code == 401
            app.dependency_overrides[get_current_user] = lambda: make_user(role="vendor")
            assert http.post("/api/v1/categories", json=item).status_code == 403
            app.dependency_overrides[get_current_user] = lambda: make_user(role="admin")
            assert http.post("/api/v1/categories", json=item).status_code == 201
            assert http.post("/api/v1/categories", json=item).status_code == 409
            assert db.query(Category).filter_by(slug=item["slug"]).count() == 1
    finally:
        app.dependency_overrides.clear()


def test_material_categories_support_hierarchy_without_public_writes(db, make_user):
    def override_db():
        yield db
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as http:
            result = http.get("/api/v1/vendor-categories")
            assert result.status_code == 200
            assert isinstance(result.json(), list)
            assert any(row["slug"] == "fabrics" for row in result.json())
            app.dependency_overrides[get_current_user] = lambda: make_user(role="admin")
            parent = db.query(VendorCategory).filter_by(slug="fabrics").one()
            payload = {"name": "Printed Cotton Test", "slug": "printed-cotton-test",
                       "parent_category_id": str(parent.id)}
            assert http.post("/api/v1/vendor-categories", json=payload).status_code == 201
            assert http.post("/api/v1/vendor-categories", json=payload).status_code == 409
            assert db.query(VendorCategory).filter_by(slug=payload["slug"]).count() == 1
            payload["slug"] = "bad SLUG"
            assert http.post("/api/v1/vendor-categories", json=payload).status_code == 422
    finally:
        app.dependency_overrides.clear()
