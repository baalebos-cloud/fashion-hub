"""
API-level test documenting the exact required order endpoint surface:

  GET  /api/v1/orders
  GET  /api/v1/orders/{order_id}
  POST /api/v1/orders/{order_id}/accept
  POST /api/v1/orders/{order_id}/start-production
  POST /api/v1/orders/{order_id}/ready
  POST /api/v1/orders/{order_id}/ship
  GET  /api/v1/orders/{order_id}/tracking
  POST /api/v1/orders/{order_id}/received
  GET  /api/v1/orders/{order_id}/timeline
  POST /api/v1/orders/{order_id}/review
"""
import pytest

pytestmark = pytest.mark.skip(reason="Requires a configured test database; wire up an app fixture overriding get_db before enabling.")

REQUIRED_ORDER_ROUTES = [
    ("GET", "/api/v1/orders"),
    ("GET", "/api/v1/orders/{order_id}"),
    ("POST", "/api/v1/orders/{order_id}/accept"),
    ("POST", "/api/v1/orders/{order_id}/start-production"),
    ("POST", "/api/v1/orders/{order_id}/ready"),
    ("POST", "/api/v1/orders/{order_id}/ship"),
    ("GET", "/api/v1/orders/{order_id}/tracking"),
    ("POST", "/api/v1/orders/{order_id}/received"),
    ("GET", "/api/v1/orders/{order_id}/timeline"),
    ("POST", "/api/v1/orders/{order_id}/review"),
]


def test_all_required_order_routes_are_registered():
    from app.main import app

    registered_paths = {route.path for route in app.routes}
    for _, path_template in REQUIRED_ORDER_ROUTES:
        assert path_template.replace("{order_id}", "{order_id}") in registered_paths
