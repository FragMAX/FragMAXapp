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
