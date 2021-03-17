import os
import time
import threading
from os import path
from django.shortcuts import render
from django.http import HttpResponseBadRequest
from fragview.projects import current_project, project_script, dataset_xml_file
from fragview.projects import project_process_protein_dir, project_log_path, dataset_master_image
from fragview import versions
from fragview.filters import get_proc_datasets
from fragview.forms import ProcessForm
from fragview.xsdata import XSDataCollection
from fragview.views.utils import add_update_status_script_cmds
from fragview.sites import SITE
from fragview.sites.plugin import Duration, DataSize
from fragview.pipeline_commands import get_xia_dials_commands, get_xia_xdsxscale_commands
from fragview.pipeline_commands import get_xdsapp_command, get_autoproc_command
from jobs.client import JobsSet


def datasets(request):
    proj = current_project(request)

    form = ProcessForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(f"invalid processing arguments {form.errors}")

    filters = form.datasets_filter

    options = {
        "spacegroup": form.space_group,
        "cellparam": form.cell_params,
        "friedel_law": form.friedel_law,
        "customxds": form.custom_xds,
        "customautoproc": form.custom_autoproc,
        "customdials": form.custom_dials,
        "customxdsapp": form.custom_xdsapp,
    }

    if form.use_xdsapp:
        t = threading.Thread(target=run_xdsapp, args=(proj, filters, options))
        t.daemon = True
        t.start()

    if form.use_dials:
        t = threading.Thread(target=run_dials, args=(proj, filters, options))
        t.daemon = True
        t.start()

    if form.use_autoproc:
        t = threading.Thread(target=run_autoproc, args=(proj, filters, options))
        t.daemon = True
        t.start()

    if form.use_xdsxscale:
        t = threading.Thread(target=run_xds, args=(proj, filters, options))
        t.daemon = True
        t.start()

    return render(request, "fragview/jobs_submitted.html")


def _get_dataset_params(proj, dset):
    xsdata = XSDataCollection(dataset_xml_file(proj, dset))

    outdir = path.join(project_process_protein_dir(proj),
                       xsdata.imagePrefix,
                       f"{xsdata.imagePrefix}_{xsdata.dataCollectionNumber}")

    master_image = path.join(xsdata.imageDirectory, dataset_master_image(dset))

    sample = outdir.split("/")[-1]

    return outdir, master_image, sample, xsdata.numberOfImages


def run_xdsapp(proj, filters, options):
    # XDSAPP cmd options
    # -h, --help
    # show this help message and exit
    # --cmd
    # start the command line version of XDSAPP
    # --suffix=SUFFIX
    # give the suffix of your images, e.g. --suffix ".cbf" (just for multi mode)
    # -i IMAGE, --image=IMAGE
    # single mode: give one image of a dataset, this dataset will be processed, e.g. -i abcd_01_010.img
    # --xdsinp
    # genereate XDS.INP for this dataset, only in single mode
    # --index
    # index dataset, only in single mode
    # --range=RANGE
    # give datarange in format --range "start end"
    # --spotrange=SPOT_RANGE
    # give spotrange manually, can be 1-3 pairs, e.g. --spotrange "1 10 20 40 60 80"
    # --org=ORGXY
    # give orgx, orgy manually: --org "orgx orgy"
    # -f FRIEDEL, --fried=FRIEDEL
    # set friedel law, give "true" or "false", default: false
    # -s SG, --spacegroup=SG
    # give spacegroup and unit cell constants in format -s "sg a b c α β γ"
    # --dir=RESULT_DIR
    # give resultdir, e.g. --dir myresults, default: xdsit/surname
    # -r REINT, --reint=REINT
    # no of reintegration cycles, default: 2
    # --live=LIVE_NO
    # live processing, give last image no., e.g. --live 200
    # --ccstar=CCSTAR
    # do resolution cutoff based on ccstar
    # -a, --all
    # multi-mode: process all datasets in a dir (recursively)
    # --cont=ALLAROUND
    # multi-mode: look continuously for datasets and process them
    # -j JOBS_NO, --jobs=JOBS_NO
    # set number of parallel jobs for xds, default: 1
    # -c CPU_NO, --cpu=CPU_NO
    # set number of cpus for xds, default: all cpus of the machine
    # --nice=NICE_LEVEL
    # set nice level of xds, default: 19
    # --res=RESOLUTION
    # use data up to resolution
    # --delphi=DELPHI
    # give delphi manually
    # --norestest
    # do resolution test

    # Modules list for HPC env
    softwares = ["gopresto", versions.XDSAPP_MOD]

    jobs = JobsSet("XDSAPP")
    hpc = SITE.get_hpc_runner()
    epoch = str(round(time.time()))

    for num, dset in enumerate(get_proc_datasets(proj, filters)):
        batch = hpc.new_batch_file("XDSAPP",
                                   project_script(proj, f"xdsapp_fragmax_part{num}.sh"),
                                   project_log_path(proj, f"multi_xdsapp_{epoch}_%j_out.txt"),
                                   project_log_path(proj, f"multi_xdsapp_{epoch}_%j_err.txt"))

        batch.set_options(time=Duration(hours=168), exclusive=True, nodes=1, cpus_per_task=64,
                          partition="fujitsu", memory=DataSize(gigabyte=300))

        batch.purge_modules()
        batch.load_modules(softwares)

        outdir, image_file, sample, num_images = _get_dataset_params(proj, dset)

        os.makedirs(outdir, mode=0o760, exist_ok=True)
        os.makedirs(outdir + "/xdsapp", mode=0o760, exist_ok=True)

        if options["spacegroup"] != "":
            cellpar = " ".join(options["cellparam"].split(","))
            spacegroup = options["spacegroup"]
            spg = f"--spacegroup='{spacegroup} {cellpar}'"
        else:
            spg = ""

        customxdsapp = options["customxdsapp"]
        if options["friedel_law"] == "true":
            friedel = "--fried=True"
        else:
            friedel = "--fried=False"

        batch.add_commands(
            f"mkdir -p {outdir}/xdsapp",
            f"cd {outdir}/xdsapp",
            get_xdsapp_command(outdir, spg, customxdsapp, friedel, image_file, num_images))

        add_update_status_script_cmds(proj, sample, batch, softwares)

        batch.save()
        jobs.add_job(batch)

    jobs.submit()


