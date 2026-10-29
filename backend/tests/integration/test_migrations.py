"""Fresh and historical upgrades on disposable databases, never live data."""
from pathlib import Path
import uuid

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from tests.conftest import TEST_DATABASE_URL


@pytest.fixture()
def migration_database():
    # CI's dedicated Postgres role can create databases. Unique database names
    # keep these scenarios independent of the main service-test transaction.
    url = make_url(TEST_DATABASE_URL)
    name = "fashion_migration_" + uuid.uuid4().hex
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    engine = create_engine(url.set(database=name))
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    try:
        yield engine, config
    finally:
        engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()


def migrate(engine, config, revision):
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, revision)


@pytest.mark.parametrize("previous", [None, "0001", "035e1bd61029", "0002", "2ab23f38e9c6", "0003", "0004", "0005"])
def test_fresh_and_historical_upgrades_preserve_records(migration_database, previous):
    engine, config = migration_database
    if previous:
        migrate(engine, config, previous)
    user_id = uuid.uuid4()
    notification_id = uuid.uuid4()
    location_id = uuid.uuid4()
    if previous in {"035e1bd61029", "0002", "2ab23f38e9c6", "0003", "0004"}:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO users (id,email,hashed_password,full_name,role,is_active,is_email_verified,is_phone_verified,timezone) VALUES (:id,'preserved@example.com','test','Preserved','customer',true,false,false,'UTC')"), {"id": user_id})
            event_column = ',event_type' if previous in {'0003', '0004'} else ''
            event_value = ",'legacy.payment'" if previous in {'0003', '0004'} else ''
            conn.execute(text(f"INSERT INTO notifications (id,recipient_user_id,title,body,notification_type,is_read{event_column}) VALUES (:id,:user,'Preserved','Legacy notification','legacy.payment',false{event_value})"),
                         {"id": notification_id, "user": user_id})
            if previous == '0004':
                conn.execute(text("INSERT INTO locations (id,location_type,formatted_address,city,state_region,country,latitude,longitude) VALUES (:id,'customer_address','10 Legacy Street','Lagos','Lagos','NG',6.5244,3.3792)"), {'id': location_id})
            else:
                conn.execute(text("INSERT INTO locations (id,name,address_line,city,state,country,geom) VALUES (:id,'Old home','10 Legacy Street','Lagos','Lagos','NG',ST_GeogFromText('SRID=4326;POINT(3.3792 6.5244)'))"), {'id': location_id})
    migrate(engine, config, "head")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0014"
        assert {"users", "payouts", "referrals", "payment_outbox", "addresses"} <= set(inspect(conn).get_table_names())
        assert "eta_minutes" in {c["name"] for c in inspect(conn).get_columns("delivery_tracking")}
        assert str(next(x for x in inspect(conn).get_columns("payment_transactions") if x["name"] == "processed")["type"]) == "BOOLEAN"
        if previous in {"035e1bd61029", "0002", "2ab23f38e9c6", "0003", "0004"}:
            preserved_location = conn.execute(text('SELECT formatted_address,state_region,latitude,longitude FROM locations WHERE id=:id'), {'id': location_id}).one()
            assert preserved_location.formatted_address == '10 Legacy Street'
            assert preserved_location.state_region == 'Lagos'
            assert float(preserved_location.latitude) == 6.5244
            assert float(preserved_location.longitude) == 3.3792
            assert conn.execute(text("SELECT full_name FROM users WHERE id=:id"), {"id": user_id}).scalar_one() == "Preserved"
            assert conn.execute(text("SELECT event_type FROM notifications WHERE id=:id"), {"id": notification_id}).scalar_one() == "legacy.payment"
    # Repeating an upgrade is safe; the new revision can also be rolled back
    # and reapplied without touching pre-existing user records.
    migrate(engine, config, "head")
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.downgrade(config, "2ab23f38e9c6")
    migrate(engine, config, "head")


def test_duplicate_invoices_abort_instead_of_deleting_data(migration_database):
    engine, config = migration_database
    migrate(engine, config, "2ab23f38e9c6")
    order_id = uuid.uuid4()
    with engine.begin() as conn:
        for index in range(2):
            conn.execute(text("INSERT INTO invoices (id,invoice_number,order_id,issued_to_user_id,issued_by_user_id,line_items_snapshot,subtotal,delivery_fee,tax_amount,discount_amount,total_amount,currency,payment_status) VALUES (:id,:number,:order,:buyer,:seller,'[]',10,0,0,0,10,'NGN','successful')"),
                         {"id": uuid.uuid4(), "number": f"OLD-{index}", "order": order_id,
                          "buyer": uuid.uuid4(), "seller": uuid.uuid4()})
    with pytest.raises(RuntimeError, match="Duplicate invoices"):
        migrate(engine, config, "head")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM invoices")).scalar_one() == 2
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "2ab23f38e9c6"


