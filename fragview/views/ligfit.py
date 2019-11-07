import subprocess
import threading
from django.shortcuts import render
from fragview.projects import current_project, project_script


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

    return render(request, "fragview/ligfit_datasets.html", {"allproc": "<br>".join(userInput.split(";;"))})


def auto_ligand_fit(proj, useLigFit, useRhoFit, filters):
    if "filters:" in filters:
        filters = filters.split(":")[-1]
    if filters == "ALL":
        filters = ""

    with open(project_script(proj, "autoligand.py"), "w") as writeFile:
        writeFile.write(f'''import multiprocessing
import time
import subprocess
import sys
import glob
import os
path="{proj.data_path()}"
fraglib="{proj.library}"
acr="{proj.protein}"
shiftList="{proj.shift_list}"
fitmethod=sys.argv[4]
pdbList=list()
shiftList=shiftList.split(",")
for s in shiftList:
    p="/data/visitors/biomax/{proj.proposal}/"+s
    pdbList+=glob.glob(p+"/fragmax/results/"+acr+"*/*/*/final.pdb")
pdbList=[x for x in pdbList if "Apo" not in x and "{filters}" in x]
cifList=list()
mtzList=[x.replace(".pdb",".mtz") for x in pdbList]
outListR=[x.replace("final.pdb","rhofit/") for x in pdbList]
outListP=[x.replace("final.pdb","ligfit/") for x in pdbList]
for i in pdbList:
    fragID=i.split("/")[8].split("-")[-1].split("_")[0]
    cifList.append(path+"/fragmax/process/fragment/"+fraglib+"/"+fragID+"/"+fragID+".cif")
inpdataR=list()
inpdataP=list()
for a,b,c,d in zip(cifList,mtzList,pdbList,outListR):
    inpdataR.append([a,b,c,d])
for a,b,c,d in zip(cifList,mtzList,pdbList,outListP):
    inpdataP.append([a,b,c,d])
def fit_worker((cif, mtz, pdb, out)):
    if fitmethod=="rhofit":
        if os.path.exists(out):
            os.system("rm -rf "+out)
        command="rhofit -l %s -m %s -p %s -d %s" %(cif, mtz, pdb, out)
        subprocess.call(command, shell=True)
    if fitmethod=="ligfit":
        out="/".join(out.split("/")[:-1])
        if not os.path.exists(out):
            os.makedirs(out)
            command="cd %s && phenix.ligandfit data=%s model=%s ligand=%s fill=True clean_up=True" %(out,mtz, pdb, cif)
            subprocess.call(command, shell=True)
def mp_handler():
    p = multiprocessing.Pool(48)
    if fitmethod=="ligfit":
        p.map(fit_worker, inpdataP)
    if fitmethod=="rhofit":
        p.map(fit_worker, inpdataR)
if __name__ == '__main__':
    mp_handler()''')

    print(project_script(proj, "autoligand.py"))

    script = proj.data_path() + "/fragmax/scripts/autoligand.sh"
    if "True" in useRhoFit:
        with open(script, "w") as writeFile:
            writeFile.write('''#!/bin/bash\n'''
                            '''#!/bin/bash\n'''
                            '''#SBATCH -t 99:55:00\n'''
                            '''#SBATCH -J autoRhofit\n'''
                            '''#SBATCH --exclusive\n'''
                            '''#SBATCH -N1\n'''
                            '''#SBATCH --cpus-per-task=48\n'''
                            '''#SBATCH -o ''' + proj.data_path() + '''/fragmax/logs/auto_rhofit_%j_out.txt\n'''
                            '''#SBATCH -e ''' + proj.data_path() + '''/fragmax/logs/auto_rhofit_%j_err.txt\n'''
                            '''module purge\n'''
                            '''module load autoPROC BUSTER Phenix CCP4\n'''
                            '''python ''' + proj.data_path() + '''/fragmax/scripts/autoligand.py ''' +
                            proj.data_path() + ''' ''' + proj.library + ''' ''' + proj.protein + ''' rhofit\n''')
        command = 'echo "module purge | module load BUSTER CCP4 | sbatch ' + script + ' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command, shell=True)

    if "True" in useLigFit:
        with open(script, "w") as writeFile:
            writeFile.write('''#!/bin/bash\n'''
                            '''#!/bin/bash\n'''
                            '''#SBATCH -t 3:00:00\n'''
                            '''#SBATCH -J autoLigfit\n'''
                            '''#SBATCH --exclusive\n'''
                            '''#SBATCH -N1\n'''
                            '''#SBATCH --cpus-per-task=48\n'''
                            '''#SBATCH -o ''' + proj.data_path() + '''/fragmax/logs/auto_ligfit_%j_out.txt\n'''
                            '''#SBATCH -e ''' + proj.data_path() + '''/fragmax/logs/auto_ligfit_%j_err.txt\n'''
                            '''module purge\n'''
                            '''module load autoPROC BUSTER Phenix CCP4\n'''
                            '''python ''' + proj.data_path() + '''/fragmax/scripts/autoligand.py ''' +
                            proj.data_path() + ''' ''' + proj.library + ''' ''' + proj.protein + ''' ligfit\n''')
        command = 'echo "module purge | module load CCP4 Phenix | sbatch ' + script + ' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command, shell=True)
