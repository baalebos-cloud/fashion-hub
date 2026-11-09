"""FRONTEND_URL is the site's root, so emailed and shared links point at real pages."""
import pytest

from app.core.config import Settings


@pytest.mark.parametrize("value", [
    "https://fashion-hub-tawny.vercel.app",
    "https://fashion-hub-tawny.vercel.app/",
    "https://fashion-hub-tawny.vercel.app/app",
    "https://fashion-hub-tawny.vercel.app/app/",
    " https://fashion-hub-tawny.vercel.app/app/ ",
])
def test_the_signed_in_area_link_counts_as_the_site(value):
    assert Settings(_env_file=None, FRONTEND_URL=value).FRONTEND_URL == "https://fashion-hub-tawny.vercel.app"


def test_other_paths_are_left_alone():
    assert Settings(_env_file=None, FRONTEND_URL="https://example.com/shop/").FRONTEND_URL == "https://example.com/shop"
