from importlib import import_module
from fragview.sites.plugin import SitePlugin


def get_site_name() -> str:
    import local_site

    return local_site.SITE.lower()


def _load_site_plugin():
    site_name = get_site_name()
    try:
        site_module = import_module(f"fragview.sites.{site_name}")
    except ModuleNotFoundError as e:
        raise ValueError(f"Error loading site-plugin for '{site_name}': {e}")

    return site_module.SitePlugin()


SITE: SitePlugin = _load_site_plugin()
