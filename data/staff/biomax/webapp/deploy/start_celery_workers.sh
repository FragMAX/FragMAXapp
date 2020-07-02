#!/bin/sh
. /mxn/groups/biomax/wmxsoft/phenix/build/setpaths.sh

# set HOME variable, otherwise we get problems running phenix.elbow
HOME=/home/biomax-service
celery -A fragmax worker --uid 1990 --gid 1300 --loglevel=info
