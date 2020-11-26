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

# Acknowledgement

FragMAXapp uses many scientific software packages from multiple developers for its purposes.
Each of these packages should be cited independently when publishing your results.

Here is a non-exhaustive alphabetically-ordered list of software used by FragMAXapp, Developers, citation and links for original documentation.

|Software|Developer|Links|
|---|---|---|
|autoPROC|[Global Phasing](https://www.globalphasing.com/)|- [Documentation](https://www.globalphasing.com/autoproc/)<br>- [How to cite](https://www.globalphasing.com/autoproc/wiki/index.cgi?CitingAutoPROC)|
|BUSTER|[Global Phasing](https://www.globalphasing.com/)|- [Documentation](https://www.globalphasing.com/buster/)<br>- [How to cite](http://www.globalphasing.com/buster/wiki/index.cgi?BusterCite)|
|CCP4 suite|[CCP4](https://www.ccp4.ac.uk/)|[How to cite](http://legacy.ccp4.ac.uk/html/REFERENCES.html)|
|Crystal Shifter|[OxfordLabTech](https://oxfordlabtech.com/shifter/)|-|
|DIALS|[DIALS](https://dials.github.io/)|[How to cite](http://scripts.iucr.org/cgi-bin/paper?S2059798317017235)|
|DIMPLE|[DIMPLE](https://ccp4.github.io/dimple/)|[How to cite](http://cloud.ccp4.ac.uk/manuals/html-taskref/doc.task.Dimple.html)|
|fspipeline|[FS @ HZB](https://www.helmholtz-berlin.de/forschung/oe/np/gmx/fragment-screening/index_en.html)|[How to cite](https://pubmed.ncbi.nlm.nih.gov/27452405/)|
|Gemmi|[gemmi @ PyPi](https://pypi.org/project/gemmi/)|-|
|PanDDA|[PanDDA](https://pandda.bitbucket.io/)|[How to cite](https://doi.org/10.1038/ncomms15123)|
|Pipedream|[Global Phasing](https://www.globalphasing.com/)|- [Documentation](https://www.globalphasing.com/buster/manual/pipedream/manual/index.html/)<br>- [How to cite](https://www.globalphasing.com/buster/manual/pipedream/manual/index.html#_how_to_cite_use_of_pipedream)|
|Phenix suite|[Phenix](https://www.phenix-online.org/)|[How to cite](https://www.phenix-online.org/documentation/reference/citations.html)|
|RhoFit|[Global Phasing](https://www.globalphasing.com/)|- [Documentation](https://www.globalphasing.com/buster/manual/rhofit/manual/)<br>- [How to cite](https://www.globalphasing.com/buster/manual/rhofit/manual/#cite)|
|XDS|[XDS](http://xds.mpimf-heidelberg.mpg.de/)|[How to cite](http://scripts.iucr.org/cgi-bin/paper?S0907444909047337)|
|XDSAPP|[HZB](https://www.helmholtz-berlin.de/)|[How to cite](https://www.helmholtz-berlin.de/forschung/oe/np/gmx/xdsapp/index_en.html)|
|XIA2|[XIA2](https://xia2.github.io/)|[How to cite](https://xia2.github.io/acknowledgements.html#id4)|

If you find a missing reference in this list, please let us know by creating a new issue or emailing the devs. 
