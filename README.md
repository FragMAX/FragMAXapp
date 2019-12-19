# FragMAX_WebApp
FragMAX webapp for data processing and visualisation


Django application to plan fragment screening experiments, process data, visualise results and compare structures. 

Uses [UglyMOL](http://uglymol.github.io/) for electron density visualisation
Uses CCP4, XDS, Phenix packages for data processing and analysis

## Application map

- Plan soaking for Crystal Shifter
- Data processing using: XIA2/DIALS, XIA2/XDS.XSCALE, XDSAPP, autoPROC
- Structure Solving/Refinement: Dimple, BUSTER, FSpipeline
- Ligand fitting: RhoFit, Phenix LigFit

Dataset analysis with Pandda



## Dependencies

See environment.yml and requirements.txt files.

## Set-up with conda

Follow steps below to set-up an environment for running FragMAX webapp using conda.

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

The '--concurrency' argument specifies number of worker threads to use.
The '--loglevel' argument specifies log verbosity.

To start _Web Application_ activate 'FragMAX' environment and run:

    ./manage.py runserver


