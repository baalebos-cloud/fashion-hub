"""Authoritative catalog orders and address schema compatibility.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if connection.execute(sa.text('SELECT 1 FROM order_items i LEFT JOIN orders o ON o.id=i.order_id WHERE o.id IS NULL LIMIT 1')).first():
        raise RuntimeError('Orphan order items found; repair these records before upgrading. No data was removed.')
    op.create_foreign_key('fk_order_items_order_id', 'order_items', 'orders', ['order_id'], ['id'])
    for name, kind in [('pricing_source', sa.String(32)), ('request_fingerprint', sa.String(64)),
                       ('delivery_address_snapshot', postgresql.JSONB()), ('measurement_snapshot', postgresql.JSONB())]:
        op.add_column('orders', sa.Column(name, kind, nullable=True))
    op.add_column('payments', sa.Column('authorization_url', sa.String(2048), nullable=True))

    # Preserve legacy address fields and their contents. Nullable coordinates
    # permit a manually entered postal address without inventing GPS points.
    for name, kind in [('latitude', sa.Numeric(10, 7)), ('longitude', sa.Numeric(10, 7)),
                       ('formatted_address', sa.String(512)), ('state_region', sa.String(128))]:
        op.add_column('locations', sa.Column(name, kind, nullable=True))
    op.add_column('locations', sa.Column('location_type', sa.String(32), nullable=False, server_default='legacy'))
    op.execute('UPDATE locations SET formatted_address=address_line, state_region=state, latitude=ST_Y(geom::geometry), longitude=ST_X(geom::geometry)')
    op.alter_column('locations', 'address_line', existing_type=sa.String(512), nullable=True)
    op.alter_column('locations', 'state', existing_type=sa.String(128), nullable=True)


def downgrade():
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT 1 FROM orders WHERE pricing_source IS NOT NULL LIMIT 1")).first():
        raise RuntimeError('Catalog order snapshots exist; archive and explicitly migrate them before downgrading.')
    op.execute("UPDATE locations SET address_line=COALESCE(address_line,formatted_address,''), state=COALESCE(state,state_region,'')")
    op.alter_column('locations', 'address_line', existing_type=sa.String(512), nullable=False)
    op.alter_column('locations', 'state', existing_type=sa.String(128), nullable=False)
    for name in ['location_type', 'state_region', 'formatted_address', 'longitude', 'latitude']:
        op.drop_column('locations', name)
    op.drop_column('payments', 'authorization_url')
    for name in ['measurement_snapshot', 'delivery_address_snapshot', 'request_fingerprint', 'pricing_source']:
        op.drop_column('orders', name)
    op.drop_constraint('fk_order_items_order_id', 'order_items', type_='foreignkey')
