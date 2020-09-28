# FragMAXapp
FragMAXapp for data processing and visualisation

Web application to plan fragment screening experiments, process data, visualize results and compare structures.

Uses [UglyMOL](http://uglymol.github.io/) for electron density visualisation
Uses CCP4, XDS, Phenix packages for data processing and analysis

## Application map

- Plan soaking for Crystal Shifter
- All in one solution: Pipedream
- Data processing using: XIA2/DIALS, XIA2/XDS.XSCALE, XDSAPP, autoPROC
- Structure Solving/Refinement: Dimple, BUSTER, FSpipeline
- Ligand fitting: RhoFit, Phenix LigFit

Dataset analysis with Pandda

## Site Deployment

The FragMAX webapp supports customization for different sites via the `site-plugins` architecture.
The site specific behaviour is implemented by the code provided by the selected site-plugin python module.
For more details on the `site plugin` architecture see the [site plugins](site_plugins.md) documentation.

### Site Plugin Configuration

The site-plugin that will be used by the application is configured by creating `local_site.py` file in the root of the application.
This file must define SITE variable, which is a string representation of the site-plugin to load.
For example, following file configures to use MAXIV site-plugin:

    SITE = "MAXIV"

The 'deploy/local_site.py-maxiv' file in this repository, is an example on how to select "MAXIV" site-plugin.

Currently supported sites are "MAXIV" and "HZB".

## Site specific settings

All application settings defined in fragmax.settings can be overriden by creating the `site_settings.py` file in the root of the application.
The `site_settings.py` is used to define site specific settings for deployment at different sites.

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