def run_autoproc(proj, filters, options):
    # Modules list for HPC env
    softwares = ["gopresto", versions.CCP4_MOD, versions.AUTOPROC_MOD, versions.DURIN_MOD]

    jobs = JobsSet("autoPROC")
    hpc = SITE.get_hpc_runner()
    epoch = str(round(time.time()))

    for num, dset in enumerate(get_proc_datasets(proj, filters)):
        batch = hpc.new_batch_file("autoPROC",
                                   project_script(proj, f"autoproc_fragmax_part{num}.sh"),
                                   project_log_path(proj, f"multi_autoproc_{epoch}_%j_out.txt"),
                                   project_log_path(proj, f"multi_autoproc_{epoch}_%j_err.txt"))

        batch.set_options(time=Duration(hours=168), exclusive=True, nodes=1, cpus_per_task=64,
                          partition="fujitsu", memory=DataSize(gigabyte=300))

        batch.purge_modules()
        batch.load_modules(softwares)

        outdir, h5master, sample, num_images = _get_dataset_params(proj, dset)

        os.makedirs(outdir, mode=0o760, exist_ok=True)

        if options["spacegroup"] != "":
            spacegroup = options["spacegroup"]
            spg = f"symm='{spacegroup}'"
        else:
            spg = ""
        if options["cellparam"] != "":
            cellpar = " ".join(options["cellparam"].split(","))
            cellpar = cellpar.replace("(", "").replace(")", "")
            unit_cell = f"cell='{cellpar}'"
        else:
            unit_cell = ""

        customautoproc = options["customautoproc"]
        if options["friedel_law"] == "true":
            friedel = "-ANO"
        else:
            friedel = "-noANO"

        batch.add_commands(
            f"rm -rf {outdir}/autoproc",
            f"mkdir -p {outdir}",
            f"cd {outdir}",
            get_autoproc_command(outdir, spg, unit_cell, customautoproc, friedel, h5master, num_images)
        )

        add_update_status_script_cmds(proj, sample, batch, softwares)

        batch.save()
        jobs.add_job(batch)

    jobs.submit()


