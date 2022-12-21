#!/bin/bash

#
# start the supervisord inside 'FragMAX' conda environment
#

eval "$(micromamba shell hook --shell=bash)"
micromamba activate FragMAX
/usr/bin/supervisord --nodaemon --configuration /etc/supervisor/supervisord.conf
