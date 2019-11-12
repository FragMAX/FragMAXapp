import os
import pypdb
import pyfastcopy  # noqa
import shutil
import subprocess
from glob import glob
from django.shortcuts import render
from fragview.projects import current_project, project_script, project_process_protein_dir
from .utils import scrsplit


def datasets(request):
    proj = current_project(request)

    userInput = str(request.GET.get("submitrfProc"))
    empty, dimpleSW, fspSW, busterSW, refinemode, mrthreshold, refinerescutoff, userPDB, refspacegroup, filters, \
        customrefdimple, customrefbuster, customreffspipe, aimlessopt = userInput.split(";;")

    if "false" in dimpleSW:
        useDIMPLE = False
    else:
        useDIMPLE = True
    if "false" in fspSW:
        useFSP = False
    else:
        useFSP = True
    if "false" in busterSW:
        useBUSTER = False
    else:
        useBUSTER = True
    # if len(userPDB)<20:
    pdbmodel = userPDB.replace("pdbmodel:", "")
    os.makedirs(proj.data_path() + "/fragmax/models/", mode=0o777, exist_ok=True)
    if pdbmodel != "":
        if pdbmodel in [x.split("/")[-1].split(".pdb")[0] for x in glob(proj.data_path() + "/fragmax/models/*.pdb")]:
            if ".pdb" not in pdbmodel:
                pdbmodel = proj.data_path() + "/fragmax/models/" + pdbmodel + ".pdb"
            else:
                pdbmodel = proj.data_path() + "/fragmax/models/" + pdbmodel
        elif "/data/visitors/biomax/" in pdbmodel:

            if not os.path.exists(proj.data_path() + "/fragmax/models/" + pdbmodel.split("/")[-1]):
                shutil.copyfile(pdbmodel, proj.data_path() + "/fragmax/models/" + pdbmodel.split("/")[-1])
                pdbmodel = proj.data_path() + "/fragmax/models/" + pdbmodel.split("/")[-1]
        else:
            if ".pdb" in pdbmodel:
                pdbmodel = pdbmodel.split(".pdb")[0]
            with open(proj.data_path() + "/fragmax/models/" + pdbmodel + ".pdb", "w") as pdb:
                pdb.write(pypdb.get_pdb_file(pdbmodel, filetype='pdb'))
            pdbmodel = proj.data_path() + "/fragmax/models/" + pdbmodel + ".pdb"
    pdbmodel.replace(".pdb.pdb", ".pdb")
    spacegroup = refspacegroup.replace("refspacegroup:", "")

    run_structure_solving(proj, useDIMPLE, useFSP, useBUSTER, pdbmodel, spacegroup, filters, customrefdimple,
                          customrefbuster, customreffspipe, aimlessopt)
    outinfo = "<br>".join(userInput.split(";;"))

    return render(
        request,
        "fragview/jobs_submitted.html",
        {"command": outinfo})


