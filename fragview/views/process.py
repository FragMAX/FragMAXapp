import time
from django.shortcuts import render
from django.http import HttpResponseBadRequest
from fragview.projects import current_project, project_script
from fragview.projects import project_log_path
from fragview import versions
from fragview.filters import get_proc_datasets
from fragview.forms import OldProcessForm
from fragview.tools import Tools, get_space_group_argument
from fragview.views.utils import start_thread
from fragview.views.update_jobs import add_update_job
from fragview.sites import SITE
from fragview.sites.plugin import Duration, DataSize
from fragview.pipeline_commands import (
    get_xia_dials_commands,
    get_xia_xds_commands,
)
from fragview.pipeline_commands import get_xdsapp_command, get_autoproc_command
from jobs.client import JobsSet
from projects.database import db_session


def datasets(request):
    proj = current_project(request)

    form = OldProcessForm(request.POST)
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

    if form.use_dials:
        start_thread(run_dials, proj, filters, options)

    if form.use_xds:
        start_thread(run_xds, proj, filters, options)

    if form.use_xdsapp:
        start_thread(run_xdsapp, proj, filters, options)

    if form.use_autoproc:
        start_thread(run_autoproc, proj, filters, options)

    return render(request, "jobs_submitted.html")


def _get_dataset_params(project, dataset):
    return (
        project.get_dataset_process_dir(dataset),
        project.get_dataset_master_image(dataset),
    )


@db_session
def run_xdsapp(project, filters, options):
    # Modules list for HPC env
    softwares = ["gopresto", versions.XDSAPP_MOD]

    jobs = JobsSet("XDSAPP")
    hpc = SITE.get_hpc_runner()
    epoch = str(round(time.time()))

    for num, dset in enumerate(get_proc_datasets(project, filters, "xdsapp")):
        outdir, image_file = _get_dataset_params(project, dset)

        if options["spacegroup"] is not None:
            cellpar = " ".join(options["cellparam"].split(","))
            spacegroup = get_space_group_argument(Tools.XDSAPP, options["spacegroup"])
            spg = f"--spacegroup='{spacegroup} {cellpar}'"
        else:
            spg = ""

        customxdsapp = options["customxdsapp"]
        if options["friedel_law"] == "true":
            friedel = "--fried=True"
        else:
            friedel = "--fried=False"

        xdsapp_command, cpus = get_xdsapp_command(
            outdir, spg, customxdsapp, friedel, image_file, dset.images
        )

        batch = hpc.new_batch_file(
            "XDSAPP",
            project_script(project, f"xdsapp_fragmax_part{num}.sh"),
            project_log_path(project, f"multi_xdsapp_{epoch}_%j_out.txt"),
            project_log_path(project, f"multi_xdsapp_{epoch}_%j_err.txt"),
            cpus,
        )

        batch.set_options(
            time=Duration(hours=168),
            exclusive=True,
            nodes=1,
        )

        batch.purge_modules()
        batch.load_modules(softwares)

        batch.add_commands(
            f"mkdir -p {outdir}/xdsapp",
            f"cd {outdir}/xdsapp",
            xdsapp_command,
        )

        batch.save()
        jobs.add_job(batch)

        add_update_job(jobs, hpc, project, "xdsapp", dset, batch)

    jobs.submit()


