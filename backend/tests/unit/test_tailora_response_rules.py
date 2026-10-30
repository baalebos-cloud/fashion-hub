from app.integrations.ai.navigation_agent import tailora_response_rules


def test_customer_rules_include_real_order_tracking_and_invoice_routes():
    instructions = tailora_response_rules("customer")
    assert "/app/customer/orders" in instructions
    assert "/app/customer/orders/:id/track" in instructions
    assert "/app/customer/invoices" in instructions
    assert "Markdown tables" in instructions
    assert "Never invent" in instructions


def test_role_separation_excludes_customer_pages_from_vendor():
    instructions = tailora_response_rules("vendor")
    assert "/app/customer/orders" not in instructions
    assert "/app/vendor/orders" in instructions


def test_unknown_role_gets_no_private_routes():
    instructions = tailora_response_rules("guest")
    assert "/app/customer/orders" not in instructions
    assert "none" in instructions
