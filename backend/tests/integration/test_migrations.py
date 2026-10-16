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


@pytest.mark.parametrize("previous", [None, "0001", "035e1bd61029", "0002", "2ab23f38e9c6"])
def test_fresh_and_historical_upgrades_preserve_records(migration_database, previous):
    engine, config = migration_database
    if previous:
        migrate(engine, config, previous)
    user_id = uuid.uuid4()
    if previous in {"035e1bd61029", "0002", "2ab23f38e9c6"}:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO users (id,email,hashed_password,full_name,role,is_active,is_email_verified,is_phone_verified,timezone) VALUES (:id,'preserved@example.com','test','Preserved','customer',true,false,false,'UTC')"), {"id": user_id})
    migrate(engine, config, "head")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0003"
        assert {"users", "payouts", "referrals", "payment_outbox"} <= set(inspect(conn).get_table_names())
        assert str(next(x for x in inspect(conn).get_columns("payment_transactions") if x["name"] == "processed")["type"]) == "BOOLEAN"
        if previous in {"035e1bd61029", "0002", "2ab23f38e9c6"}:
            assert conn.execute(text("SELECT full_name FROM users WHERE id=:id"), {"id": user_id}).scalar_one() == "Preserved"
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
