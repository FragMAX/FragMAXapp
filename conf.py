from pathlib import Path

#
# setting that are shared between multiple processes
# and/or settings we need to change at different deployment set-ups
#

# If true, django et al will run with debug features enabled
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# URL for accessing redis service
REDIS_URL = "redis://localhost"

# absolute path to the directory for database related files
DATABASE_DIR = str(Path(Path(__file__).parent, "db").absolute())

# absolute path to the directory where projects database files are stored
PROJECTS_DB_DIR = Path(DATABASE_DIR, "projs")

# path where project files will be stored
# NOTE: this must be configured via local_conf.py module
PROJECTS_ROOT_DIR: Path

# path to jobsd requests socket
JOBSD_SOCKET = str(Path(DATABASE_DIR, "jobsd.sock"))

# SLURM front-end host ssh settings
SLURM_FRONT_END = {
    "host": "clu0-fe-0",
    "user": "biomax-service",
    "key_file": "/volume/ssh/id_rsa",
}

# path crystal snapshot pictures root directory
SNAPSHOTS_ROOT_DIR = Path("/", "data", "staff", "ispybstorage", "pyarch", "visitors")

#
# Sets UI visual style to represent deployment type.
#
# This is used to minimize the risk of confusing for example
# production instance of the application with testing set-up.
#
# Valid values are:
#
# 'production' - production deployment
# 'test'       - testing deploymnet
# 'dev'        - development deployment
#
DEPLOYMENT_TYPE = "dev"

# load set-up specific settings
from local_conf import *  # noqa F403, F401
