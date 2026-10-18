"""Owned carts, catalog integrity and durable stock reservations."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

LINKS = [
    ('vendors', 'user_id', 'users'), ('vendor_products', 'vendor_id', 'vendors'),
    ('product_variants', 'product_id', 'vendor_products'),
    ('inventory', 'product_variant_id', 'product_variants'),
    ('carts', 'owner_user_id', 'users'), ('cart_items', 'cart_id', 'carts'),
    ('cart_items', 'product_variant_id', 'product_variants'),
    ('cart_items', 'vendor_id', 'vendors'),
]


def upgrade():
    bind = op.get_bind()
    for table, column, target in LINKS[:-1]:
        if bind.execute(sa.text(f'SELECT 1 FROM {table} c LEFT JOIN {target} p ON p.id=c.{column} WHERE p.id IS NULL LIMIT 1')).first():
            raise RuntimeError(f'Orphan {table}.{column} records require repair before upgrading; no data was removed.')
    for sql, message in [
        ("SELECT 1 FROM carts WHERE status='active' GROUP BY owner_user_id HAVING count(*)>1", 'Duplicate active carts'),
        ('SELECT 1 FROM cart_items GROUP BY cart_id,product_variant_id HAVING count(*)>1', 'Duplicate cart lines'),
        ('SELECT 1 FROM cart_items WHERE quantity NOT BETWEEN 1 AND 10000', 'Invalid cart quantities'),
        ('SELECT 1 FROM inventory WHERE quantity_available<0 OR quantity_reserved<0 OR quantity_available+quantity_reserved>1000000000', 'Invalid stock counters'),
        ('SELECT 1 FROM inventory WHERE quantity_reserved<>0', 'Unattributed legacy reserved stock'),
    ]:
        if bind.execute(sa.text(sql)).first():
            raise RuntimeError(message + '; explicitly reconcile these records before upgrading.')
    # The old cart service used product IDs as vendor IDs. Resolve the real
    # business profile deterministically; the product/variant guards ran above.
    op.execute('UPDATE cart_items c SET vendor_id=p.vendor_id FROM product_variants v JOIN vendor_products p ON p.id=v.product_id WHERE c.product_variant_id=v.id')
    for table, column, target in LINKS:
        op.create_foreign_key(f'fk_{table}_{column}', table, target, [column], ['id'])
    op.add_column('carts', sa.Column('revision', sa.Integer(), nullable=False, server_default='0'))
    op.create_check_constraint('ck_cart_revision', 'carts', 'revision >= 0')
    op.create_index('uq_cart_active_owner', 'carts', ['owner_user_id'], unique=True, postgresql_where=sa.text("status='active'"))
    op.create_unique_constraint('uq_cart_variant', 'cart_items', ['cart_id', 'product_variant_id'])
    op.create_check_constraint('ck_cart_item_quantity', 'cart_items', 'quantity BETWEEN 1 AND 10000')
    op.create_check_constraint('ck_inventory_counters', 'inventory', 'quantity_available>=0 AND quantity_reserved>=0 AND quantity_available+quantity_reserved<=1000000000')
    op.add_column('orders', sa.Column('source_cart_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_orders_source_cart_id', 'orders', 'carts', ['source_cart_id'], ['id'])
    op.add_column('orders', sa.Column('reservation_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_orders_active_reservation_expiry', 'orders', ['reservation_expires_at', 'id'], postgresql_where=sa.text("order_type='vendor_order' AND pricing_source='vendor_catalog_v1' AND status IN ('checkout','payment_pending')"))
    op.create_table('stock_reservations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('product_variant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('product_variants.id'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('order_id', 'product_variant_id', name='uq_reservation_order_variant'),
        sa.CheckConstraint('quantity > 0', name='ck_reservation_quantity'),
        sa.CheckConstraint("status IN ('active','consumed','released')", name='ck_reservation_status'),
    )
    op.create_index('ix_stock_reservations_order_id', 'stock_reservations', ['order_id'])
    op.create_index('ix_stock_reservations_product_variant_id', 'stock_reservations', ['product_variant_id'])


def downgrade():
    bind = op.get_bind()
    if bind.execute(sa.text('SELECT 1 FROM stock_reservations LIMIT 1')).first() or bind.execute(sa.text("SELECT 1 FROM orders WHERE pricing_source='vendor_catalog_v1' LIMIT 1")).first():
        raise RuntimeError('Stock reservation history exists; preserve it with a reviewed forward migration.')
    op.drop_table('stock_reservations')
    op.drop_index('ix_orders_active_reservation_expiry', table_name='orders')
    op.drop_column('orders', 'reservation_expires_at')
    op.drop_constraint('fk_orders_source_cart_id', 'orders', type_='foreignkey')
    op.drop_column('orders', 'source_cart_id')
    op.drop_constraint('ck_inventory_counters', 'inventory', type_='check')
    op.drop_constraint('ck_cart_item_quantity', 'cart_items', type_='check')
    op.drop_constraint('uq_cart_variant', 'cart_items', type_='unique')
    op.drop_index('uq_cart_active_owner', table_name='carts')
    op.drop_constraint('ck_cart_revision', 'carts', type_='check')
    op.drop_column('carts', 'revision')
    for table, column, target in reversed(LINKS):
        op.drop_constraint(f'fk_{table}_{column}', table, type_='foreignkey')
