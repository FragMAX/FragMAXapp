#!/bin/sh

CUR_DIR=$(dirname $0)

module purge
module load GCCcore/8.3.0 Python/3.7.4
$CUR_DIR/crypt_files.py $*
module purge
