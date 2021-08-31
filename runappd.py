#!/usr/bin/env python3
"""
A script to run all the daemons for the FragMAX application inside a
specified conda environment.

This is used when deploying FragMAX app using conda environment and systemd
for services management.

This script is invoked by the systemd service unit to start and stop the
FragMAX application.

On start, django webserver, redis, jobsd and celery worker daemons will be started.
This script will block, waiting for SIGTERM. Once the SIGTERM is received,
the daemons started will be terminated with SIGTERM.
"""

import os
import sys
import subprocess
import signal
import argparse
from os import path

CONDA_ENV = "FragMAX"

got_exit_signal = False


def parse_args():
    def conda_env_dir(dir_path):
        if not path.isdir(dir_path):
            raise argparse.ArgumentTypeError("%s: invalid directory path" % dir_path)

        return dir_path

    parser = argparse.ArgumentParser(
        description="run all FragMAX daemons inside conda environment"
    )

    parser.add_argument(
        "conda_env_dir",
        type=conda_env_dir,
        help="full path to conda environment directory",
    )

    return parser.parse_args().conda_env_dir


def current_dir():
    return path.abspath(path.dirname(__file__))


def python_path(conda_env_dir):
    """
    derive absolute path to python binary
    """
    return path.join(conda_env_dir, "bin", "python")


def start_redis(conda_env_dir):
    # derive absolute path to redis-server binary
    redis_server = path.join(conda_env_dir, "bin", "redis-server")

    return subprocess.Popen([redis_server], cwd=current_dir())


def start_jobsd():
    cur_dir = current_dir()
    return subprocess.Popen(
        [path.join(cur_dir, "deploy", "start_jobsd.sh")],
        cwd=cur_dir,
    )


def start_webserver(conda_env_dir):
    return subprocess.Popen(
        [python_path(conda_env_dir), "manage.py", "runserver", "0.0.0.0:8080"],
        cwd=current_dir(),
    )


def start_celery(conda_env_dir):
    # derive absolute path to celery binary
    celery = path.join(conda_env_dir, "bin", "celery")
    return subprocess.Popen(
        [celery, "-A", "fragmax", "worker", "--concurrency=4", "--loglevel=info"],
        cwd=current_dir(),
    )


def signals_handler(*_):
    global got_exit_signal
    got_exit_signal = True


def main():
    global got_exit_signal
    conda_env_dir = parse_args()

    # on TERM and INTERRUPT (Ctrl+C) signals,
    # terminate all started processes and exit
    signal.signal(signal.SIGTERM, signals_handler)
    signal.signal(signal.SIGINT, signals_handler)

    # start all daemons
    redis = start_redis(conda_env_dir)
    jobsd = start_jobsd()
    webserver = start_webserver(conda_env_dir)
    celery = start_celery(conda_env_dir)

    # wait for exit signals
    while not got_exit_signal:
        signal.pause()

    print("got exit signal, terminating daemons")

    # first terminate webserver, celery and jobsd, and keep
    # redis running, as redis should go down last
    celery.send_signal(signal.SIGTERM)
    webserver.send_signal(signal.SIGTERM)
    jobsd.send_signal(signal.SIGTERM)
    jobsd.wait()
    webserver.wait()
    celery.wait()

    # finally terminate redis
    redis.send_signal(signal.SIGTERM)
    redis.wait()

    print("all done, auf Wiedersehen")

    # check if any of the daemons existed with an error
    for proc in [redis, webserver, celery]:
        if proc.returncode != os.EX_OK:
            # signal that something went wrong
            return 1

    return 0  # all is good


sys.exit(main())
