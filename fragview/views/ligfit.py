import threading
import os
from django.shortcuts import render
from django.http import HttpResponseBadRequest
from fragview import versions
from fragview.forms import LigfitForm
from fragview.projects import current_project, project_script, project_log_path, parse_dataset_name
from fragview.projects import project_fragment_cif, project_fragment_pdb
from fragview.filters import get_ligfit_datasets, get_ligfit_pdbs
from fragview.sites import SITE
from fragview.sites.plugin import Duration
from fragview.views.utils import add_update_status_script_cmds, add_update_results_script_cmds
from jobs.client import JobsSet


def datasets(request):
    proj = current_project(request)

    form = LigfitForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(f"invalid ligfit arguments {form.errors}")

    worker_args = (proj, form.use_phenix_ligfit, form.use_rho_fit, form.datasets_filter, form.cif_method,
                   form.custom_ligfit, form.custom_rhofit)

    t1 = threading.Thread(target=auto_ligand_fit, args=worker_args)
    t1.daemon = True
    t1.start()

    return render(request, "fragview/jobs_submitted.html")


def get_fragment_smiles(proj, dset):
    """
    figure out fragment ID and fragment SMILES for a dataset
    """
    _, sample = dset.rsplit("-", 1)

    fragID, _ = parse_dataset_name(sample)
    frag = proj.library.get_fragment(fragID)

    if frag is None:
        return fragID, "none"

    return fragID, frag.smiles


def auto_ligand_fit(proj, useLigFit, useRhoFit, filters, cifMethod, custom_ligfit, custom_rhofit):
    # Modules for HPC env
    softwares = ["gopresto", versions.BUSTER_MOD, versions.PHENIX_MOD]

    jobs = JobsSet("Ligand Fit")
    hpc = SITE.get_hpc_runner()

    datasets = get_ligfit_datasets(proj, filters, useLigFit, useRhoFit)
    for num, (sample, pdb) in enumerate(get_ligfit_pdbs(proj, datasets)):
        fragID, smiles = get_fragment_smiles(proj, sample)
        clear_tmp_cmd = ""
        cif_out = pdb.replace("final.pdb", fragID)
        if cifMethod == "elbow":
            cif_cmd = f"phenix.elbow --smiles='{smiles}' --output={cif_out}\n"
        elif cifMethod == "acedrg":
            cif_cmd = f"acedrg -i '{smiles}' -o {cif_out}\n"
            clear_tmp_cmd = f"rm -rf {cif_out}_TMP/\n"
        elif cifMethod == "grade":
            cif_cmd = (
                f"rm {cif_out}.cif {cif_out}.pdb\n"
                f"grade '{smiles}' -ocif {cif_out}.cif -opdb {cif_out}.pdb -nomogul\n"
            )
        else:
            cif_cmd = ""
        rhofit_cmd = ""
        ligfit_cmd = ""

        ligCIF = f"{cif_out}.cif"
        ligPDB = f"{cif_out}.pdb"
        projCIF = project_fragment_cif(proj, fragID)
        projPDB = project_fragment_pdb(proj, fragID)
        move_cif_cmd = f"cp {ligCIF} {projCIF}\ncp {ligPDB} {projPDB}\n"
        rhofit_outdir = pdb.replace("final.pdb", "rhofit/")
        ligfit_outdir = pdb.replace("final.pdb", "ligfit/")
        mtz_input = pdb.replace(".pdb", ".mtz")

        if useRhoFit:
            if os.path.exists(rhofit_outdir):
                rhofit_cmd += f"rm -rf {rhofit_outdir}\n"
            rhofit_cmd += f"rhofit -l {ligCIF} -m {mtz_input} -p {pdb} -d {rhofit_outdir} {custom_rhofit}\n"

        if useLigFit:
            if os.path.exists(ligfit_outdir):
                ligfit_cmd += f"rm -rf {ligfit_outdir}\n"
            ligfit_cmd += f"mkdir -p {ligfit_outdir}\n"
            ligfit_cmd += f"cd {ligfit_outdir} \n"
            ligfit_cmd += f"phenix.ligandfit data={mtz_input} model={pdb} ligand={ligPDB} " \
                          f"fill=True clean_up=True {custom_ligfit}\n"

        batch = hpc.new_batch_file(
            "autoLigfit",
            project_script(proj, f"autoligand_{sample}_{num}.sh"),
            project_log_path(proj, "auto_ligfit_%j_out.txt"),
            project_log_path(proj, "auto_ligfit_%j_err.txt")
        )

        batch.set_options(time=Duration(hours=1), cpus_per_task=1)

        batch.purge_modules()
        batch.load_modules(softwares)

        batch.add_commands(
            cif_cmd,
            move_cif_cmd,
            rhofit_cmd,
            ligfit_cmd,
        )

        add_update_status_script_cmds(proj, sample, batch, softwares)
        add_update_results_script_cmds(proj, sample, batch, softwares)

        batch.add_commands(
            clear_tmp_cmd
        )

        batch.save()
        jobs.add_job(batch)

    jobs.submit()
