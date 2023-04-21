#!/bin/sh

#
# install package used for development and CI checks
#

micromamba install --channel conda-forge \
    black=22.3.0 \
    flake8=3.9.2 \
    coverage=6.5.0 \
    mypy=1.2.0 \
    types-requests=2.25.1 \
    types-redis=3.5.2 \
    types-python-dateutil=0.1.6 \
    types-pyyaml=5.4.8
