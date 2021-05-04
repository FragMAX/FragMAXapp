"""
WSGI config for fragmax project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/howto/deployment/wsgi/
"""
from os import environ
from django.core.wsgi import get_wsgi_application
from pony.orm import db_session

environ.setdefault('DJANGO_SETTINGS_MODULE', 'fragmax.settings')

# wrap the whole app into a pony orm database session,
# this way we can always access database from all ports of the app
application = db_session(get_wsgi_application())
