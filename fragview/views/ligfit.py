import subprocess
import threading
import os
from django.shortcuts import render
from fragview.projects import current_project, project_script, project_process_protein_dir

from glob import glob



update_script="/data/staff/biomax/webapp/static/scripts/update_status.py"

def datasets(request):
    proj = current_project(request)

    userInput = str(request.GET.get("submitligProc"))
    empty, rhofitSW, ligfitSW, ligandfile, fitprocess, scanchirals, customligfit, ligfromname, filters = \
        userInput.split(";;")

    useRhoFit = "False"
    useLigFit = "False"

    if "true" in rhofitSW:
        useRhoFit = "True"
    if "true" in ligfitSW:
        useLigFit = "True"

    t1 = threading.Thread(target=auto_ligand_fit, args=(proj, useLigFit, useRhoFit, filters))
    t1.daemon = True
    t1.start()

    return render(
        request,
        "fragview/jobs_submitted.html",
        {"command": "<br>".join(userInput.split(";;"))})


def auto_ligand_fit(proj, useLigFit, useRhoFit, filters):
    
    if "filters:" in filters:
        filters = filters.split(":")[-1]
    if filters == "ALL":
        filters = ""

    fitmethod=""
    if useLigFit=="True":
        fitmethod+="ligfit"
    if useRhoFit=="True":
        fitmethod+="rhofit"


    pdbList=glob(f"{proj.data_path()}/fragmax/results/{proj.protein}*/*/*/final.pdb")
    pdbList=[x for x in pdbList if "Apo" not in x and filters in x]
    header=""
    header+="#!/bin/bash\n"
    header+="#!/bin/bash\n"
    header+="#SBATCH -t 01:00:00\n"
    header+="#SBATCH -J autoLigfit\n"
    header+="#SBATCH --cpus-per-task=1\n"
    header+=f"#SBATCH -o /data/visitors/biomax/{proj.proposal}/{proj.shift}/fragmax/logs/auto_ligfit_%j_out.txt\n"
    header+=f"#SBATCH -e /data/visitors/biomax/{proj.proposal}/{proj.shift}/fragmax/logs/auto_ligfit_%j_err.txt\n"
    header+="module purge\n"
    header+="module load autoPROC BUSTER Phenix CCP4\n"    
    
    for pdb in pdbList:
        rhofit_cmd = ""
        ligfit_cmd = ""    
        fragID         = pdb.split("/")[8].split("-")[-1].split("_")[0]
        ligCIF         = proj.data_path()+"/fragmax/process/fragment/"+proj.library+"/"+fragID+"/"+fragID+".cif"
        ligPDB         = proj.data_path()+"/fragmax/process/fragment/"+proj.library+"/"+fragID+"/"+fragID+".pdb"
        rhofit_outdir  = pdb.replace("final.pdb","rhofit/")
        ligfit_outdir  = pdb.replace("final.pdb","ligfit/")
        mtz_input      = pdb.replace(".pdb",".mtz") 
        sample         = pdb.split("/")[8]
        if "rhofit" in fitmethod:
            if os.path.exists(rhofit_outdir):
                rhofit_cmd += f"rm -rf {rhofit_outdir}\n"
            rhofit_cmd     += f"rhofit -l {ligCIF} -m {mtz_input} -p {pdb} -d {rhofit_outdir}\n"
        if "ligfit" in fitmethod:
            if os.path.exists(ligfit_outdir):
                ligfit_cmd += f"rm -rf {ligfit_outdir}\n"
            ligfit_cmd     += f"mkdir -p {ligfit_outdir}\n"
            ligfit_cmd     += f"cd {ligfit_outdir} \n"
            ligfit_cmd     += f"phenix.ligandfit data={mtz_input} model={pdb} ligand={ligPDB} fill=True clean_up=True \n"
            
        with open(project_script(proj, "autoligand_"+sample+".sh"), "w") as writeFile:
            writeFile.write(header)
            writeFile.write(rhofit_cmd)
            writeFile.write(ligfit_cmd)
            writeFile.write(f"python {update_script} {sample} {proj.proposal}/{proj.shift}")
            writeFile.write("\n\n")
        script=project_script(proj, "autoligand_"+sample+".sh")    
        command = 'echo "module purge | module load CCP4 Phenix | sbatch ' + script + ' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command, shell=True)
        #os.remove(script)
