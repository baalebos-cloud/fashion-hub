"""Provider URI compatibility and credential-safe boot failures; no live DB."""
import os
from pathlib import Path
import subprocess
import sys
import traceback

import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from app.core.config import Settings


@pytest.mark.parametrize('scheme', ['postgres', 'postgresql', 'postgresql+psycopg'])
@pytest.mark.parametrize('port', ['', ':5432', ':6543'])
def test_provider_urls_select_psycopg_and_preserve_destination_and_ssl(scheme, port):
    value = f'{scheme}://buyer:p%40ss%3Aword@db.example{port}/fashion?sslmode=require&application_name=fashion-hub'
    settings = Settings(_env_file=None, DATABASE_URL=value)
    parsed = make_url(settings.DATABASE_URL)
    assert parsed.drivername == 'postgresql+psycopg'
    assert parsed.host == 'db.example' and parsed.database == 'fashion'
    assert parsed.username == 'buyer' and parsed.password == 'p@ss:word'
    assert parsed.port == (int(port[1:]) if port else None)
    assert parsed.query == {'sslmode': 'require', 'application_name': 'fashion-hub'}


@pytest.mark.parametrize('value', [
    'postgresql://user:private-test-password@db.example:/fashion',
    'postgresql://user:private-test-password@db.example:abc/fashion',
    'postgresql://user:private-test-password@db.example:0/fashion',
    'postgresql://user:private-test-password@db.example:65536/fashion',
    'postgresql://user:private-test-password@db.example:5432/',
    'postgresql://user:private-test-password@extra@db.example:5432/fashion',
    'postgresql+psycopg2://user:private-test-password@db.example:5432/fashion',
    'mysql://user:private-test-password@db.example:3306/fashion',
    '${{Postgres.DATABASE_URL}}',
    '',
])
def test_invalid_configuration_fails_without_echoing_url_or_credentials(value):
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, DATABASE_URL=value)
    rendered = ''.join(traceback.format_exception(error.value))
    assert 'DATABASE_URL' in rendered
    assert 'private-test-password' not in rendered
    assert 'db.example' not in rendered
    assert 'input_value' not in rendered


def test_settings_repr_does_not_expose_database_credentials():
    settings = Settings(_env_file=None, DATABASE_URL='postgresql://user:private-test-password@db.example/fashion')
    assert 'private-test-password' not in repr(settings)
    assert 'db.example' not in repr(settings)


def test_invalid_environment_stops_import_with_actionable_redacted_error():
    environment = {**os.environ, 'DATABASE_URL': 'postgresql://user:boot-password-marker@db.invalid:/fashion'}
    result = subprocess.run(
        [sys.executable, '-c', 'import app.main'], env=environment,
        cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, timeout=20,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert 'DATABASE_URL' in output and 'numeric port' in output
    assert 'boot-password-marker' not in output and 'db.invalid' not in output
    assert 'invalid literal for int()' not in output


def test_provider_style_url_imports_with_installed_driver_without_connecting():
    environment = {**os.environ, 'DATABASE_URL': 'postgresql://user:placeholder@db.invalid:5432/fashion?sslmode=require'}
    result = subprocess.run(
        [sys.executable, '-c', 'from app.core.database import engine; assert engine.dialect.driver == "psycopg"'],
        env=environment, cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0
