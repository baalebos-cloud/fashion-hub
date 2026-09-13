import os
import sys
from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.core.database import Base
# Import all models so Alembic registers them in Base.metadata
import app.models  # noqa: F401

target_metadata = Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Intercept database string and force container mapping parameter channels
db_url = settings.DATABASE_URL
if ":5432/" in db_url:
    db_url = db_url.replace(":5432/", ":5433/")
elif "@localhost/" in db_url or "@127.0.0.1/" in db_url:
    # Handle implicit ports by injecting 5433 explicitly
    db_url = db_url.replace("@localhost/", "@127.0.0.1:5433/").replace("@127.0.0.1/", "@127.0.0.1:5433/")

# Fallback mechanism if settings fall out of scope
if not db_url or "driver://" in db_url:
    db_url = "postgresql+psycopg://fashionhub:fashionhub@127.0.0.1:5433/fashionhub"


def include_object(object, name, type_, reflected, compare_to):
    """Filter out PostGIS system, topology, and tiger geocoder tables."""
    if type_ == "table":
        # Exact PostGIS/Topology/Tiger system tables
        postgis_tables = {
            "spatial_ref_sys", "geometry_columns", "geography_columns",
            "raster_columns", "raster_overviews", "topology", "layer",
            "geocode_settings", "geocode_settings_default"
        }
        if name in postgis_tables:
            return False

        # Prefixes used by Tiger Geocoder and related extensions
        ignored_prefixes = (
            "tiger", "topology", "zip_", "addr", "county", "state",
            "place", "cousub", "edges", "faces", "featnames", "loader_",
            "pagc_", "street_", "secondary_", "direction_", "tabblock",
            "tract", "zcta5", "bg", "geocode_"
        )
        if any(name.startswith(p) for p in ignored_prefixes):
            return False

    return True


def run_migrations_offline() -> None:
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        db_url,
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