def run_xds(proj, filters, options):
    # atom=X
    # Tell xia2 to separate anomalous pairs i.e. I(+) ≠ I(−) in scaling.
    # pipeline=3d
    # Tell xia2 to use XDS and XSCALE.
    # pipeline=3dii
    # Tell xia2 to use XDS and XSCALE, indexing with peaks found from all images.
    # pipeline=dials
    # Tell xia2 to use DIALS.
    # pipeline=dials-aimless
    # Tell xia2 to use DIALS but scale with Aimless.
    # xinfo=some.xinfo
    # Use specific modified .xinfo input file.
    # image=/path/to/an/image.img
    # Process a specific scan.
    # Pass multiple image= parameters to include multiple scans.
    # image=/path/to/an/image.img:start:end
    # Process a specific image range within a scan. start and end are numbers denoting the image range, e.g.
    # image=/path/to/an/image.img:1:100 processes images 1–100 inclusive.
    # As above, one can pass multiple image= parameters.
    # small_molecule=true
    # Process in manner more suited to small molecule data.
    # space_group=sg
    # Set the spacegroup, e.g. P21.
    # unit_cell=a,b,c,α,β,γ
    # Set the cell constants.

    # Modules list for HPC env
    softwares = ["gopresto", versions.DIALS_MOD, versions.XDS_MOD]

    jobs = JobsSet("XIA2/XDS")
    hpc = SITE.get_hpc_runner()
    epoch = str(round(time.time()))

    for num, dset in enumerate(get_proc_datasets(proj, filters)):
        batch = hpc.new_batch_file("XIA2/XDS",
                                   project_script(proj, f"xds_fragmax_part{num}.sh"),
                                   project_log_path(proj, f"multi_xia2XDS_{epoch}_%j_out.txt"),
                                   project_log_path(proj, f"multi_xia2XDS_{epoch}_%j_err.txt"))

        batch.set_options(time=Duration(hours=168), exclusive=True, nodes=1,
                          cpus_per_task=64, partition="fujitsu", memory=DataSize(gigabyte=300))

        batch.purge_modules()
        batch.load_modules(softwares)

        outdir, image_file, sample, num_images = _get_dataset_params(proj, dset)

        os.makedirs(outdir, mode=0o760, exist_ok=True)
        os.makedirs(outdir + "/xdsxscale", mode=0o760, exist_ok=True)

        if options["spacegroup"] != "":
            spacegroup = options["spacegroup"]
            spg = f"space_group={spacegroup}"
        else:
            spg = ""
        if options["cellparam"] != "":
            cellpar = ",".join(options["cellparam"].split(","))
            unit_cell = f"unit_cell={cellpar}"
        else:
            unit_cell = ""
        customxds = options["customxds"]

        if options["friedel_law"] == "true":
            friedel = "atom=X"
        else:
            friedel = ""

        batch.add_commands(
            f"mkdir -p {outdir}/xdsxscale",
            f"cd {outdir}/xdsxscale",
            *get_xia_xdsxscale_commands(spg, unit_cell, customxds, friedel, image_file, num_images))

        add_update_status_script_cmds(proj, sample, batch, softwares)

        batch.save()
        jobs.add_job(batch)

    jobs.submit()


def run_dials(proj, filters, options):
    # atom=X
    # Tell xia2 to separate anomalous pairs i.e. I(+) ≠ I(−) in scaling.
    # pipeline=3d
    # Tell xia2 to use XDS and XSCALE.
    # pipeline=3dii
    # Tell xia2 to use XDS and XSCALE, indexing with peaks found from all images.
    # pipeline=dials
    # Tell xia2 to use DIALS.
    # pipeline=dials-aimless
    # Tell xia2 to use DIALS but scale with Aimless.
    # xinfo=some.xinfo
    # Use specific modified .xinfo input file.
    # image=/path/to/an/image.img
    # Process a specific scan.
    # Pass multiple image= parameters to include multiple scans.
    # image=/path/to/an/image.img:start:end
    # Process a specific image range within a scan. start and end are numbers denoting the image range, e.g.
    # image=/path/to/an/image.img:1:100 processes images 1–100 inclusive.
    # As above, one can pass multiple image= parameters.
    # small_molecule=true
    # Process in manner more suited to small molecule data.
    # space_group=sg
    # Set the spacegroup, e.g. P21.
    # unit_cell=a,b,c,α,β,γ
    # Set the cell constants.

    # Modules list for HPC env
    softwares = ["gopresto", versions.DIALS_MOD]

    jobs = JobsSet("XIA2/DIALS")
    hpc = SITE.get_hpc_runner()
    epoch = str(round(time.time()))

    for num, dset in enumerate(get_proc_datasets(proj, filters)):
        batch = hpc.new_batch_file(
            "DIALS",
            project_script(proj, f"dials_fragmax_part{num}.sh"),
            project_log_path(proj, f"multi_xia2DIALS_{epoch}_%j_out.txt"),
            project_log_path(proj, f"multi_xia2DIALS_{epoch}_%j_err.txt"))

        batch.set_options(time=Duration(hours=168), exclusive=True, nodes=1,
                          cpus_per_task=64, partition="fujitsu", memory=DataSize(gigabyte=300))

        batch.purge_modules()
        batch.load_modules(softwares)

        outdir, image_file, sample, num_images = _get_dataset_params(proj, dset)

        os.makedirs(outdir, mode=0o760, exist_ok=True)
        os.makedirs(outdir + "/dials", mode=0o760, exist_ok=True)

        if options["spacegroup"] != "":
            spacegroup = options["spacegroup"]
            spg = f"space_group={spacegroup}"
        else:
            spg = ""
        if options["cellparam"] != "":
            cellpar = ",".join(options["cellparam"].split(","))
            cellpar = cellpar.replace("(", "").replace(")", "")
            unit_cell = f"unit_cell={cellpar}"
        else:
            unit_cell = ""
        customdials = options["customdials"]

        if options["friedel_law"] == "true":
            friedel = "atom=X"
        else:
            friedel = ""

        batch.add_commands(
            f"mkdir -p {outdir}/dials",
            f"cd {outdir}/dials",
            *get_xia_dials_commands(spg, unit_cell, customdials, friedel, image_file, num_images))

        add_update_status_script_cmds(proj, sample, batch, softwares)

        batch.save()
        jobs.add_job(batch)

    jobs.submit()