def run_structure_solving(proj, useDIMPLE, useFSP, useBUSTER, userPDB, spacegroup, filters, customrefdimple,
                          customrefbuster, customreffspipe, aimlessopt):

    customreffspipe = customreffspipe.split("customrefinefspipe:")[-1]
    customrefbuster = customrefbuster.split("customrefinebuster:")[-1]
    customrefdimple = customrefdimple.split("customrefinedimple:")[-1]
    aimlessopt = aimlessopt.split("aimlessopt:")[-1]
    argsfit = "none"
    if "filters:" in filters:
        filters = filters.split(":")[-1]
    if filters == "ALL":
        filters = ""

    process2results(proj, spacegroup, aimlessopt)

    with open(project_script(proj, "run_queueREF.py"), "w") as writeFile:
        writeFile.write('''import commands, os, sys, glob, time, subprocess
argsfit=sys.argv[1]
path=sys.argv[2]
acr=sys.argv[3]
PDBfile=sys.argv[4]
cmd = "sbatch "+path+"/fragmax/scripts/run_proc2res.sh"
status, jobnum1 = commands.getstatusoutput(cmd)
jobnum1=jobnum1.split("batch job ")[-1]
inputData=list()
for proc in glob.glob(path+"/fragmax/results/"+acr+"*/*/"):
    mtzList=glob.glob(proc+"*mtz")
    if mtzList and "''' + filters + '''" in proc:
        inputData.append(sorted(glob.glob(proc+"*mtz"))[0])
def scrsplit(a, n):
    k, m = divmod(len(a), n)
    return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))
if "dimple" in argsfit:
    cmd = "sbatch --dependency=afterany:%s %s/fragmax/scripts/run_dimple.sh" % (jobnum1,path)
    status,jobnum2 = commands.getstatusoutput(cmd)
if "fspipeline" in argsfit:
    cmd = "sbatch --dependency=afterany:%s %s/fragmax/scripts/fspipeline_master.sh" % (jobnum1,path)
    status,jobnum3 = commands.getstatusoutput(cmd)
if "buster" in argsfit:
    cmd = "sbatch --dependency=afterany:%s %s/fragmax/scripts/buster_master.sh" % (jobnum1,path)
    status,jobnum4 = commands.getstatusoutput(cmd)''')

    def fspipeline_hpc(PDB):
        inputData = list()
        m = 0

        fsp = '''python /data/staff/biomax/guslim/FragMAX_dev/fm_bessy/fspipeline.py --sa=false --refine=''' + PDB + \
              ''' --exclude="dimple fspipeline buster unmerged rhofit ligfit truncate" --cpu=2 ''' + customreffspipe
        for proc in glob(proj.data_path() + "/fragmax/results/" + proj.protein + "*/*/"):
            mtzList = glob(proc + "*mtz")
            if mtzList and filters in proc:
                inputData.append(sorted(glob(proc + "*mtz"))[0])
        scriptList = ["cd " + "/".join(x.split("/")[:-1]) + "/ \n" + fsp for x in inputData]
        nodes = round(len(inputData) / 48 + 0.499)

        for n, i in enumerate(list(scrsplit(scriptList, nodes))):
            header = '''#!/bin/bash\n'''
            header += '''#!/bin/bash\n'''
            header += '''#SBATCH -t 04:00:00\n'''
            header += '''#SBATCH -J FSpipeline\n'''
            # header+='''#SBATCH --nodelist=cn'''+str(node0+n)+'''\n'''
            header += '''#SBATCH --nice=25\n'''
            header += '''#SBATCH --cpus-per-task=2\n'''
            header += '''#SBATCH --mem=5000\n'''
            header += '''#SBATCH -o ''' + proj.data_path() + '''/fragmax/logs/fsp_fragmax_%j_out.txt\n'''
            header += '''#SBATCH -e ''' + proj.data_path() + '''/fragmax/logs/fsp_fragmax_%j_err.txt\n\n'''
            header += '''module purge\n'''
            header += '''module load CCP4 Phenix\n'''
            header += '''echo export TMPDIR=''' + proj.data_path() + '''/fragmax/logs/\n\n'''
            for j in i:
                with open(proj.data_path() + "/fragmax/scripts/fspipeline_worker_" + str(m) + ".sh", "w") as writeFile:
                    writeFile.write(header + j)
                m += 1

        with open(proj.data_path() + "/fragmax/scripts/fspipeline_master.sh", "w") as writeFile:
            writeFile.write("""#!/bin/bash\n"""
                            """#!/bin/bash\n"""
                            """#SBATCH -t 01:00:00\n"""
                            """#SBATCH -J FSPmaster\n\n"""
                            """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/fspipeline_master_%j_out.txt\n"""
                            """for file in """ + proj.data_path() + "/fragmax/scripts" +
                            """/fspipeline_worker*.sh; do   sbatch $file;   sleep 0.1; rm $file; done\n"""
                            """""")

    def buster_hpc(PDB):
        inputData = list()
        scriptList = list()
        m = 0
        for proc in glob(proj.data_path() + "/fragmax/results/" + proj.protein + "*/*/"):
            mtzList = glob(proc + "*mtz")
            if mtzList and filters in proc:
                inputData.append(sorted(glob(proc + "*mtz"))[0])
        nodes = round(len(inputData) / 48 + 0.499)
        node0 = 54 - nodes
        for n, srcmtz in enumerate(inputData):
            cmd = ""
            dstmtz = srcmtz.replace("merged", "truncate")
            if os.path.exists("/".join(srcmtz.split("/")[:-1]) + "/buster"):
                cmd += "rm -rf " + "/".join(srcmtz.split("/")[:-1]) + "/buster\n\n"
            if not os.path.exists(dstmtz):
                cmd += \
                    'echo "truncate yes \labout F=FP SIGF=SIGFP" | truncate hklin ' + srcmtz + ' hklout ' + dstmtz + \
                    " | tee " + '/'.join(dstmtz.split('/')[:-1]) + "/truncate.log\n\n"  # noqa
            cmd += "refine -L -p " + PDB + " -m " + dstmtz + " " + customrefbuster + " -TLS -nthreads 2 -d " + "/".join(
                srcmtz.split("/")[:-1]) + "/buster \n"
            scriptList.append(cmd)

        for n, i in enumerate(list(scrsplit(scriptList, nodes))):
            header = '''#!/bin/bash\n'''
            header += '''#!/bin/bash\n'''
            header += '''#SBATCH -t 04:00:00\n'''
            header += '''#SBATCH -J BUSTER\n'''
            header += '''#SBATCH --cpus-per-task=2\n'''
            header += '''#SBATCH --mem=5000\n'''
            header += '''#SBATCH --nice=25\n'''
            header += '''#SBATCH --nodelist=cn''' + str(node0 + n) + '''\n'''
            header += '''#SBATCH -o ''' + proj.data_path() + '''/fragmax/logs/buster_fragmax_%j_out.txt\n'''
            header += '''#SBATCH -e ''' + proj.data_path() + '''/fragmax/logs/buster_fragmax_%j_err.txt\n\n'''
            header += '''module purge\n'''
            header += '''module load autoPROC BUSTER\n'''
            header += '''echo export TMPDIR=''' + proj.data_path() + '''/fragmax/logs/\n\n'''
            for j in i:
                with open(proj.data_path() + "/fragmax/scripts/buster_worker_" + str(m) + ".sh", "w") as writeFile:
                    writeFile.write(header + j)
                m += 1
        with open(proj.data_path() + "/fragmax/scripts/buster_master.sh", "w") as writeFile:
            writeFile.write("""#!/bin/bash\n"""
                            """#!/bin/bash\n"""
                            """#SBATCH -t 01:00:00\n"""
                            """#SBATCH -J BSTRmaster\n\n"""
                            """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/buster_master_%j_out.txt\n"""
                            """for file in """ + proj.data_path() + "/fragmax/scripts" +
                            """/buster_worker*.sh; do   sbatch $file;   sleep 0.1; rm $file; done\n"""
                            """rm buster_worker*sh""")

    def dimple_hpc(PDB):
        # Creates HPC script to run dimple on all mtz files provided.
        # PDB _file can be provided in the header of the python script and parse to all
        # pipelines (Dimple, pipedream, bessy)

        # This line will make dimple run on unscaled unmerged files. It seems that works
        # better sometimes

        # outDirs = list()
        # inputData = list()
        dimpleOut = ""

        # define env for script for dimple
        dimpleOut += """#!/bin/bash\n"""
        dimpleOut += """#!/bin/bash\n"""
        dimpleOut += """#SBATCH -t 99:55:00\n"""
        dimpleOut += """#SBATCH -J dimple\n"""
        dimpleOut += """#SBATCH --exclusive\n"""
        dimpleOut += """#SBATCH -N1\n"""
        dimpleOut += """#SBATCH --cpus-per-task=48\n"""
        dimpleOut += """#SBATCH --mem=220000\n"""
        dimpleOut += """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/dimple_fragmax_%j_out.txt\n"""
        dimpleOut += """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/dimple_fragmax_%j_err.txt\n"""
        dimpleOut += """module purge\n"""
        dimpleOut += """module load CCP4 Phenix \n\n"""

        dimpleOut += "python " + proj.data_path() + "/fragmax/scripts/run_dimple.py"
        dimpleOut += "\n\n"

        with open(proj.data_path() + "/fragmax/scripts/run_dimple.sh", "w") as outp:
            outp.write(dimpleOut)

        with open(proj.data_path() + "/fragmax/scripts/run_dimple.py", "w") as writeFile:
            writeFile.write('''import multiprocessing
import subprocess
import glob


path="%s"
acr="%s"
PDB="%s"

inputData=list()
for proc in glob.glob(path+"/fragmax/results/"+acr+"*/*/"):
    mtzList=glob.glob(proc+"*mtz")
    if mtzList and "%s" in proc:
        inputData.append(sorted(glob.glob(proc+"*mtz"))[0])

outDirs=["/".join(x.split("/")[:-1])+"/dimple" for x in inputData]
mtzList=inputData

inpdata=list()
for a,b in zip(outDirs,mtzList):
    inpdata.append([a,b])

def fragmax_worker((di, mtz)):
    command="dimple -s "+mtz+" "+PDB+" "+di+" %s ; cd "+di+" ; phenix.mtz2map final.mtz"
    subprocess.call(command, shell=True)

def mp_handler():
    p = multiprocessing.Pool(48)
    p.map(fragmax_worker, inpdata)

if __name__ == "__main__":
    mp_handler()\n''' % (
             proj.data_path(), proj.protein, PDB, filters, customrefdimple))

    if userPDB != "":
        if useFSP:
            fspipeline_hpc(userPDB)
            argsfit += "fspipeline"
        if useDIMPLE:
            dimple_hpc(userPDB)
            argsfit += "dimple"
        if useBUSTER:
            buster_hpc(userPDB)
            argsfit += "buster"
    else:
        userPDB = "-"

    command = \
        'echo "python ' + proj.data_path() + '/fragmax/scripts/run_queueREF.py ' + argsfit + ' ' + \
        proj.data_path() + ' ' + proj.protein + ' ' + userPDB + ' " | ssh -F ~/.ssh/ clu0-fe-1'
    subprocess.call("rm " + proj.data_path() + "/fragmax/scripts/*.setvar.lis", shell=True)
    subprocess.call("rm " + proj.data_path() + "/fragmax/scripts/slurm*_out.txt", shell=True)
    subprocess.call(command, shell=True)


