#!/bin/sh

#
# start the supervisord inside 'FragMAX' conda environment
#

. /opt/conda/etc/profile.d/conda.sh
conda activate FragMAX
/usr/bin/supervisord --nodaemon --configuration /etc/supervisor/supervisord.conf