@db_session
def run_autoproc(proj, filters, options):
    # Modules list for HPC env
    softwares = [
        "gopresto",
        versions.CCP4_MOD,
        versions.AUTOPROC_MOD,
        versions.DURIN_MOD,
    ]

    jobs = JobsSet("autoPROC")
    hpc = SITE.get_hpc_runner()
    epoch = str(round(time.time()))

    for num, dset in enumerate(get_proc_datasets(proj, filters, "autoproc")):
        batch = hpc.new_batch_file(
            "autoPROC",
            project_script(proj, f"autoproc_fragmax_part{num}.sh"),
            project_log_path(proj, f"multi_autoproc_{epoch}_%j_out.txt"),
            project_log_path(proj, f"multi_autoproc_{epoch}_%j_err.txt"),
        )

        batch.set_options(
            time=Duration(hours=168),
            exclusive=True,
            nodes=1,
            cpus_per_task=64,
            memory=DataSize(gigabyte=300),
        )

        batch.purge_modules()
        batch.load_modules(softwares)

        outdir, h5master, sample, num_images = _get_dataset_params(proj, dset)

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
            get_autoproc_command(
                outdir, spg, unit_cell, customautoproc, friedel, h5master, num_images
            ),
        )

        batch.save()
        jobs.add_job(batch)

        add_update_job(jobs, hpc, proj, "autoproc", dset, batch)

    jobs.submit()


@db_session
def run_xds(proj, filters, options):
    # Modules list for HPC env
    softwares = ["gopresto", versions.DIALS_MOD, versions.XDS_MOD]

    jobs = JobsSet("XIA2/XDS")
    hpc = SITE.get_hpc_runner()
    epoch = str(round(time.time()))

    for num, dset in enumerate(get_proc_datasets(proj, filters, "xds")):
        outdir, image_file = _get_dataset_params(proj, dset)

        spg = get_space_group_argument(Tools.XDS, options["spacegroup"])

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

        xds_commands, cpus = get_xia_xds_commands(
            spg, unit_cell, customxds, friedel, image_file, dset.images
        )

        batch = hpc.new_batch_file(
            "XIA2/XDS",
            project_script(proj, f"xds_fragmax_part{num}.sh"),
            project_log_path(proj, f"multi_xia2XDS_{epoch}_%j_out.txt"),
            project_log_path(proj, f"multi_xia2XDS_{epoch}_%j_err.txt"),
            cpus,
        )

        batch.set_options(
            time=Duration(hours=168),
            exclusive=True,
            nodes=1,
        )

        batch.purge_modules()
        batch.load_modules(softwares)

        batch.add_commands(f"mkdir -p {outdir}/xds", f"cd {outdir}/xds", *xds_commands)

        batch.save()
        jobs.add_job(batch)

        add_update_job(jobs, hpc, proj, "xds", dset, batch)

    jobs.submit()


@db_session
def run_dials(proj, filters, options):
    # Modules list for HPC env
    softwares = ["gopresto", versions.DIALS_MOD]

    jobs = JobsSet("XIA2/DIALS")
    hpc = SITE.get_hpc_runner()
    epoch = str(round(time.time()))

    for num, dset in enumerate(get_proc_datasets(proj, filters, "dials")):
        outdir, image_file = _get_dataset_params(proj, dset)

        spg = get_space_group_argument(Tools.DIALS, options["spacegroup"])

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

        dials_commands, cpus = get_xia_dials_commands(
            spg, unit_cell, customdials, friedel, image_file, dset.images
        )

        batch = hpc.new_batch_file(
            "DIALS",
            project_script(proj, f"dials_fragmax_part{num}.sh"),
            project_log_path(proj, f"multi_xia2DIALS_{epoch}_%j_out.txt"),
            project_log_path(proj, f"multi_xia2DIALS_{epoch}_%j_err.txt"),
            cpus,
        )

        batch.set_options(
            time=Duration(hours=168),
            exclusive=True,
            nodes=1,
        )

        batch.purge_modules()
        batch.load_modules(softwares)

        batch.add_commands(
            f"mkdir -p {outdir}/dials",
            f"cd {outdir}/dials",
            *dials_commands,
        )

        batch.add_commands(
            "echo 'remove .refl files, to conserve disk space'",
            f"rm -rfv {outdir}/dials/DataFiles/*.refl",
            f"rm -rfv {outdir}/dials/DEFAULT/scale/*.refl",
            f"rm -rfv {outdir}/dials/DEFAULT/SAD/*/*/*.refl",
        )

        batch.save()
        jobs.add_job(batch)

        add_update_job(jobs, hpc, proj, "dials", dset, batch)

    jobs.submit()
