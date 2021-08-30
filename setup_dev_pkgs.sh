#!/bin/sh

#
# install package used for development and CI checks
#

conda install --channel conda-forge \
    black=21.8b0 \
    flake8=3.9.2 \
    mypy==0.910 \
    types-requests=2.25.1 \
    types-redis=3.5.2 \
    types-python-dateutil=0.1.6 \
    types-pyyaml=5.4.8
