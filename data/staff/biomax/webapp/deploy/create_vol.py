#!/usr/bin/env python3

from contextlib import contextmanager
from tempfile import mkdtemp
from shutil import copyfile, rmtree
from os import path
import subprocess


RSA_KEY_FILE = "id_rsa"

SETUP_SCRIPT_NAME = "setup_vol.sh"
SETUP_SCRIPT = \
    """#!/bin/sh

# ssh key for HPC frontend
mkdir /volume/ssh
cp /init_volume/id_rsa /volume/ssh
chmod 0500 /volume/ssh
chmod 0600 /volume/ssh/id_rsa

# https certificate files
mkdir /volume/cert
cp /init_volume/fragmax.crt /volume/cert
cp /init_volume/fragmax.key /volume/cert

# django database dir
mkdir /volume/db

# set all files to be owned by biomax-service:MAX-Lab
chown -R 1990:1300 /volume
"""


@contextmanager
def temp_init_dir():
    def _copy_to_temp(filename):
        dest = path.join(temp_dir, filename)
        copyfile(filename, dest)

    # prepare
    temp_dir = mkdtemp(prefix="FMAX")

    # RSA key file
    _copy_to_temp(RSA_KEY_FILE)

    # HTTPS certificate files
    _copy_to_temp("fragmax.crt")
    _copy_to_temp("fragmax.key")

    # volume set-up script
    script = path.join(temp_dir, SETUP_SCRIPT_NAME)
    with open(script, "w") as f:
        f.write(SETUP_SCRIPT)

    yield temp_dir

    # remove
    rmtree(temp_dir)


with temp_init_dir() as temp_dir:
    print(f"working in {temp_dir}")
    cmd = [
        "docker", "run",
        "--mount", "source=fragmax,target=/volume",
        "--mount", f"type=bind,source={temp_dir},target=/init_volume",
        "-ti", "docker.maxiv.lu.se/fragmax",
        "sh", f"/init_volume/{SETUP_SCRIPT_NAME}"
    ]
    print(" ".join(cmd))
    subprocess.run(cmd)