def insert_payment(connection):
    order_id, payment_id = uuid.uuid4(), uuid.uuid4()
    connection.execute(text("INSERT INTO orders (id,order_number,order_type,buyer_user_id,seller_user_id,status,subtotal,delivery_fee,tax_amount,discount_amount,total_amount,currency) VALUES (:id,:number,'customer_order',:buyer,:seller,'pending',10,0,0,0,10,'NGN')"),
                       {"id": order_id, "number": "MIG-" + uuid.uuid4().hex[:16], "buyer": uuid.uuid4(), "seller": uuid.uuid4()})
    connection.execute(text("INSERT INTO payments (id,order_id,provider,provider_reference,amount,currency,status) VALUES (:id,:order,'paystack',:reference,10,'NGN','initialized')"),
                       {"id": payment_id, "order": order_id, "reference": "MIG-" + uuid.uuid4().hex})
    return payment_id


def test_json_boolean_development_schema_is_converted_without_losing_event(migration_database):
    engine, config = migration_database
    migrate(engine, config, "2ab23f38e9c6")
    event_id = uuid.uuid4()
    with engine.begin() as conn:
        payment_id = insert_payment(conn)
        conn.execute(text("INSERT INTO payment_transactions (id,payment_id,provider,provider_event_id,event_type,amount,raw_payload,processed) VALUES (:id,:payment,'paystack','legacy','charge.success',10,'{}',true)"),
                     {"id": event_id, "payment": payment_id})
        conn.execute(text("ALTER TABLE payment_transactions ALTER COLUMN processed TYPE json USING to_json(processed)"))
    migrate(engine, config, "head")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT processed FROM payment_transactions WHERE id=:id"), {"id": event_id}).scalar_one() is True


def test_downgrade_refuses_to_discard_pending_work(migration_database):
    engine, config = migration_database
    migrate(engine, config, "head")
    with engine.begin() as conn:
        payment_id = insert_payment(conn)
        conn.execute(text("INSERT INTO payment_outbox (id,payment_id,dedupe_key,kind,payload) VALUES (:id,:payment,'pending-migration-test','payment.settled','{}')"),
                     {"id": uuid.uuid4(), "payment": payment_id})
    with pytest.raises(RuntimeError, match="pending payment outbox"):
        with engine.begin() as conn:
            config.attributes["connection"] = conn
            command.downgrade(config, "2ab23f38e9c6")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM payment_outbox")).scalar_one() == 1
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0014"


def test_orphan_line_items_abort_without_removing_records(migration_database):
    engine, config = migration_database
    migrate(engine, config, '0003')
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO order_items (id,order_id,reference_type,name_snapshot,unit_price,quantity,line_total) VALUES (:id,:order,'design','Legacy orphan',10,1,10)"),
                     {'id': uuid.uuid4(), 'order': uuid.uuid4()})
    with pytest.raises(RuntimeError, match='Orphan order items'):
        migrate(engine, config, 'head')
    with engine.connect() as conn:
        assert conn.execute(text('SELECT count(*) FROM order_items')).scalar_one() == 1
        assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '0003'


@pytest.mark.parametrize('saved_record', ['order', 'address'])
def test_downgrade_preserves_new_checkout_records(migration_database, saved_record):
    from sqlalchemy.orm import Session
    from app.models.address import Address
    from app.models.location import Location
    from app.models.user import User
    engine, config = migration_database
    migrate(engine, config, 'head')
    if saved_record == 'order':
        with engine.begin() as conn:
            payment_id = insert_payment(conn)
            conn.execute(text("UPDATE orders SET pricing_source='catalog_v1' WHERE id=(SELECT order_id FROM payments WHERE id=:id)"), {'id': payment_id})
    else:
        with Session(engine) as db:
            user = User(email='address@example.com', hashed_password='not-used', full_name='Test', role='customer')
            location = Location(location_type='customer_address', formatted_address='10 Test Street', city='Lagos', country='NG')
            db.add_all([user, location])
            db.flush()
            db.add(Address(user_id=user.id, location_id=location.id))
            db.commit()
    with pytest.raises(RuntimeError, match='exist'):
        with engine.begin() as conn:
            config.attributes['connection'] = conn
            command.downgrade(config, '0003')
    with engine.connect() as conn:
        assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '0014'
        table = 'orders' if saved_record == 'order' else 'addresses'
        assert conn.execute(text(f'SELECT count(*) FROM {table}')).scalar_one() == 1


