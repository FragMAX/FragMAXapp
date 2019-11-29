#!/bin/sh

# script to run DB migrations as root user
# after migration is performed, change
# db files owner and groupd to biomax-service and MAX-Lab

python3 ./manage.py migrate
chown 1990:1300 db/db.sqlite3
