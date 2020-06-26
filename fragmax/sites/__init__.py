def params():
    import importlib
    from django.conf import settings

    return importlib.import_module(f"fragmax.sites.{settings.SITE}")
