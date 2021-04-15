#!/bin/bash

#
# start the jobsd daemon inside 'FragMAX' conda environment
#

. /soft/pxsoft/64/pymol_2.1/etc/profile.d/conda.sh
conda activate FragMAX
./jobsd.py --cpu-limit 192