def stock_legacy_seed(engine):
    from sqlalchemy.orm import Session
    from tests.vendor_helpers import user, address
    from app.models.cart import Cart
    from app.models.cart_item import CartItem
    # ORM's new Cart.revision cannot be used before 0005; insert the old
    # cart shape explicitly while keeping catalog fixtures version-neutral.
    with Session(engine) as db:
        # Historical revision 0004 predates product image/unit columns.
        # Seed the exact legacy schema rather than using the latest ORM model.
        from app.models.vendor import Vendor
        from app.models.product_variant import ProductVariant
        from app.models.inventory import Inventory
        seller = user(db, 'vendor')
        vendor = Vendor(user_id=seller.id, business_name='Verified fabrics', is_verified=True)
        db.add(vendor)
        db.flush()
        from sqlalchemy import text as sql_text
        product_id = uuid.uuid4()
        db.execute(sql_text("INSERT INTO vendor_products (id,vendor_id,name,description,base_price,currency,is_active) "
                            "VALUES (:id,:vendor,'Navy cotton','Per yard',100.01,'NGN',true)"),
                   {"id": product_id, "vendor": vendor.id})
        variant = ProductVariant(product_id=product_id, sku='TEST-'+uuid.uuid4().hex, price=100.01)
        db.add(variant)
        db.flush()
        inv = Inventory(product_variant_id=variant.id, quantity_available=10, quantity_reserved=0)
        db.add(inv)
        buyer = user(db, 'tailor')
        db.commit()
        values = dict(cart=uuid.uuid4(), item=uuid.uuid4(), owner=buyer.id,
                      variant=variant.id, vendor=vendor.id, product=product_id, inventory=inv.id)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO carts (id,owner_user_id,status) VALUES (:cart,:owner,'active')"), values)
        conn.execute(text("INSERT INTO cart_items (id,cart_id,product_variant_id,vendor_id,quantity,unit_price_snapshot) VALUES (:item,:cart,:variant,:product,2,100.01)"), values)
    return values


@pytest.mark.parametrize('invalid', ['reserved', 'duplicate_cart', 'duplicate_line', 'quantity', 'orphan'])
def test_stock_migration_rejects_ambiguous_legacy_data_without_deleting_it(migration_database, invalid):
    engine, config = migration_database
    migrate(engine, config, '0004')
    values = stock_legacy_seed(engine)
    with engine.begin() as conn:
        if invalid == 'reserved': conn.execute(text('UPDATE inventory SET quantity_reserved=2'))
        if invalid == 'duplicate_cart': conn.execute(text("INSERT INTO carts (id,owner_user_id,status) VALUES (:id,:owner,'active')"), {**values, 'id': uuid.uuid4()})
        if invalid == 'duplicate_line': conn.execute(text('INSERT INTO cart_items (id,cart_id,product_variant_id,vendor_id,quantity,unit_price_snapshot) VALUES (:id,:cart,:variant,:product,1,100.01)'), {**values, 'id': uuid.uuid4()})
        if invalid == 'quantity': conn.execute(text('UPDATE cart_items SET quantity=0'))
        if invalid == 'orphan': conn.execute(text('UPDATE product_variants SET product_id=:id'), {'id': uuid.uuid4()})
    with pytest.raises(RuntimeError, match='legacy reserved|Duplicate|Invalid|Orphan'):
        migrate(engine, config, 'head')
    with engine.connect() as conn:
        assert conn.execute(text('SELECT count(*) FROM cart_items')).scalar_one() == (2 if invalid == 'duplicate_line' else 1)
        assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '0004'
        assert conn.execute(text('SELECT vendor_id FROM cart_items LIMIT 1')).scalar_one() == values['product']


def test_stock_migration_repairs_vendor_identity_and_preserves_history_on_downgrade(migration_database):
    engine, config = migration_database
    migrate(engine, config, '0004')
    values = stock_legacy_seed(engine)
    migrate(engine, config, 'head')
    with engine.connect() as conn:
        assert conn.execute(text('SELECT vendor_id FROM cart_items')).scalar_one() == values['vendor']
        assert conn.execute(text('SELECT revision FROM carts')).scalar_one() == 0
    with engine.begin() as conn:
        payment_id = insert_payment(conn)
        conn.execute(text("UPDATE orders SET pricing_source='vendor_catalog_v1',order_type='vendor_order',status='checkout' WHERE id=(SELECT order_id FROM payments WHERE id=:id)"), {'id': payment_id})
    with pytest.raises(RuntimeError, match='history exists'):
        with engine.begin() as conn:
            config.attributes['connection'] = conn
            command.downgrade(config, '0004')
    with engine.connect() as conn:
        assert conn.execute(text('SELECT count(*) FROM orders')).scalar_one() == 1
        assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '0014'


def test_latest_migration_can_rollback_one_revision_and_reapply(migration_database):
    """Prove latest reversible schema operations on an isolated disposable DB."""
    engine, config = migration_database
    migrate(engine, config, "head")
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.downgrade(config, "-1")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0013"
    migrate(engine, config, "head")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0014"


