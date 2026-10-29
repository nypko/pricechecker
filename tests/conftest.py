import pytest

from pricechecker import fx, run, site, terms


@pytest.fixture(scope="session")
def site_build(tmp_path_factory):
    """The real site built once per session from the saved config and prices, offline, into a temp dir."""
    out = tmp_path_factory.mktemp("site") / "build"
    stores, catalog = run.load_config()
    mp = pytest.MonkeyPatch()
    mp.setattr(site, "OUT", out)
    try:
        site.build(catalog, stores, fx.cached(), terms.saved_status())
    finally:
        mp.undo()
    return out
