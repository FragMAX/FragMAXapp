#!/bin/sh
. /mxn/groups/biomax/wmxsoft/phenix/build/setpaths.sh

# set HOME variable, otherwise we get problems running phenix.elbow
HOME=/home/fragmax-service
celery -A fragmax worker --uid 91121 --gid 1300 --loglevel=info
