#!/bin/sh

# script to run DB migrations as root user
# after migration is performed, change
# db files owner and groupd to biomax-service and MAX-Lab

. /opt/conda/etc/profile.d/conda.sh
conda activate FragMAX
python3 ./manage.py migrate
chown 1990:1300 db/db.sqlite3
