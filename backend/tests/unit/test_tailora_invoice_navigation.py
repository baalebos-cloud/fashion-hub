from app.integrations.ai.navigation_agent import build_navigation_response


def test_customer_invoice_help():
    reply = build_navigation_response(user_role='customer', user_question='Where is my invoice?', offline_only=True)
    assert '/app/customer/invoices' in reply
    assert '/app/customer/orders' in reply
    assert 'cannot confirm' in reply


def test_customer_receipt_help():
    reply = build_navigation_response(user_role='customer', user_question='Where is my receipt?', offline_only=True)
    assert '/app/customer/invoices' in reply


def test_other_roles_do_not_receive_customer_invoice_page():
    reply = build_navigation_response(user_role='tailor', user_question='Where is my invoice?', offline_only=True)
    assert '/app/customer/invoices' not in reply
