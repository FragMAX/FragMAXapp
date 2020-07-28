# FragMAX_WebApp
FragMAX webapp for data processing and visualisation

Web application to plan fragment screening experiments, process data, visualize results and compare structures.

Uses [UglyMOL](http://uglymol.github.io/) for electron density visualisation
Uses CCP4, XDS, Phenix packages for data processing and analysis

## Application map

- Plan soaking for Crystal Shifter
- Data processing using: XIA2/DIALS, XIA2/XDS.XSCALE, XDSAPP, autoPROC
- Structure Solving/Refinement: Dimple, BUSTER, FSpipeline
- Ligand fitting: RhoFit, Phenix LigFit

Dataset analysis with Pandda

## Deployment

### Site specific settings

All application settings defined in fragmax.settings can be overriden by creating the file `site_settings.py` in the root of the application.
The `site_settings.py` is used to define site specific settings for deployment at different sites.

### Authentication

FragMAX app supports authentication using local user database or DUO/ISPyB system.
The authentication used is controlled by the AUTHENTICATION_BACKENDS setting.

#### ISPyB Authentication

The DUO/ISPyB authentication is implemented by _fragview.auth.ISPyBBackend_ authentication back-end.
Add the back-end to AUTHENTICATION_BACKENDS list to enable it, for example:

    AUTHENTICATION_BACKENDS = [
        "fragview.auth.ISPyBBackend"
    ]

The ISPyBBackend will use ISPyB REST API to check the login credentials.
See the fragview.auth.ISPyBBackend module's documentation for details on how to confgure ISPyB authentication.

#### Local Authentication

To implement a stand-alone FragMAX user accounts, use the _fragview.auth.LocalBackend_ authentication back-end.
Add the back-end to AUTHENTICATION_BACKENDS list to enable it, for example:

    AUTHENTICATION_BACKENDS = [
        "fragview.auth.LocalBackend"
    ]

The LocalBackend will use the site's django database to store user names and password.
To manage the local accounts use the manage.py commands.

User can be added with `manage.py add` command:

    ./manage.py adduser <user_name>

The command will prompt for the password.

To change an existing user's password use `manage.py changepassword` command:

    ./manage.py changepassword <user_name>

The command will prompt for the new password.

## Development

### Components

The FragMAX webapp consists of 3 major components:

 * Web Application
 * Workers Threads
 * Redis Server

The _Web Application_ component implements the UI part of the FragMAX.
It is build on top of Django framework, and serves the web-requests.

The _Worker Threads_ component handles performing long running tasks, not suitable to be performed on web-request threads.
Note that the heavy data processing is performed on an HPC cluster, thus the worker threads are not involved.

The _Redis Server_ is used for communication between the web-request and worker threads.

### Dependencies

The required python package are listed in `environment.yml` file.

### Set-up with conda

Follow steps below to set-up an environments for running FragMAX webapp using conda.

- use you prefered method for installing [conda](https://docs.conda.io/en/latest/)
- clone this repository

    git clone <repo-url> <src-dir>

- create conda environment 'FragMAX'

    conda env create -f <src-dir>/environment.yml

The conda environment 'FragMAX' will contain all required package for FragMAX webapp.

### Running the Webapp

To run FragMAX application the _Web Application_, _Workers Threads_ and _Redis Server_ components must be started.
Each component runs in it's own separate process.

To start _Redis Server_ activate 'FragMAX' environment and run:

    redis-server

To start _Workers Threads_ activate 'FragMAX' environment and run:

    celery -A fragmax worker --loglevel=info

The '--loglevel' argument specifies log verbosity.

To start _Web Application_ activate 'FragMAX' environment and run:

    ./manage.py runserver

