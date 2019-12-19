#
# Make the celery magic work.
#
# This will make sure the app is always imported when Django starts
# so that @celery.task will use this app.
from .celery import app as celery_app

__all__ = ("celery_app",)