def test_locations_have_a_gist_spatial_index_after_migrations(migration_database):
    """Spatial proximity must be indexable, not a full-table scan."""
    engine, config = migration_database
    migrate(engine, config, "head")
    with engine.connect() as conn:
        indexes = conn.execute(text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE schemaname = current_schema() AND tablename = 'locations'"
        )).scalars().all()
    assert any("using gist" in definition.lower() and "geom" in definition.lower()
               for definition in indexes)


def test_order_status_check_rejects_incorrect_type_and_state(migration_database):
    """Database rejects direct invalid state writes even outside application APIs."""
    from sqlalchemy.exc import IntegrityError

    engine, config = migration_database
    migrate(engine, config, "head")
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO orders (id,order_number,order_type,buyer_user_id,seller_user_id,"
                "status,subtotal,delivery_fee,tax_amount,discount_amount,total_amount,currency) "
                "VALUES (:id,:number,'customer_order',:buyer,:seller,'in_transit',10,0,0,0,10,'NGN')"
            ), {"id": uuid.uuid4(), "number": "BAD-" + uuid.uuid4().hex[:16],
                "buyer": uuid.uuid4(), "seller": uuid.uuid4()})


def test_material_order_parent_link_is_constrained_and_downgrade_preserves_links(migration_database):
    """Material linkage cannot be assigned to a clothing order or silently dropped."""
    from sqlalchemy.exc import IntegrityError

    engine, config = migration_database
    migrate(engine, config, "head")
    with engine.begin() as conn:
        customer_id = uuid.uuid4()
        vendor_id = uuid.uuid4()
        for id_, number, kind, status in [
            (customer_id, "SAGA-" + uuid.uuid4().hex[:16], "customer_order", "paid"),
            (vendor_id, "SAGA-" + uuid.uuid4().hex[:16], "vendor_order", "checkout"),
        ]:
            conn.execute(text(
                "INSERT INTO orders (id,order_number,order_type,buyer_user_id,seller_user_id,"
                "status,subtotal,delivery_fee,tax_amount,discount_amount,total_amount,currency) "
                "VALUES (:id,:number,:kind,:buyer,:seller,:status,10,0,0,0,10,'NGN')"
            ), {"id": id_, "number": number, "kind": kind, "status": status,
                "buyer": uuid.uuid4(), "seller": uuid.uuid4()})
        conn.execute(text("UPDATE orders SET parent_customer_order_id=:parent WHERE id=:material"),
                     {"parent": customer_id, "material": vendor_id})
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text("UPDATE orders SET parent_customer_order_id=:parent WHERE id=:id"),
                         {"parent": vendor_id, "id": customer_id})
    # New 0011 is an empty audit migration in this scenario and can be
    # safely rolled back before testing the 0010 guarded parent removal.
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.downgrade(config, "0010")
    with pytest.raises(RuntimeError, match="Linked material orders"):
        with engine.begin() as conn:
            config.attributes["connection"] = conn
            command.downgrade(config, "-1")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0010"


def test_saga_audit_ledger_immutable_and_rollback_rejects_history(migration_database):
    from sqlalchemy.exc import DBAPIError

    engine, config = migration_database
    migrate(engine, config, "head")
    order_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO orders (id,order_number,order_type,buyer_user_id,seller_user_id,"
            "status,subtotal,delivery_fee,tax_amount,discount_amount,total_amount,currency)"
            " VALUES (:id,:number,'customer_order',:buyer,:seller,'pending',100,0,0,0,100,'NGN')"
        ), {"id": order_id, "number": "LED-" + uuid.uuid4().hex[:16],
            "buyer": uuid.uuid4(), "seller": uuid.uuid4()})
        conn.execute(text(
            "INSERT INTO saga_step_log (id,order_id,step_name,status,payload)"
            " VALUES (:id,:order_id,'PENDING_PAYMENT','completed','{}'::jsonb)"
        ), {"id": uuid.uuid4(), "order_id": order_id})
        for account, direction in (("sandbox_receivable", "debit"), ("sandbox_liability", "credit")):
            conn.execute(text(
                "INSERT INTO ledger_entries (id,order_id,event_key,account,direction,amount_minor)"
                " VALUES (:id,:order_id,'test-event',:account,:direction,10000)"
            ), {"id": uuid.uuid4(), "order_id": order_id,
                "account": account, "direction": direction})
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM ledger_entries WHERE order_id=:id"), {"id": order_id})
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(text("UPDATE saga_step_log SET status='failed' WHERE order_id=:id"), {"id": order_id})
    with pytest.raises(RuntimeError, match="audit records"):
        with engine.begin() as conn:
            config.attributes["connection"] = conn
            command.downgrade(config, "0010")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0014"
        assert conn.execute(text("SELECT count(*) FROM ledger_entries")).scalar_one() == 2
