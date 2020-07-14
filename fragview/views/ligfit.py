import threading
import os
from django.shortcuts import render
from django.http import HttpResponseBadRequest
from fragview import hpc
from fragview.forms import LigfitForm
from fragview.projects import current_project, project_script, project_update_status_script_cmds
from fragview.projects import project_update_results_script_cmds
from fragview.views.utils import write_script

from glob import glob

update_script = "/data/staff/biomax/webapp/static/scripts/update_status.py"


def datasets(request):
    proj = current_project(request)

    form = LigfitForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(f"invalid ligfit arguments {form.errors}")

    worker_args = (
        proj, form.use_phenix_ligfit, form.use_rho_fit, form.datasets_filter, form.cif_method
    )

    t1 = threading.Thread(target=auto_ligand_fit, args=worker_args)
    t1.daemon = True
    t1.start()

    return render(request, "fragview/jobs_submitted.html")


def auto_ligand_fit(proj, useLigFit, useRhoFit, filters, cifMethod):
    # Modules for HPC env
    softwares = "autoPROC BUSTER Phenix CCP4"
    lib = proj.library

    if filters == "ALL":
        filters = ""
    if filters == "NEW":
        refinedDatasets = \
            glob(f"{proj.data_path()}/fragmax/results/{proj.protein}*/*/*/rhofit") + \
            glob(f"{proj.data_path()}/fragmax/results/{proj.protein}*/*/*/ligfit")
        processedDatasets = set(["/".join(x.split("/")[:-3]) for x in refinedDatasets])
        allDatasets = [x.split("/")[-2] for x in
                       sorted(glob(f"{proj.data_path()}/fragmax/process/{proj.protein}/{proj.protein}*/*/"))]
        filters = ",".join(list(set(allDatasets) - set(processedDatasets)))

    pdbList = glob(f"{proj.data_path()}/fragmax/results/{proj.protein}*/*/*/final.pdb")
    pdbList = [x for x in pdbList if "Apo" not in x and filters in x]
    header = ""
    header += "#!/bin/bash\n"
    header += "#!/bin/bash\n"
    header += "#SBATCH -t 01:00:00\n"
    header += "#SBATCH -J autoLigfit\n"
    header += "#SBATCH --cpus-per-task=1\n"
    header += f"#SBATCH -o /data/visitors/biomax/{proj.proposal}/{proj.shift}/fragmax/logs/auto_ligfit_%j_out.txt\n"
    header += f"#SBATCH -e /data/visitors/biomax/{proj.proposal}/{proj.shift}/fragmax/logs/auto_ligfit_%j_err.txt\n"
    header += "module purge\n"
    header += f"module load {softwares}\n"

    for num, pdb in enumerate(pdbList):
        fragID = pdb.split("fragmax")[-1].split("/")[2].split("-")[-1].split("_")[0]
        smiles = lib.get_fragment(fragID).smiles
        clear_tmp_cmd = ""
        move_cif_cmd = ""
        cif_out = pdb.replace("final.pdb", fragID)
        if cifMethod == "elbow":
            cif_cmd = f"phenix.elbow --smiles='{smiles}' --output={cif_out}\n"
        elif cifMethod == "acedrg":
            cif_cmd = f"acedrg -i '{smiles}' -o {cif_out}\n"
            clear_tmp_cmd = f"rm -rf {cif_out}_TMP/\n"
        elif cifMethod == "grade":
            cif_cmd = f"grade '{smiles}' -ocif {cif_out} -opdb {cif_out} -nomogul\n"
        else:
            cif_cmd = ""
        rhofit_cmd = ""
        ligfit_cmd = ""

        ligCIF = f"{cif_out}.cif"
        ligPDB = f"{cif_out}.pdb"

        rhofit_outdir = pdb.replace("final.pdb", "rhofit/")
        ligfit_outdir = pdb.replace("final.pdb", "ligfit/")
        mtz_input = pdb.replace(".pdb", ".mtz")
        sample = pdb.split("/")[8]

        if useRhoFit:
            if os.path.exists(rhofit_outdir):
                rhofit_cmd += f"rm -rf {rhofit_outdir}\n"
            rhofit_cmd += f"rhofit -l {ligCIF} -m {mtz_input} -p {pdb} -d {rhofit_outdir}\n"

        if useLigFit:
            if os.path.exists(ligfit_outdir):
                ligfit_cmd += f"rm -rf {ligfit_outdir}\n"
            ligfit_cmd += f"mkdir -p {ligfit_outdir}\n"
            ligfit_cmd += f"cd {ligfit_outdir} \n"
            ligfit_cmd += f"phenix.ligandfit data={mtz_input} model={pdb} ligand={ligPDB} fill=True clean_up=True \n"

        script = project_script(proj, f"autoligand_{sample}_{num}.sh")
        write_script(script,
                     f"{header}" +
                     f"{cif_cmd}" +
                     f"{move_cif_cmd}" +
                     f"{rhofit_cmd}" +
                     f"{ligfit_cmd}\n" +
                     project_update_status_script_cmds(proj, sample, softwares) +
                     "\n" +
                     project_update_results_script_cmds(proj, sample, softwares) +
                     "\n\n" +
                     f"{clear_tmp_cmd}\n")

        hpc.run_sbatch(script)
        # os.remove(script)
