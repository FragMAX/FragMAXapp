# import tasks here to make them visible to celery
from .diffractions import get_diffraction  # noqa E402
from .ccp4 import mtz_to_map  # noqa E402
from .project import setup_project_files  # noqa E402