#!/bin/sh

#
# make mtzdmp command available
#
export MX_SOFT=/mxn/groups/biomax/wmxsoft
. /mxn/groups/biomax/wmxsoft/env_setup/ccp4_env.sh


#
# start the supervisord inside 'FragMAX' conda environment
#

. /opt/conda/etc/profile.d/conda.sh
conda activate FragMAX
/usr/bin/supervisord --nodaemon --configuration /etc/supervisor/supervisord.conf