def process2results(proj, spacegroup, aimlessopt):
    glob_pattern = f"{project_process_protein_dir(proj)}/*/*/"
    for dp in ["xdsapp", "autoproc", "xdsxscale", "EDNA", "fastdp", "dials"]:
        [os.makedirs("/".join(x.split("/")[:8] + x.split("/")[10:]).replace("/process/", "/results/") + dp, mode=0o760,
                     exist_ok=True) for x in glob(glob_pattern)]

    py_script = project_script(proj, "process2results.py")
    with open(py_script, "w") as writeFile:
        writeFile.write(
'''import os
nimport glob
import subprocess
import shutil
import sys
path="%s"
nacr="%s"
spg="%s"
aimless="%s"
subprocess.call("rm "+path+"/fragmax/results/"+acr+"*/*/*merged.mtz",shell=True)
datasetList=glob.glob(path+"/fragmax/process/"+acr+"/*/*/")
for dataset in datasetList:
    if glob.glob(dataset+"autoproc/*mtz")!=[]:
        try:
            srcmtz=[x for x in glob.glob(dataset+"autoproc/*mtz") if "staraniso" in x][0]
        except IndexError:
            try:
                srcmtz=[x for x in glob.glob(dataset+"autoproc/*mtz") if "aimless" in x][0]
            except IndexError:
                srcmtz=[x for x in glob.glob(dataset+"autoproc/*mtz")][0]
    dstmtz=path+"/fragmax/results/"+dataset.split("/")[-2]+"/autoproc/"+dataset.split("/")[-2]+"_autoproc_merged.mtz"
    if not os.path.exists(dstmtz) and os.path.exists(srcmtz):
        shutil.copyfile(srcmtz,dstmtz)
        cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "
        if aimless=="true":
            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)
    srcmtz=dataset+"dials/DEFAULT/scale/AUTOMATIC_DEFAULT_scaled.mtz"
    if os.path.exists(srcmtz):
        dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/dials/"+dataset.split("/")[-2]+"_dials_merged.mtz"
        if not os.path.exists(dstmtz) and os.path.exists(srcmtz):
            shutil.copyfile(srcmtz,dstmtz)
            cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "
        if aimless=="true":
            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)
    srcmtz=dataset+"xdsxscale/DEFAULT/scale/AUTOMATIC_DEFAULT_scaled.mtz"
    if os.path.exists(srcmtz):
        dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/xdsxscale/"+dataset.split("/")[-2]+"_xdsxscale_merged.mtz"
        if not os.path.exists(dstmtz) and os.path.exists(srcmtz):
            shutil.copyfile(srcmtz,dstmtz)
            cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "
        if aimless=="true":
            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)
    mtzoutList=glob.glob(dataset+"xdsapp/*F.mtz")
    if mtzoutList!=[]:
        srcmtz=mtzoutList[0]
    if os.path.exists(srcmtz):
        dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/xdsapp/"+dataset.split("/")[-2]+"_xdsapp_merged.mtz"
        if not os.path.exists(dstmtz) and os.path.exists(srcmtz):
            shutil.copyfile(srcmtz,dstmtz)
            cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "
        if aimless=="true":
            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)
    mtzoutList=glob.glob(path+"/process/"+acr+"/"+dataset.split("/")[-3]+"/*"+dataset.split("/")[-2]+"*/EDNA_proc/results/*_noanom_aimless.mtz")
    if mtzoutList!=[]:
        srcmtz=mtzoutList[0]
    dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/EDNA/"+dataset.split("/")[-2]+"_EDNA_merged.mtz"
    if not os.path.exists(dstmtz) and os.path.exists(srcmtz):
        shutil.copyfile(srcmtz,dstmtz)
        cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "
        if aimless=="true":
            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)
    mtzoutList=glob.glob(path+"/process/"+acr+"/"+dataset.split("/")[-3]+"/*"+dataset.split("/")[-2]+"*/fastdp/results/*_noanom_fast_dp.mtz.gz")
    if mtzoutList!=[]:
        srcmtz=mtzoutList[0]
        if os.path.exists(srcmtz):
            dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/fastdp/"+dataset.split("/")[-2]+"_fastdp_merged.mtz"
            if not os.path.exists(dstmtz) and os.path.exists(srcmtz):
                shutil.copyfile(srcmtz,dstmtz)
                try:
                    subprocess.check_call(['gunzip', dstmtz+".gz"])
                except:
                    pass
                a=dataset.split("process/")[0]+"results/"+dataset+"/fastdp/"+dataset+"_fastdp_unmerged.mtz"
                cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "
        if aimless=="true":
            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)''' % (  # noqa
                        proj.data_path(), proj.protein, spacegroup, aimlessopt))

    proc2resOut = ""

    # define env for script for dimple

    proc2resOut += """#!/bin/bash\n"""
    proc2resOut += """#!/bin/bash\n"""
    proc2resOut += """#SBATCH -t 99:55:00\n"""
    proc2resOut += """#SBATCH -J Pro2Res\n"""
    proc2resOut += """#SBATCH --exclusive\n"""
    proc2resOut += """#SBATCH -N1\n"""
    proc2resOut += """#SBATCH --cpus-per-task=48\n"""
    proc2resOut += """#SBATCH --mem=220000\n"""
    proc2resOut += """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/process2results_%j_out.txt\n"""
    proc2resOut += """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/process2results_%j_err.txt\n"""
    proc2resOut += """module purge\n"""
    proc2resOut += """module load CCP4 Phenix\n\n"""
    proc2resOut += "\n\n"
    proc2resOut += "python " + py_script

    with open(project_script(proj, "run_proc2res.sh"), "w") as outp:
        outp.write(proc2resOut)
