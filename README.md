# FragMAXapp

The FragMAXapp is a web application for processing and visualisation of macromolecular crystallography data,
with the focus on fragment screening campaigns.

The application manages processing of diffraction images collected from many crystals in a highly automated style.
It supports analysing data with many of the standard MX software packages.
The data can be processed with CCP4, XDS, Phenix and PanDDa software.

The computed electron density maps can be viewed directly in the app with [UglyMOL](http://uglymol.github.io/) based viewer.

## Processing Support

- Data processing using: XIA2/DIALS, XIA2/XDS.XSCALE, XDSAPP, autoPROC
- Structure Solving/Refinement: Dimple, FSpipeline
- Ligand fitting: RhoFit, Phenix LigFit
- Dataset analysis with Pandda

## Availability

The FragMAXapp is currently available for users of MX beamlines at
[MAX IV](https://www.maxiv.lu.se/accelerators-beamlines/beamlines/biomax/) and
[HZB](https://www.helmholtz-berlin.de/) facilities.

More information on using the application is available [here](https://fragmax.github.io/).

## Site Customization

The FragMAXapp is designed to be customizable for different research facilities.
The customization is supported via the `site-plugins` architecture.
To adapt the FragMAXapp for a new deployment site, a plugin module can be developed.
The `site-plugin` implements site specific details and configuration.
For more details on writing plugins see the [site plugins](docs/site_plugins.md) documentation.

# Managing

[Operating FragMAXapp](docs/operation.md) document contains some useful information on managing and running a deploymnet of the application.

# Development

The overview of the app's structure is described in the [Architecture](docs/architecture.md) document.
The details on setting up development environment are available in the [Hacking](docs/hacking.md) guide.

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
|Phenix suite|[Phenix](https://www.phenix-online.org/)|[How to cite](https://www.phenix-online.org/documentation/reference/citations.html)|
|RhoFit|[Global Phasing](https://www.globalphasing.com/)|- [Documentation](https://www.globalphasing.com/buster/manual/rhofit/manual/)<br>- [How to cite](https://www.globalphasing.com/buster/manual/rhofit/manual/#cite)|
|XDS|[XDS](http://xds.mpimf-heidelberg.mpg.de/)|[How to cite](http://scripts.iucr.org/cgi-bin/paper?S0907444909047337)|
|XDSAPP|[HZB](https://www.helmholtz-berlin.de/)|[How to cite](https://www.helmholtz-berlin.de/forschung/oe/np/gmx/xdsapp/index_en.html)|
|XIA2|[XIA2](https://xia2.github.io/)|[How to cite](https://xia2.github.io/acknowledgements.html#id4)|

If you find a missing reference in this list, please let us know by creating a new issue or emailing the devs. 
