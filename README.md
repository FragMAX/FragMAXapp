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

If all goes well, the conda environment called 'FragMAX' will contain all required package for the webapp.

