from pathlib import Path

#
# setting shared between multiple processes
#
# for example redis settings are used
# by django webapp and celery worker processes
#

# URL for accessing redis service
REDIS_URL = "redis://localhost"

# absolute path to the directory for database related files
DATABASE_DIR = str(Path(Path(__file__).parent, "db").absolute())

# path to jobsd requests socket
JOBSD_SOCKET = str(Path(DATABASE_DIR, "jobsd.sock"))

# SLURM front-end host ssh settings
SLURM_FRONT_END = {
    "host": "clu0-fe-0",
    "user": "biomax-service",
    "key_file": "/volume/ssh/id_rsa",
}

# maximum number of jobs jobsd
# will allow to run at the same time
JOBSD_MAX_JOBS = 128
