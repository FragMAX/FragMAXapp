#!/bin/bash

#
# start the jobsd daemon inside 'FragMAX' conda environment
#

. /fraghome/fragadm/miniconda3/etc/profile.d/conda.sh
conda activate FragMAX
./jobsd.py --cpu-limit 192
