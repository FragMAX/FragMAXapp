# import tasks here to make them visible to celery
from .diffractions import make_diffraction_jpeg  # noqa E402
from .project import setup_project  # noqa E402
from .project import import_crystals  # noqa E402
