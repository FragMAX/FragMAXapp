from importlib import import_module
from fragview.sites.plugin import SitePlugin


def _load_site_plugin():
    import local_site

    try:
        site_module = import_module(f"fragview.sites.{local_site.SITE.lower()}")
    except ModuleNotFoundError as e:
        raise ValueError(f"Error loading site-plugin for '{local_site.SITE}': {e}")

    return site_module.SitePlugin()


SITE: SitePlugin = _load_site_plugin()
