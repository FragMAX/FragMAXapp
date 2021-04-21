# Components

The FragMAX webapp consists of following major components:

 * Web Application
 * Workers Threads
 * Redis Server
 * Jobs Manager

For details of each component see the [Architecture](architecture.md) description.

# Dependencies

The required python package are listed in `environment.yml` file.

## Set-up with conda

Follow steps below to set-up an environments for running FragMAX webapp using conda.

- use you prefered method for installing [conda](https://docs.conda.io/en/latest/)
- clone this repository

    git clone <repo-url> <src-dir>

- create conda environment 'FragMAX'

    conda env create -f <src-dir>/environment.yml

The conda environment 'FragMAX' will contain all required packages for FragMAX webapp.

# Running the Webapp

To run FragMAX application the _Web Application_, _Workers Threads_, _Redis Server_ and _Jobs Manager_ components must be started.
Each component runs in it's own separate process.

To start _Redis Server_ activate 'FragMAX' environment and run:

    redis-server

To start _Workers Threads_ activate 'FragMAX' environment and run:

    celery -A fragmax worker --loglevel=info

The '--loglevel' argument specifies log verbosity.

To start _Jobs Manager_ activate 'FragMAX' environment and run:

    ./jobsd.py

To start _Web Application_ activate 'FragMAX' environment and run:

    ./manage.py runserver
