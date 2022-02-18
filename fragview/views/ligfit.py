import itertools
from pathlib import Path
from django.shortcuts import render
from django.http import HttpResponseBadRequest
from fragview import versions
from fragview.forms import OldLigfitForm
from fragview.projects import (
    current_project,
    project_script,
    project_log_path,
    Project,
)
from fragview.filters import get_ligfit_datasets
from fragview.sites import SITE
from fragview.sites.plugin import Duration
from fragview.views.utils import start_thread, get_crystals_fragment
from fragview.views.update_jobs import add_update_job
from jobs.client import JobsSet
from projects.database import db_session


# TODO: remove me
def datasets(request):
    proj = current_project(request)

    form = OldLigfitForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(f"invalid ligfit arguments {form.errors}")

    start_thread(
        auto_ligand_fit,
        proj,
        form.use_phenix_ligfit,
        form.use_rho_fit,
        form.datasets_filter,
        form.cif_method,
        form.custom_ligfit,
        form.custom_rhofit,
    )

    return render(request, "jobs_submitted.html")


def _get_refine_results(
    project: Project, filters: str, use_ligandfit: bool, use_rhofit: bool
):
    datasets = []

    if filters == "NEW":
        if use_ligandfit:
            datasets.append(get_ligfit_datasets(project, filters, "ligandfit"))

        if use_rhofit:
            datasets.append(get_ligfit_datasets(project, filters, "rhofit"))
    else:
        datasets.append(get_ligfit_datasets(project, filters, None))

    for dataset in itertools.chain(*datasets):
        for result in project.get_datasets_refine_results(dataset):
            yield result


@db_session
def auto_ligand_fit(
    project, useLigFit, useRhoFit, filters, cifMethod, custom_ligfit, custom_rhofit
):
    # Modules for HPC env
    softwares = ["gopresto", versions.BUSTER_MOD, versions.PHENIX_MOD]

    jobs = JobsSet("Ligand Fit")
    hpc = SITE.get_hpc_runner()

    refine_results = _get_refine_results(project, filters, useLigFit, useRhoFit)

    for num, result in enumerate(refine_results):
        dataset = result.dataset
        if dataset.crystal.is_apo():
            # don't try to fit ligand to an apo crystal
            continue

        fragment = get_crystals_fragment(dataset.crystal)
        result_dir = project.get_refine_result_dir(result)

        pdb = Path(result_dir, "final.pdb")

        clear_tmp_cmd = ""
        cif_out = Path(result_dir, fragment.code)

        if cifMethod == "elbow":
            cif_cmd = f"phenix.elbow --smiles='{fragment.smiles}' --output={cif_out}\n"
        elif cifMethod == "acedrg":
            cif_cmd = f"acedrg -i '{fragment.smiles}' -o {cif_out}\n"
            clear_tmp_cmd = f"rm -rf {cif_out}_TMP/\n"
        elif cifMethod == "grade":
            cif_cmd = (
                f"rm -f {cif_out}.cif {cif_out}.pdb\n"
                f"grade '{fragment.smiles}' -ocif {cif_out}.cif -opdb {cif_out}.pdb -nomogul\n"
            )
        else:
            cif_cmd = ""
        rhofit_cmd = ""
        ligfit_cmd = ""

        ligCIF = f"{cif_out}.cif"
        ligPDB = f"{cif_out}.pdb"

        rhofit_outdir = Path(result_dir, "rhofit")
        ligfit_outdir = Path(result_dir, "ligfit")
        mtz_input = Path(result_dir, "final.mtz")

        if useRhoFit:
            if rhofit_outdir.exists():
                rhofit_cmd += f"rm -rf {rhofit_outdir}\n"
            rhofit_cmd += f"rhofit -l {ligCIF} -m {mtz_input} -p {pdb} -d {rhofit_outdir} {custom_rhofit}\n"

        if useLigFit:
            if ligfit_outdir.exists():
                ligfit_cmd += f"rm -rf {ligfit_outdir}\n"
            ligfit_cmd += f"mkdir -p {ligfit_outdir}\n"
            ligfit_cmd += f"cd {ligfit_outdir} \n"
            ligfit_cmd += (
                f"phenix.ligandfit data={mtz_input} model={pdb} ligand={ligPDB} "
                f"fill=True clean_up=True {custom_ligfit}\n"
            )

        batch = hpc.new_batch_file(
            "autoLigfit",
            project_script(project, f"autoligand_{dataset.name}_{num}.sh"),
            project_log_path(project, "auto_ligfit_%j_out.txt"),
            project_log_path(project, "auto_ligfit_%j_err.txt"),
            cpus=1,
        )

        batch.set_options(time=Duration(hours=1))

        batch.purge_modules()
        batch.load_modules(softwares)

        batch.add_commands(
            cif_cmd,
            rhofit_cmd,
            ligfit_cmd,
        )

        batch.add_commands(clear_tmp_cmd)

        batch.save()
        jobs.add_job(batch)

        # NOTE: all the update commands needs to be chained to run after each other,
        # due to limitations (bugs!) in jobsd handling of 'run_after' dependencies.
        # Currently it does not work to specify that multiple jobs should be run after
        # a job is finished.
        #

        if useRhoFit:
            batch = add_update_job(jobs, hpc, project, "rhofit", dataset, batch)

        if useLigFit:
            add_update_job(jobs, hpc, project, "ligandfit", dataset, batch)

    jobs.submit()
