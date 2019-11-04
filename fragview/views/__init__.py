from django.shortcuts import render
from fragview.projects import current_project, project_shift_dirs, project_static_url
from fragview.projects import project_script, project_process_protein_dir, project_model_path
from fragview.projects import project_raw_master_h5_files, project_ligand_cif, project_definitions, project_xml_files
from difflib import SequenceMatcher

import glob
import os
import random
import natsort
import shutil
import pyfastcopy
import csv
import subprocess
import itertools
import time
import threading
import pypdb
import ast
import sys
import xmltodict
from subprocess import Popen, PIPE
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

################################


def reciprocal_lattice(request):
    proj = current_project(request)
    dataset = str(request.GET.get('dataHeader'))

    flatlist = [
        y for x in
        [
            glob.glob(f"{shift_dir}/fragmax/process/{proj.protein}/*/{dataset}/dials/DEFAULT/NATIVE/*/index/2_SWEEP*")
            for shift_dir in project_shift_dirs(proj)
        ]
        for y in x]


    state="new"
    if flatlist != []:
        rlpdir="/".join(flatlist[0].split("/")[:-1])
        if os.path.exists(rlpdir+"/rlp.json"):
            rlpdir="/".join(flatlist[0].split("/")[:-1])
            rlp=rlpdir+"/rlp.json"
            state="none"
        else:
            cmd='echo "module load DIALS;cd '+rlpdir+'; dials.export 2_SWEEP1_datablock.json 2_SWEEP1_strong.pickle format=json" | ssh -F ~/.ssh/ clu0-fe-1'
            subprocess.call(cmd,shell=True)
            rlp=rlpdir+"/rlp.json"
    else:
        rlp="none2"
    if dataset in rlp:
        timer=0
        while os.path.exists(rlp)==False:
            if timer==20:
                break
            time.sleep(1)
            timer+=1
    rlp=rlp.replace("/data/visitors/","/static/")
    return render(request,'fragview/reciprocal_lattice.html', {'dataset': dataset, "rlp":rlp,"state":state})


################ PIPEDREAM #####################

def pipedream(request):
    proj = current_project(request)

    datasetPathList=glob.glob(proj.data_path() + "/raw/" + proj.protein + "/*/*master.h5")
    datasetPathList=natsort.natsorted(datasetPathList)
    datasetNameList= [i.split("/")[-1].replace("_master.h5","") for i in datasetPathList if "ref-" not in i]
    datasetList=zip(datasetPathList,datasetNameList)
    return render(request, "fragview/pipedream.html",{"data":datasetList})


def pipedream_results(request):
    proj = current_project(request)
    pipedream_csv = os.path.join(project_process_protein_dir(proj), "pipedream.csv")

    resync=str(request.GET.get("resync"))
    if "resyncresults" in resync:
        get_pipedream_results(proj, pipedream_csv)

    if not os.path.exists(pipedream_csv):
        get_pipedream_results(proj, pipedream_csv)
    if os.path.exists(pipedream_csv):
        with open(pipedream_csv,"r") as readFile:
            reader = csv.reader(readFile)
            lines = list(reader)[1:]
        return render(request,'fragview/pipedream_results.html', {'lines': lines})
    else:
        return render(request,'fragview/pipedream_results.html')


def submit_pipedream(request):
    def get_user_pdb_path():
        if len(b_userPDBcode.replace("b_userPDBcode:", "")) == 4:
            userPDB = b_userPDBcode.replace("b_userPDBcode:", "")
            userPDBpath = project_model_path(proj, f"{userPDB}.pdb")

            ## Download and prepare PDB _file - remove waters and HETATM
            with open(userPDBpath, "w") as pdb:
                pdb.write(pypdb.get_pdb_file(userPDB, filetype='pdb'))

            preparePDB = "pdb_selchain -" + pdbchains + " " + userPDBpath + " | pdb_delhetatm | pdb_tidy > " + userPDBpath.replace(
                ".pdb", "_tidy.pdb")
            subprocess.call(preparePDB, shell=True)
        else:
            if len(b_userPDBcode.split("b_userPDBcode:")) == 2:
                if proj.data_path() in b_userPDBcode.split("b_userPDBcode:")[1]:
                    userPDBpath = b_userPDBcode.split("b_userPDBcode:")[1]
                else:
                    userPDBpath = project_model_path(proj, b_userPDBcode.split("b_userPDBcode:")[1])


        return userPDBpath

    proj = current_project(request)
    ppdCMD=str(request.GET.get("ppdform"))
    empty,input_data, ap_spacegroup, ap_cellparam,ap_staraniso,ap_xbeamcent,ap_ybeamcent,ap_datarange,ap_rescutoff,ap_highreslim,ap_maxrpim,ap_mincomplet,ap_cchalfcut,ap_isigicut,ap_custompar,b_userPDBfile,b_userPDBcode,b_userMTZfile,b_refinemode,b_MRthreshold,b_chainsgroup,b_bruteforcetf,b_reslimits,b_angularrf,b_sideaiderefit,b_sideaiderebuild,b_pepflip,b_custompar,rho_ligandsmiles,rho_ligandcode,rho_ligandfromname,rho_copiestosearch,rho_keepH,rho_allclusters,rho_xclusters,rho_postrefine,rho_occuprefine,rho_fittingproc,rho_scanchirals,rho_custompar,extras = ppdCMD.split(";;")

    nodes=10
    #variables init
    ligand="none"
    ppdoutdir="none"
    ppd="INITVALUE"
    userPDB="NoPDB"
    pdbchains="A"
    userPDBpath=""
    #Select one dataset or entire project
    if "alldatasets" not in input_data:
        input_data=input_data.replace("input_data:","")
        ppdoutdir = os.path.join(
            project_process_protein_dir(proj),
            input_data.split(proj.protein + "/")[-1].replace("_master.h5", ""),
            "pipedream")
        os.makedirs("/".join(ppdoutdir.split("/")[:-1]),mode=0o760, exist_ok=True)

        # we need to make sure that pipedream output directory does
        # not exist before invoking pipedream, as pipedream can potentionally
        # refuse to run if the directory already exists
        if os.path.exists(ppdoutdir):
            shutil.rmtree(ppdoutdir)

        userPDBpath = get_user_pdb_path()

        #STARANISO setting
        if "true" in ap_staraniso:
            useANISO=" -useaniso"
        else:
            useANISO=""

        #BUSTER refinement mode
        if "thorough" in b_refinemode:
            refineMode=" -thorough"
        elif "quick" in b_refinemode:
            refineMode=" -quick"
        else:
            refineMode=" "

        #PDB_REDO options
        pdbREDO=""
        if "true" in b_sideaiderefit:
            pdbREDO+=" -remediate"
            refineMode=" -thorough"
        if "true" in b_sideaiderebuild:
            if "remediate" not in pdbREDO:
                pdbREDO+=" -remediate"
            pdbREDO+=" -sidechainrebuild"
        if "true" in b_pepflip:
            pdbREDO+=" -runpepflip"

        #Rhofit ligand
        if "true" in rho_ligandfromname:
            ligand = input_data.split("/")[8].split("-")[-1]

        elif "false" in rho_ligandfromname:
            if len(rho_ligandcode)>15:
                ligand=rho_ligandcode.replace("rho_ligandcode:","")
            elif len(rho_ligandsmiles)>17:
                ligand=rho_ligandsmiles.replace("rho_ligandsmiles:","")

        rhofitINPUT = f" -rhofit {project_ligand_cif(proj, ligand)}"

        #Keep Hydrogen RhoFit
        keepH=""
        if "true" in rho_keepH:
            keepH=" -keepH"

        #Cluster to search for ligands
        clusterSearch=""
        ncluster="1"
        if len(rho_allclusters)>16:
            if "true" in rho_allclusters.split(":")[-1].lower():
                clusterSearch=" -allclusters"
            else:
                ncluster=rho_xclusters.split(":")[-1]
                if ncluster=="":
                    ncluster=1
                clusterSearch=" -xcluster "+ncluster
        else:
            ncluster=rho_xclusters.split(":")[-1]
            if ncluster=="":
                    ncluster="1"
            clusterSearch=" -xcluster "+ncluster

        #Search mode for RhoFit
        if "thorough" in rho_fittingproc:
            fitrefineMode=" -rhothorough"
        elif "quick" in rho_fittingproc:
            fitrefineMode=" -rhoquick"
        else:
            fitrefineMode=" "
        #Post refine for RhoFit
        if "thorough" in rho_postrefine:
            postrefineMode=" -postthorough"
        elif "standard" in rho_postrefine:
            postrefineMode=" -postref"
        elif "quick" in rho_postrefine:
            postrefineMode=" -postquick"
        else:
            postrefineMode=" "

        scanChirals=""
        if "false" in rho_scanchirals:
            scanChirals=" -nochirals"

        occRef=""
        if "false" in rho_occuprefine:
            occRef=" -nooccref"

        singlePipedreamOut=""
        singlePipedreamOut+= """#!/bin/bash\n"""
        singlePipedreamOut+= """#!/bin/bash\n"""
        singlePipedreamOut+= """#SBATCH -t 99:55:00\n"""
        singlePipedreamOut+= """#SBATCH -J pipedream\n"""
        singlePipedreamOut+= """#SBATCH --exclusive\n"""
        singlePipedreamOut+= """#SBATCH -N1\n"""
        singlePipedreamOut+= """#SBATCH --cpus-per-task=48\n"""
        singlePipedreamOut+= """#SBATCH --mem=220000\n"""
        singlePipedreamOut+= """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/pipedream_"""+ligand+"""_%j_out.txt\n"""
        singlePipedreamOut+= """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/pipedream_"""+ligand+"""_%j_err.txt\n"""
        singlePipedreamOut+= """module purge\n"""
        singlePipedreamOut+= """module load autoPROC BUSTER\n\n"""

        chdir="cd "+"/".join(ppdoutdir.split("/")[:-1])
        ppd="pipedream -h5 "+input_data+" -d "+ppdoutdir+" -xyzin "+userPDBpath+rhofitINPUT+useANISO+refineMode+pdbREDO+keepH+clusterSearch+fitrefineMode+postrefineMode+scanChirals+occRef+" -nofreeref -nthreads -1 -v"

        singlePipedreamOut+=chdir+"\n"
        singlePipedreamOut+=ppd

        script = project_script(proj, f"pipedream_{ligand}.sh")
        with open(script, "w") as ppdsh:
            ppdsh.write(singlePipedreamOut)

        command ='echo "module purge | module load autoPROC BUSTER | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)

    if "alldatasets" in input_data:
        ppddatasetList = list(project_raw_master_h5_files(proj))

        ppdoutdirList = [
            f"{project_process_protein_dir(proj)}/" + x.split(proj.protein + "/")[-1].replace("_master.h5", "") + "/pipedream"
            for x in ppddatasetList]

        userPDBpath = get_user_pdb_path()

        #STARANISO setting
        if "true" in ap_staraniso:
            useANISO=" -useaniso"
        else:
            useANISO=""

        #BUSTER refinement mode
        if "thorough" in b_refinemode:
            refineMode=" -thorough"
        elif "quick" in b_refinemode:
            refineMode=" -quick"
        else:
            refineMode=" "

        #PDB_REDO options
        pdbREDO=""
        if "true" in b_sideaiderefit:
            pdbREDO+=" -remediate"
            refineMode=" -thorough"
        if "true" in b_sideaiderebuild:
            if "remediate" not in pdbREDO:
                pdbREDO+=" -remediate"
            pdbREDO+=" -sidechainrebuild"
        if "true" in b_pepflip:
            pdbREDO+=" -runpepflip"

        #Rhofit ligand


        lib=rho_ligandcode.replace("rho_ligandcode:","")


        #Keep Hydrogen RhoFit
        keepH=""
        if "true" in rho_keepH:
            keepH=" -keepH"

        #Cluster to search for ligands
        clusterSearch=""
        if len(rho_allclusters)>16:
            if "true" in rho_allclusters.split(":")[-1].lower():
                clusterSearch=" -allclusters"
            else:
                ncluster=rho_xclusters.split(":")[-1]
                if ncluster=="":
                    ncluster="1"
                clusterSearch=" -xcluster "+ncluster
        else:
            ncluster=rho_xclusters.split(":")[-1]
            if ncluster=="":
                    ncluster="1"
            clusterSearch=" -xcluster "+ncluster

        #Search mode for RhoFit
        if "thorough" in rho_fittingproc:
            fitrefineMode=" -rhothorough"
        elif "quick" in rho_fittingproc:
            fitrefineMode=" -rhoquick"
        else:
            fitrefineMode=" "
        #Post refine for RhoFit
        if "thorough" in rho_postrefine:
            postrefineMode=" -postthorough"
        elif "standard" in rho_postrefine:
            postrefineMode=" -postref"
        elif "quick" in rho_postrefine:
            postrefineMode=" -postquick"
        else:
            postrefineMode=" "

        scanChirals=""
        if "false" in rho_scanchirals:
            scanChirals=" -nochirals"

        occRef=""
        if "false" in rho_occuprefine:
            occRef=" -nooccref"

        header=""
        header+= """#!/bin/bash\n"""
        header+= """#!/bin/bash\n"""
        header+= """#SBATCH -t 99:55:00\n"""
        header+= """#SBATCH -J pipedream\n"""
        header+= """#SBATCH --exclusive\n"""
        header+= """#SBATCH -N1\n"""
        header+= """#SBATCH --cpus-per-task=40\n"""
        #header+= """#SBATCH --mem=220000\n"""
        header+= """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/pipedream_allDatasets_%j_out.txt\n"""
        header+= """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/pipedream_allDatasets_%j_err.txt\n"""
        header+= """module purge\n"""
        header+= """module load autoPROC BUSTER\n\n"""
        scriptList=list()

        for ppddata,ppdout in zip(ppddatasetList,ppdoutdirList):
            chdir="cd "+"/".join(ppdout.split("/")[:-1])
            if "apo" not in ppddata.lower():
                ligand = ppddata.split("/")[8].split("-")[-1]
                rhofitINPUT = f" -rhofit {project_ligand_cif(proj, ligand)} {keepH}{clusterSearch}" \
                              f"{fitrefineMode}{postrefineMode}{scanChirals}{occRef}"
            if "apo" in ppddata.lower():
                rhofitINPUT=""
            ppd="pipedream -h5 "+ppddata+" -d "+ppdout+" -xyzin "+userPDBpath+rhofitINPUT+useANISO+refineMode+pdbREDO+" -nofreeref -nthreads -1 -v"

            allPipedreamOut=chdir+"\n"
            allPipedreamOut+=chdir.replace("cd ","rm -rf ")+"/pipedream/"+"\n"
            allPipedreamOut+=ppd+"\n\n"

            scriptList.append(allPipedreamOut)
        chunkScripts=[header+"".join(x) for x in list(scrsplit(scriptList,nodes) )]

        for num,chunk in enumerate(chunkScripts):
            time.sleep(0.2)
            script = project_script(proj, f"pipedream_part{num}.sh")
            with open(script, "w") as outfile:
                outfile.write(chunk)

            command ='echo "module purge | module load autoPROC BUSTER | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
            subprocess.call(command,shell=True)


    return render(request,
                  "fragview/jobs_submitted.html",
                  {"command":"<br>".join(ppdCMD.split(";;"))})


def get_pipedream_results(proj, pipedream_csv):
    with open(pipedream_csv, "w") as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow(["sample","summaryFile","fragment","fragmentLibrary","symmetry","resolution","rwork","rfree","rhofitscore","a","b","c","alpha","beta","gamma","ligsvg"])

        pipedreamXML=list()
        for shift_dir in project_shift_dirs(proj):
            xml_glob = f"{shift_dir}/fragmax/process/{proj.protein}/*/*/pipedream/summary.xml"
            pipedreamXML += glob.glob(xml_glob)

        for summary in pipedreamXML:
            try:
                with open(summary,"r") as fd:
                    doc=xmltodict.parse(fd.read())


                sample=doc['GPhL-pipedream']['setup']["runfrom"].split("/")[-1]
                a=doc['GPhL-pipedream']['refdata']["cell"]["a"]
                b=doc['GPhL-pipedream']['refdata']["cell"]["b"]
                c=doc['GPhL-pipedream']['refdata']["cell"]["c"]
                alpha=doc['GPhL-pipedream']['refdata']["cell"]["alpha"]
                beta=doc['GPhL-pipedream']['refdata']["cell"]["beta"]
                gamma=doc['GPhL-pipedream']['refdata']["cell"]["gamma"]
                ligandID=doc['GPhL-pipedream']['ligandfitting']["ligand"]["@id"]
                symm=doc['GPhL-pipedream']['refdata']["symm"]
                rhofitscore=doc['GPhL-pipedream']['ligandfitting']["ligand"]["rhofitsolution"]["correlationcoefficient"]
                R=doc['GPhL-pipedream']['refinement']['Cycle'][-1]["R"]
                Rfree=doc['GPhL-pipedream']['refinement']['Cycle'][-1]["Rfree"]
                resolution=doc['GPhL-pipedream']['inputdata']['table1']['shellstats'][0]['reshigh']
                ligsvg = f"{project_static_url(proj)}/fragmax/process/fragment/{proj.library}/{ligandID}/{ligandID}.svg"
                print(summary.replace("/data/visitors/","/static/").replace(".xml","_out.txt"))
                writer.writerow([
                    sample, summary.replace("/data/visitors/","/static/").replace(".xml",".out"), ligandID,
                    proj.library, symm, resolution, R, Rfree, rhofitscore, a, b, c, alpha, beta, gamma, ligsvg])

            except:
                pass

#############################################

def procReport(request):
    method=""
    report=str(request.GET.get('dataHeader'))
    if "fastdp" in report or "EDNA" in report:
        method="log"
        with open(report.replace("/static/","/data/visitors/"),"r") as readFile:
            report=readFile.readlines()
        report="<br>".join(report)
    return render(request,'fragview/procReport.html', {'reportHTML': report, "method":method})

def refine_datasets(request):
    userInput=str(request.GET.get("submitrfProc"))
    empty,dimpleSW,fspSW,busterSW,refinemode,mrthreshold,refinerescutoff,userPDB,refspacegroup,filters,customrefdimple,customrefbuster,customreffspipe,aimlessopt=userInput.split(";;")
    proj = current_project(request)

    if "false" in dimpleSW:
        useDIMPLE=False
    else:
        useDIMPLE=True
    if "false" in fspSW:
        useFSP=False
    else:
        useFSP=True
    if "false" in busterSW:
        useBUSTER=False
    else:
        useBUSTER=True
    #if len(userPDB)<20:
    pdbmodel=userPDB.replace("pdbmodel:","")
    os.makedirs(proj.data_path()+"/fragmax/models/",mode=0o777, exist_ok=True)
    if pdbmodel!="":
        if pdbmodel in [x.split("/")[-1].split(".pdb")[0] for x in glob.glob(proj.data_path()+"/fragmax/models/*.pdb")]:
            if ".pdb" not in pdbmodel:
                pdbmodel=proj.data_path()+"/fragmax/models/"+pdbmodel+".pdb"
            else:
                pdbmodel=proj.data_path()+"/fragmax/models/"+pdbmodel
        elif "/data/visitors/biomax/" in pdbmodel:

            if not os.path.exists(proj.data_path()+"/fragmax/models/"+pdbmodel.split("/")[-1]):
                shutil.copyfile(pdbmodel,proj.data_path()+"/fragmax/models/"+pdbmodel.split("/")[-1])
                pdbmodel=proj.data_path()+"/fragmax/models/"+pdbmodel.split("/")[-1]
        else:
            if ".pdb" in pdbmodel:
                pdbmodel=pdbmodel.split(".pdb")[0]
            with open(proj.data_path()+"/fragmax/models/"+pdbmodel+".pdb","w") as pdb:
                pdb.write(pypdb.get_pdb_file(pdbmodel, filetype='pdb'))
            pdbmodel=proj.data_path()+"/fragmax/models/"+pdbmodel+".pdb"
    pdbmodel.replace(".pdb.pdb",".pdb")
    spacegroup=refspacegroup.replace("refspacegroup:","")
    run_structure_solving(request, useDIMPLE, useFSP, useBUSTER, pdbmodel, spacegroup,filters,customrefdimple,customrefbuster,customreffspipe,aimlessopt)
    outinfo = "<br>".join(userInput.split(";;"))

    return render(request,'fragview/refine_datasets.html', {'allproc': outinfo})

def ligfit_datasets(request):
    userInput=str(request.GET.get("submitligProc"))
    proj=current_project(request)
    empty,rhofitSW,ligfitSW,ligandfile,fitprocess,scanchirals,customligfit,ligfromname,filters=userInput.split(";;")
    useRhoFit="False"
    useLigFit="False"

    if "true" in rhofitSW:
        useRhoFit="True"
    if "true" in ligfitSW:
        useLigFit="True"

    t1 = threading.Thread(target=autoLigandFit, args=(request, useLigFit, useRhoFit, proj.library, filters))
    t1.daemon = True
    t1.start()
    return render(request,'fragview/ligfit_datasets.html', {'allproc': "<br>".join(userInput.split(";;"))})

def dataproc_datasets(request):
    proj = current_project(request)

    allprc  = str(request.GET.get("submitallProc"))
    dtprc   = str(request.GET.get("submitdtProc"))
    if allprc!="None":
        userinputs=allprc.split(";;")
        dpSW=list()
        dpSW.append("xdsapp")    if ("true" in userinputs[3]) else False
        dpSW.append("xdsxscale") if ("true" in userinputs[2]) else False
        dpSW.append("dials")     if ("true" in userinputs[1]) else False
        dpSW.append("autoproc")  if ("true" in userinputs[4]) else False
        if dpSW==[]:
            dpSW=[""]

        rfSW=list()
        rfSW.append("dimple")     if ("true" in userinputs[12]) else False
        rfSW.append("fspipeline") if ("true" in userinputs[13]) else False
        rfSW.append("buster")     if ("true" in userinputs[14]) else False
        if rfSW==[]:
            rfSW=[""]

        lfSW=list()
        lfSW.append("rhofit") if ("true" in userinputs[19]) else False
        lfSW.append("ligfit") if ("true" in userinputs[20]) else False
        if lfSW==[]:
            lfSW=[""]

        PDBID=userinputs[18].split(":")[-1]

        spg=userinputs[5].split(":")[-1]
        pnodes=10
        shell_script = project_script(proj, "processALL.sh")
        with open(shell_script, "w") as outp:
            outp.write("""#!/bin/bash \n"""
                    """#!/bin/bash \n"""
                    """#SBATCH -t 99:55:00 \n"""
                    """#SBATCH -J FragMAX \n"""
                    """#SBATCH --exclusive \n"""
                    """#SBATCH -N1 \n"""
                    """#SBATCH --cpus-per-task=40 \n"""
                    """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/analysis_workflow_%j_out.txt \n"""
                    """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/analysis_workflow_%j_err.txt \n"""
                    """module purge \n"""
                    """module load DIALS CCP4 autoPROC BUSTER XDSAPP PyMOL \n"""
                    """python """ + project_script(proj, "processALL.py") + """ '""" + proj.data_path() + """' '""" + \
                       proj.library + """' '""" + PDBID+"""' '""" + spg+"""' $1 $2 '""" + ",".join(dpSW) + \
                       """' '""" + ",".join(rfSW) + """' '""" + ",".join(lfSW) + """' \n""")
        for node in range(pnodes):
            command ='echo "module purge | module load CCP4 autoPROC DIALS XDSAPP | sbatch ' + \
                     shell_script + " "+str(node)+" "+str(pnodes)+' " | ssh -F ~/.ssh/ clu0-fe-1'
            subprocess.call(command,shell=True)
            time.sleep(0.2)
        return render(request,'fragview/testpage.html', {
            'dpSW': "<br>".join(dpSW),
            'rfSW': "<br>".join(rfSW),
            'lfSW': "<br>".join(lfSW),
            "pdb":PDBID,
            "sym":spg
            })
    if dtprc!="None":
        dtprc_inp=dtprc.split(";")
        usedials=dtprc_inp[1].split(":")[-1]
        usexdsxscale=dtprc_inp[2].split(":")[-1]
        usexdsapp=dtprc_inp[3].split(":")[-1]
        useautproc=dtprc_inp[4].split(":")[-1]
        spacegroup=dtprc_inp[5].split(":")[-1]
        cellparam=dtprc_inp[6].split(":")[-1]
        friedel=dtprc_inp[7].split(":")[-1]
        datarange=dtprc_inp[8].split(":")[-1]
        rescutoff=dtprc_inp[9].split(":")[-1]
        cccutoff=dtprc_inp[10].split(":")[-1]
        isigicutoff=dtprc_inp[11].split(":")[-1]
        filters=dtprc_inp[-1].split(":")[-1]
        sbatch_script_list=list()
        nodes=3
        if filters!="ALL":
            nodes=1
        if usexdsapp=="true":
            t = threading.Thread(target=run_xdsapp, args=(proj, nodes, filters))
            t.daemon = True
            t.start()
        if usedials=="true":
            t = threading.Thread(target=run_dials, args=(proj, nodes, filters))
            t.daemon = True
            t.start()

        if useautproc=="true":
            t = threading.Thread(target=run_autoproc, args=(proj, nodes, filters))
            t.daemon = True
            t.start()

        if usexdsxscale=="true":
            t = threading.Thread(target=run_xdsxscale, args=(proj, nodes, filters))
            t.daemon = True
            t.start()

        return render(request,'fragview/dataproc_datasets.html', {'allproc': "Jobs submitted using "+str(nodes)+" per method"})



    return render(request,'fragview/dataproc_datasets.html', {'allproc': ""})

##############################################


def run_xdsapp(proj, nodes, filters):
    if "filters:" in filters:
        filters=filters.split(":")[-1]

    if filters=="ALL":
        filters=""

    header= """#!/bin/bash\n"""
    header+= """#!/bin/bash\n"""
    header+= """#SBATCH -t 99:55:00\n"""
    header+= """#SBATCH -J XDSAPP\n"""
    header+= """#SBATCH --exclusive\n"""
    header+= """#SBATCH -N1\n"""
    header+= """#SBATCH --cpus-per-task=40\n"""
    #header+= """#SBATCH --mem=220000\n"""
    header+= """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/xdsapp_fragmax_%j_out.txt\n"""
    header+= """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/xdsapp_fragmax_%j_err.txt\n"""
    header+= """module purge\n\n"""
    header+= """module load CCP4 XDSAPP\n\n"""

    scriptList=list()

    xml_files = sorted(x for x in project_xml_files(proj) if filters in x)

    for xml in xml_files:
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc=doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir=os.path.join(proj.data_path(),"fragmax","process",proj.protein,dtc["imagePrefix"],dtc["imagePrefix"]+"_"+dtc["dataCollectionNumber"])
        h5master=dtc["imageDirectory"]+"/"+dtc["fileTemplate"].replace("%06d.h5","")+"master.h5"
        nImg=dtc["numberOfImages"]

        script="cd "+outdir+"/xdsapp\n"
        script+='xdsapp --cmd --dir='+outdir+'/xdsapp -j 8 -c 5 -i '+h5master+' --delphi=10 --fried=True --range=1\ '+nImg+' \n\n'
        scriptList.append(script)
        os.makedirs(outdir,mode=0o760, exist_ok=True)
        os.makedirs(outdir+"/xdsapp",mode=0o760, exist_ok=True)

    chunkScripts=[header+"".join(x) for x in list(scrsplit(scriptList,nodes) )]
    for num,chunk in enumerate(chunkScripts):
        time.sleep(0.2)

        script = project_script(proj, f"xdsapp_fragmax_part{num}.sh")
        with open(script, "w") as outfile:
            outfile.write(chunk)

        command ='echo "module purge | module load CCP4 XDSAPP DIALS | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)
        print(f"running command '{command}'")

def run_autoproc(proj, nodes, filters):
    if "filters:" in filters:
        filters=filters.split(":")[-1]

    if filters=="ALL":
        filters=""

    header= """#!/bin/bash\n"""
    header+= """#!/bin/bash\n"""
    header+= """#SBATCH -t 99:55:00\n"""
    header+= """#SBATCH -J autoPROC\n"""
    header+= """#SBATCH --exclusive\n"""
    header+= """#SBATCH -N1\n"""
    header+= """#SBATCH --cpus-per-task=40\n"""
    #header+= """#SBATCH --mem=220000\n"""
    header+= """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/autoproc_fragmax_%j_out.txt\n"""
    header+= """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/autoproc_fragmax_%j_err.txt\n"""
    header+= """module purge\n\n"""
    header+= """module load CCP4 autoPROC\n\n"""

    scriptList=list()

    xml_files = sorted(x for x in project_xml_files(proj) if filters in x)

    for xml in xml_files:
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc=doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir=os.path.join(proj.data_path(),"fragmax","process",proj.protein,dtc["imagePrefix"],dtc["imagePrefix"]+"_"+dtc["dataCollectionNumber"])
        h5master=dtc["imageDirectory"]+"/"+dtc["fileTemplate"].replace("%06d.h5","")+"master.h5"
        nImg=dtc["numberOfImages"]
        os.makedirs(outdir,mode=0o760, exist_ok=True)
        script="cd "+outdir+"\n"
        script+='''process -h5 '''+h5master+''' -noANO autoPROC_Img2Xds_UseXdsPlugins_DectrisHdf5="durin-plugin" autoPROC_XdsKeyword_LIB=\$EBROOTNEGGIA/lib/dectris-neggia.so autoPROC_XdsKeyword_ROTATION_AXIS='0  -1 0' autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_JOBS=8 autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_PROCESSORS=5 autoPROC_XdsKeyword_DATA_RANGE=1\ '''+nImg+''' autoPROC_XdsKeyword_SPOT_RANGE=1\ '''+nImg+''' -d '''+outdir+'''/autoproc\n\n'''
        scriptList.append(script)

    chunkScripts=[header+"".join(x) for x in list(scrsplit(scriptList,nodes) )]

    for num,chunk in enumerate(chunkScripts):
        time.sleep(0.2)

        script = project_script(proj, f"autoproc_fragmax_part{num}.sh")
        with open(script, "w") as outfile:
            outfile.write(chunk)
        command ='echo "module purge | module load CCP4 autoPROC DIALS | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)

def run_xdsxscale(proj, nodes, filters):
    if "filters:" in filters:
        filters=filters.split(":")[-1]

    if filters=="ALL":
        filters=""


    header= """#!/bin/bash\n"""
    header+= """#!/bin/bash\n"""
    header+= """#SBATCH -t 99:55:00\n"""
    header+= """#SBATCH -J xdsxscale\n"""
    header+= """#SBATCH --exclusive\n"""
    header+= """#SBATCH -N1\n"""
    header+= """#SBATCH --cpus-per-task=40\n"""
    #header+= """#SBATCH --mem=220000\n"""
    header+= """#SBATCH --mem-per-cpu=2000\n"""
    header+= """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/xdsxscale_fragmax_%j_out.txt\n"""
    header+= """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/xdsxscale_fragmax_%j_err.txt\n"""
    header+= """module purge\n\n"""
    header+= """module load PReSTO\n\n"""

    scriptList=list()

    with open(project_script(proj, "filter.txt"), "w") as inp:
        inp.write(filters)

    xml_files = sorted(x for x in project_xml_files(proj) if filters in x)

    for xml in xml_files:
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc=doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir=os.path.join(proj.data_path(),"fragmax","process",proj.protein,dtc["imagePrefix"],dtc["imagePrefix"]+"_"+dtc["dataCollectionNumber"])
        h5master=dtc["imageDirectory"]+"/"+dtc["fileTemplate"].replace("%06d.h5","")+"master.h5"
        nImg=dtc["numberOfImages"]
        os.makedirs(outdir,mode=0o760, exist_ok=True)
        os.makedirs(outdir+"/xdsxscale",mode=0o760, exist_ok=True)


        script="cd "+outdir+"/xdsxscale \n"
        script+="xia2 goniometer.axes=0,1,0  pipeline=3dii failover=true  nproc=40 image="+h5master+":1:"+nImg+" multiprocessing.mode=serial multiprocessing.njob=1 multiprocessing.nproc=auto\n\n"
        scriptList.append(script)

    chunkScripts=[header+"".join(x) for x in list(scrsplit(scriptList,nodes) )]


    for num,chunk in enumerate(chunkScripts):
        time.sleep(0.2)

        script = project_script(proj, f"xdsxscale_fragmax_part{num}.sh")
        with open(script, "w") as outfile:
            outfile.write(chunk)

        command ='echo "module purge | module load CCP4 XDSAPP DIALS | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)

def run_dials(proj, nodes, filters):
    if "filters:" in filters:
        filters=filters.split(":")[-1]

    if filters=="ALL":
        filters=""

    header= """#!/bin/bash\n"""
    header+= """#!/bin/bash\n"""
    header+= """#SBATCH -t 99:55:00\n"""
    header+= """#SBATCH -J DIALS\n"""
    header+= """#SBATCH --exclusive\n"""
    header+= """#SBATCH -N1\n"""
    header+= """#SBATCH --cpus-per-task=40\n"""
    #header+= """#SBATCH --mem=220000\n"""
    header+= """#SBATCH --mem-per-cpu=2000\n"""

    header+= """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/dials_fragmax_%j_out.txt\n"""
    header+= """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/dials_fragmax_%j_err.txt\n"""
    header+= """module purge\n\n"""
    header+= """module load CCP4 XDS DIALS\n\n"""

    scriptList=list()

    xml_files = sorted(x for x in project_xml_files(proj) if filters in x)

    for xml in xml_files:
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc=doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir=os.path.join(proj.data_path(),"fragmax","process",proj.protein,dtc["imagePrefix"],dtc["imagePrefix"]+"_"+dtc["dataCollectionNumber"])
        h5master=dtc["imageDirectory"]+"/"+dtc["fileTemplate"].replace("%06d.h5","")+"master.h5"
        nImg=dtc["numberOfImages"]
        os.makedirs(outdir,mode=0o760, exist_ok=True)
        os.makedirs(outdir+"/dials",mode=0o760, exist_ok=True)


        script="cd "+outdir+"/dials \n"
        script+="xia2 goniometer.axes=0,1,0 pipeline=dials failover=true  nproc=40 image="+h5master+":1:"+nImg+" multiprocessing.mode=serial multiprocessing.njob=1 multiprocessing.nproc=auto\n\n"
        scriptList.append(script)

    chunkScripts=[header+"".join(x) for x in list(scrsplit(scriptList,nodes) )]


    for num,chunk in enumerate(chunkScripts):
        time.sleep(0.2)

        script = project_script(proj, f"dials_fragmax_part{num}.sh")
        with open(script, "w") as outfile:
            outfile.write(chunk)

        command ='echo "module purge | module load CCP4 XDSAPP DIALS | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)

def process2results(request, spacegroup, filters, aimlessopt):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions(request)
    for dp in ["xdsapp","autoproc","xdsxscale","EDNA","fastdp","dials"]:
        #[os.makedirs("/".join(x.split("/")[:9]+x.split("/")[10:]).replace("/process/","/results/")+dp, mode=0o760, exist_ok=True) for x in glob.glob(path+"/fragmax/process/AR/*/*/")]
        [os.makedirs("/".join(x.split("/")[:8]+x.split("/")[10:]).replace("/process/","/results/")+dp, mode=0o760, exist_ok=True) for x in glob.glob(path+"/fragmax/process/"+acr+"/*/*/")]
    with open(path+"/fragmax/scripts/process2results.py","w") as writeFile:
        writeFile.write('''import os '''
                '''\nimport glob'''
                '''\nimport subprocess'''
                '''\nimport shutil'''
                '''\nimport sys'''
                '''\npath="%s"'''
                '''\nacr="%s"'''
                '''\nspg="%s"'''
                '''\naimless="%s"'''
                '''\nsubprocess.call("rm "+path+"/fragmax/results/"+acr+"*/*/*merged.mtz",shell=True)'''
                '''\ndatasetList=glob.glob(path+"/fragmax/process/"+acr+"/*/*/")'''
                '''\nfor dataset in datasetList:    '''
                '''\n    if glob.glob(dataset+"autoproc/*mtz")!=[]:'''
                '''\n        try:'''
                '''\n            srcmtz=[x for x in glob.glob(dataset+"autoproc/*mtz") if "staraniso" in x][0]'''
                '''\n        except IndexError:'''
                '''\n            try:'''
                '''\n                srcmtz=[x for x in glob.glob(dataset+"autoproc/*mtz") if "aimless" in x][0]'''
                '''\n            except IndexError:'''
                '''\n                srcmtz=[x for x in glob.glob(dataset+"autoproc/*mtz")][0]'''
                '''\n    dstmtz=path+"/fragmax/results/"+dataset.split("/")[-2]+"/autoproc/"+dataset.split("/")[-2]+"_autoproc_merged.mtz"'''
                '''\n    if not os.path.exists(dstmtz) and os.path.exists(srcmtz):            '''
                '''\n        shutil.copyfile(srcmtz,dstmtz)'''
                '''\n        cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "'''
                '''\n        if aimless=="true":'''
                '''\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)        '''
                '''\n    srcmtz=dataset+"dials/DEFAULT/scale/AUTOMATIC_DEFAULT_scaled.mtz"'''
                '''\n    if os.path.exists(srcmtz):'''
                '''\n        dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/dials/"+dataset.split("/")[-2]+"_dials_merged.mtz"'''
                '''\n        if not os.path.exists(dstmtz) and os.path.exists(srcmtz):            '''
                '''\n            shutil.copyfile(srcmtz,dstmtz)            '''
                '''\n            cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "'''
                '''\n        if aimless=="true":'''
                '''\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)        '''
                '''\n    srcmtz=dataset+"xdsxscale/DEFAULT/scale/AUTOMATIC_DEFAULT_scaled.mtz"'''
                '''\n    if os.path.exists(srcmtz):'''
                '''\n        dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/xdsxscale/"+dataset.split("/")[-2]+"_xdsxscale_merged.mtz"'''
                '''\n        if not os.path.exists(dstmtz) and os.path.exists(srcmtz):            '''
                '''\n            shutil.copyfile(srcmtz,dstmtz)            '''
                '''\n            cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "'''
                '''\n        if aimless=="true":'''
                '''\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)        '''
                '''\n    mtzoutList=glob.glob(dataset+"xdsapp/*F.mtz")'''
                '''\n    if mtzoutList!=[]:'''
                '''\n        srcmtz=mtzoutList[0]    '''
                '''\n    if os.path.exists(srcmtz):                '''
                '''\n        dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/xdsapp/"+dataset.split("/")[-2]+"_xdsapp_merged.mtz"        '''
                '''\n        if not os.path.exists(dstmtz) and os.path.exists(srcmtz):'''
                '''\n            shutil.copyfile(srcmtz,dstmtz)        '''
                '''\n            cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "'''
                '''\n        if aimless=="true":'''
                '''\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)        '''
                '''\n    mtzoutList=glob.glob(path+"/process/"+acr+"/"+dataset.split("/")[-3]+"/*"+dataset.split("/")[-2]+"*/EDNA_proc/results/*_noanom_aimless.mtz")'''
                '''\n    if mtzoutList!=[]:'''
                '''\n        srcmtz=mtzoutList[0]    '''
                '''\n    dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/EDNA/"+dataset.split("/")[-2]+"_EDNA_merged.mtz"        '''
                '''\n    if not os.path.exists(dstmtz) and os.path.exists(srcmtz):'''
                '''\n        shutil.copyfile(srcmtz,dstmtz)        '''
                '''\n        cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "'''
                '''\n        if aimless=="true":'''
                '''\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)        '''
                '''\n    mtzoutList=glob.glob(path+"/process/"+acr+"/"+dataset.split("/")[-3]+"/*"+dataset.split("/")[-2]+"*/fastdp/results/*_noanom_fast_dp.mtz.gz")'''
                '''\n    if mtzoutList!=[]:'''
                '''\n        srcmtz=mtzoutList[0]        '''
                '''\n        if os.path.exists(srcmtz):                '''
                '''\n            dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/fastdp/"+dataset.split("/")[-2]+"_fastdp_merged.mtz"        '''
                '''\n            if not os.path.exists(dstmtz) and os.path.exists(srcmtz):'''
                '''\n                shutil.copyfile(srcmtz,dstmtz)'''
                '''\n                try:'''
                '''\n                    subprocess.check_call(['gunzip', dstmtz+".gz"])'''
                '''\n                except:'''
                '''\n                    pass'''
                '''\n                a=dataset.split("process/")[0]+"results/"+dataset+"/fastdp/"+dataset+"_fastdp_unmerged.mtz"'''
                '''\n                cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "'''
                '''\n        if aimless=="true":'''
                '''\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)'''%(path,acr,spacegroup,aimlessopt))






    proc2resOut=""

    #define env for script for dimple
    proc2resOut+= """#!/bin/bash\n"""
    proc2resOut+= """#!/bin/bash\n"""
    proc2resOut+= """#SBATCH -t 99:55:00\n"""
    proc2resOut+= """#SBATCH -J Pro2Res\n"""
    proc2resOut+= """#SBATCH --exclusive\n"""
    proc2resOut+= """#SBATCH -N1\n"""
    proc2resOut+= """#SBATCH --cpus-per-task=48\n"""
    proc2resOut+= """#SBATCH --mem=220000\n"""
    proc2resOut+= """#SBATCH -o """+path+"""/fragmax/logs/process2results_%j_out.txt\n"""
    proc2resOut+= """#SBATCH -e """+path+"""/fragmax/logs/process2results_%j_err.txt\n"""
    proc2resOut+= """module purge\n"""
    proc2resOut+= """module load CCP4 Phenix\n\n"""


    #HARD CODED
    #dimpleOut+=" & ".join(dimp)
    proc2resOut+="\n\n"
    proc2resOut+="python "+path+"/fragmax/scripts/process2results.py "
    with open(path+"/fragmax/scripts/run_proc2res.sh","w") as outp:
        outp.write(proc2resOut)

def run_structure_solving(request, useDIMPLE, useFSP, useBUSTER, userPDB, spacegroup, filters,customrefdimple,customrefbuster,customreffspipe,aimlessopt):
    #proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions(request)
    proj = current_project(request)
    customreffspipe = customreffspipe.split("customrefinefspipe:")[-1]
    customrefbuster = customrefbuster.split("customrefinebuster:")[-1]
    customrefdimple = customrefdimple.split("customrefinedimple:")[-1]
    aimlessopt      = aimlessopt.split("aimlessopt:")[-1]
    argsfit="none"
    if "filters:" in filters:
        filters=filters.split(":")[-1]
    if filters=="ALL":
        filters=""
    process2results(request, spacegroup, filters,aimlessopt)
    with open(proj.data_path()+'/fragmax/scripts/run_queueREF.py',"w") as writeFile:
        writeFile.write('''\nimport commands, os, sys, glob, time, subprocess'''
                        '''\nargsfit=sys.argv[1]'''
                        '''\npath=sys.argv[2]'''
                        '''\nacr=sys.argv[3]'''
                        '''\nPDBfile=sys.argv[4]'''
                        '''\ncmd = "sbatch "+path+"/fragmax/scripts/run_proc2res.sh"'''
                        '''\nstatus, jobnum1 = commands.getstatusoutput(cmd)'''
                        '''\njobnum1=jobnum1.split("batch job ")[-1]'''
                        '''\ninputData=list()'''
                        '''\nfor proc in glob.glob(path+"/fragmax/results/"+acr+"*/*/"):'''
                        '''\n    mtzList=glob.glob(proc+"*mtz")'''
                        '''\n    if mtzList and "'''+filters+'''" in proc:'''
                        '''\n        inputData.append(sorted(glob.glob(proc+"*mtz"))[0])'''
                        '''\ndef scrsplit(a, n):'''
                        '''\n    k, m = divmod(len(a), n)'''
                        '''\n    return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))'''
                        '''\nif "dimple" in argsfit:'''
                        '''\n    cmd = "sbatch --dependency=afterany:%s %s/fragmax/scripts/run_dimple.sh" % (jobnum1,path)'''
                        '''\n    status,jobnum2 = commands.getstatusoutput(cmd)'''
                        '''\nif "fspipeline" in argsfit:'''
                        '''\n    cmd = "sbatch --dependency=afterany:%s %s/fragmax/scripts/fspipeline_master.sh" % (jobnum1,path)'''
                        '''\n    status,jobnum3 = commands.getstatusoutput(cmd)'''
                        '''\nif "buster" in argsfit:'''
                        '''\n    cmd = "sbatch --dependency=afterany:%s %s/fragmax/scripts/buster_master.sh" % (jobnum1,path)'''
                        '''\n    status,jobnum4 = commands.getstatusoutput(cmd)''')
    def fspipeline_hpc(PDB):
        inputData=list()
        scriptList=list()
        m=0
        inputData=list()
        fsp='''python /data/staff/biomax/guslim/FragMAX_dev/fm_bessy/fspipeline.py --sa=false --refine='''+PDB+''' --exclude="dimple fspipeline buster unmerged rhofit ligfit truncate" --cpu=2 '''+customreffspipe
        for proc in glob.glob(proj.data_path()+"/fragmax/results/"+proj.protein+"*/*/"):
            mtzList=glob.glob(proc+"*mtz")
            if mtzList and filters in proc:
                inputData.append(sorted(glob.glob(proc+"*mtz"))[0])
        scriptList=["cd "+"/".join(x.split("/")[:-1])+"/ \n"+fsp for x in inputData]
        nodes=round(len(inputData)/48 + 0.499)
        node0=64-nodes

        for n,i in enumerate(list(scrsplit(scriptList,nodes))):
            header='''#!/bin/bash\n'''
            header+='''#!/bin/bash\n'''
            header+='''#SBATCH -t 04:00:00\n'''
            header+='''#SBATCH -J FSpipeline\n'''
            #header+='''#SBATCH --nodelist=cn'''+str(node0+n)+'''\n'''
            header+='''#SBATCH --nice=25\n'''
            header+='''#SBATCH --cpus-per-task=2\n'''
            header+='''#SBATCH --mem=5000\n'''
            header+='''#SBATCH -o '''+proj.data_path()+'''/fragmax/logs/fsp_fragmax_%j_out.txt\n'''
            header+='''#SBATCH -e '''+proj.data_path()+'''/fragmax/logs/fsp_fragmax_%j_err.txt\n\n'''
            header+='''module purge\n'''
            header+='''module load CCP4 Phenix\n'''
            header+='''echo export TMPDIR='''+proj.data_path()+'''/fragmax/logs/\n\n'''
            for j in i:
                with open(proj.data_path()+"/fragmax/scripts/fspipeline_worker_"+str(m)+".sh","w") as writeFile:
                    writeFile.write(header+j)
                m+=1
        with open(proj.data_path()+"/fragmax/scripts/fspipeline_master.sh","w") as writeFile:
            writeFile.write("""#!/bin/bash\n"""
                            """#!/bin/bash\n"""
                            """#SBATCH -t 01:00:00\n"""
                            """#SBATCH -J FSPmaster\n\n"""
                            """#SBATCH -o """+proj.data_path()+"""/fragmax/logs/fspipeline_master_%j_out.txt\n"""
                            """for file in """+proj.data_path()+"/fragmax/scripts"+"""/fspipeline_worker*.sh; do   sbatch $file;   sleep 0.1; rm $file; done\n"""
                            """""")

    def buster_hpc(PDB):
        inputData=list()
        scriptList=list()
        m=0
        for proc in glob.glob(proj.data_path()+"/fragmax/results/"+proj.protein+"*/*/"):
            mtzList=glob.glob(proc+"*mtz")
            if mtzList and filters in proc:
                inputData.append(sorted(glob.glob(proc+"*mtz"))[0])
        nodes=round(len(inputData)/48 + 0.499)
        node0=54-nodes
        for n,srcmtz in enumerate(inputData):
            cmd=""
            dstmtz=srcmtz.replace("merged","truncate")
            if os.path.exists("/".join(srcmtz.split("/")[:-1])+"/buster"):
                cmd+="rm -rf "+"/".join(srcmtz.split("/")[:-1])+"/buster\n\n"
            if not os.path.exists(dstmtz):
                cmd+='echo "truncate yes \labout F=FP SIGF=SIGFP" | truncate hklin '+srcmtz+' hklout '+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/truncate.log\n\n"
            cmd+="refine -L -p "+PDB+" -m "+dstmtz+" "+customrefbuster+" -TLS -nthreads 2 -d "+"/".join(srcmtz.split("/")[:-1])+"/buster \n"
            scriptList.append(cmd)
        for n,i in enumerate(list(scrsplit(scriptList,nodes))):
            header='''#!/bin/bash\n'''
            header+='''#!/bin/bash\n'''
            header+='''#SBATCH -t 04:00:00\n'''
            header+='''#SBATCH -J BUSTER\n'''
            header+='''#SBATCH --cpus-per-task=2\n'''
            header+='''#SBATCH --mem=5000\n'''
            header+='''#SBATCH --nice=25\n'''
            header+='''#SBATCH --nodelist=cn'''+str(node0+n)+'''\n'''
            header+='''#SBATCH -o '''+proj.data_path()+'''/fragmax/logs/buster_fragmax_%j_out.txt\n'''
            header+='''#SBATCH -e '''+proj.data_path()+'''/fragmax/logs/buster_fragmax_%j_err.txt\n\n'''
            header+='''module purge\n'''
            header+='''module load autoPROC BUSTER\n'''
            header+='''echo export TMPDIR='''+proj.data_path()+'''/fragmax/logs/\n\n'''
            for j in i:
                with open(proj.data_path()+"/fragmax/scripts/buster_worker_"+str(m)+".sh","w") as writeFile:
                    writeFile.write(header+j)
                m+=1
        with open(proj.data_path()+"/fragmax/scripts/buster_master.sh","w") as writeFile:
            writeFile.write("""#!/bin/bash\n"""
                            """#!/bin/bash\n"""
                            """#SBATCH -t 01:00:00\n"""
                            """#SBATCH -J BSTRmaster\n\n"""
                            """#SBATCH -o """+proj.data_path()+"""/fragmax/logs/buster_master_%j_out.txt\n"""
                            """for file in """+proj.data_path()+"/fragmax/scripts"+"""/buster_worker*.sh; do   sbatch $file;   sleep 0.1; rm $file; done\n"""
                            """rm buster_worker*sh""")

    def dimple_hpc(PDB):
        #Creates HPC script to run dimple on all mtz files provided.
        #PDB _file can be provided in the header of the python script and parse to all
        #pipelines (Dimple, pipedream, bessy)


        ##This line will make dimple run on unscaled unmerged files. It seems that works
        ##better sometimes

        outDirs=list()
        inputData=list()
        dimpleOut=""

        #define env for script for dimple
        dimpleOut+= """#!/bin/bash\n"""
        dimpleOut+= """#!/bin/bash\n"""
        dimpleOut+= """#SBATCH -t 99:55:00\n"""
        dimpleOut+= """#SBATCH -J dimple\n"""
        dimpleOut+= """#SBATCH --exclusive\n"""
        dimpleOut+= """#SBATCH -N1\n"""
        dimpleOut+= """#SBATCH --cpus-per-task=48\n"""
        dimpleOut+= """#SBATCH --mem=220000\n"""
        dimpleOut+= """#SBATCH -o """+proj.data_path()+"""/fragmax/logs/dimple_fragmax_%j_out.txt\n"""
        dimpleOut+= """#SBATCH -e """+proj.data_path()+"""/fragmax/logs/dimple_fragmax_%j_err.txt\n"""
        dimpleOut+= """module purge\n"""
        dimpleOut+= """module load CCP4 Phenix \n\n"""

        dimpleOut+="python "+proj.data_path()+"/fragmax/scripts/run_dimple.py"
        dimpleOut+="\n\n"

        with open(proj.data_path()+"/fragmax/scripts/run_dimple.sh","w") as outp:
            outp.write(dimpleOut)


        with open(proj.data_path()+"/fragmax/scripts/run_dimple.py","w") as writeFile:
            writeFile.write('''import multiprocessing\n'''
                            '''import subprocess\n'''
                            '''import glob\n'''
                            '''\n'''
                            '''\n'''
                            '''path="%s"\n'''
                            '''acr="%s"\n'''
                            '''PDB="%s"\n'''
                            '''\n'''
                            '''inputData=list()\n'''
                            '''for proc in glob.glob(path+"/fragmax/results/"+acr+"*/*/"):\n'''
                            '''    mtzList=glob.glob(proc+"*mtz")\n'''
                            '''    if mtzList and "%s" in proc:\n'''
                            '''        inputData.append(sorted(glob.glob(proc+"*mtz"))[0])\n'''
                            '''\n'''
                            '''outDirs=["/".join(x.split("/")[:-1])+"/dimple" for x in inputData]\n'''
                            '''mtzList=inputData\n'''
                            '''\n'''
                            '''inpdata=list()\n'''
                            '''for a,b in zip(outDirs,mtzList):\n'''
                            '''    inpdata.append([a,b])\n'''
                            '''    \n'''
                            '''def fragmax_worker((di, mtz)):\n'''
                            '''    command="dimple -s "+mtz+" "+PDB+" "+di+" %s ; cd "+di+" ; phenix.mtz2map final.mtz"\n'''
                            '''    subprocess.call(command, shell=True) \n'''
                            '''def mp_handler():\n'''
                            '''    p = multiprocessing.Pool(48)\n'''
                            '''    p.map(fragmax_worker, inpdata)\n'''
                            '''if __name__ == "__main__":\n'''
                            '''    mp_handler()\n'''%(proj.data_path(),proj.protein,PDB,filters,customrefdimple))

    if userPDB!="":
        if useFSP:
            fspipeline_hpc(userPDB)
            argsfit+="fspipeline"
        if useDIMPLE:
            dimple_hpc(userPDB)
            argsfit+="dimple"
        if useBUSTER:
            buster_hpc(userPDB)
            argsfit+="buster"
    else:
        userPDB="-"

    command ='echo "python '+proj.data_path()+'/fragmax/scripts/run_queueREF.py '+argsfit+' '+proj.data_path()+' '+proj.protein+' '+userPDB+' " | ssh -F ~/.ssh/ clu0-fe-1'
    subprocess.call("rm "+proj.data_path()+"/fragmax/scripts/*.setvar.lis",shell=True)
    subprocess.call("rm "+proj.data_path()+"/fragmax/scripts/slurm*_out.txt",shell=True)
    subprocess.call(command,shell=True)

def autoLigandFit(request, useLigFit,useRhoFit,fraglib,filters):
    #proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions(request)
    proj = current_project(request)

    if "filters:" in filters:
        filters=filters.split(":")[-1]
    if filters=="ALL":
        filters=""
    with open(proj.data_path()+"/fragmax/scripts/autoligand.py","w") as writeFile:
        writeFile.write('''import multiprocessing\n'''
                '''import time\n'''
                '''import subprocess\n'''
                '''import sys\n'''
                '''import glob\n'''
                '''import os\n'''
                '''path="'''+proj.data_path()+'''"\n'''
                '''fraglib="'''+proj.library+'''"\n'''
                '''acr="'''+proj.protein+'''"\n'''
                '''shiftList="'''+proj.shift_list+'''"\n'''
                '''fitmethod=sys.argv[4]\n'''
                '''pdbList=list()\n'''
                '''shiftList=shiftList.split(",")\n'''
                '''for s in shiftList:\n'''
                '''    p="/data/visitors/biomax/'''+proj.proposal+'''/"+s\n'''
                '''    pdbList+=glob.glob(p+"/fragmax/results/"+acr+"*/*/*/final.pdb")\n'''
                '''pdbList=[x for x in pdbList if "Apo" not in x and "'''+filters+'''" in x]\n'''
                '''cifList=list()\n'''
                '''mtzList=[x.replace(".pdb",".mtz") for x in pdbList]\n'''
                '''outListR=[x.replace("final.pdb","rhofit/") for x in pdbList]\n'''
                '''outListP=[x.replace("final.pdb","ligfit/") for x in pdbList]\n'''
                '''for i in pdbList:\n'''
                '''    fragID=i.split("/")[8].split("-")[-1].split("_")[0]\n'''
                '''    cifList.append(path+"/fragmax/process/fragment/"+fraglib+"/"+fragID+"/"+fragID+".cif")\n'''
                '''inpdataR=list()\n'''
                '''inpdataP=list()\n'''
                '''for a,b,c,d in zip(cifList,mtzList,pdbList,outListR):\n'''
                '''    inpdataR.append([a,b,c,d])\n'''
                '''for a,b,c,d in zip(cifList,mtzList,pdbList,outListP):\n'''
                '''    inpdataP.append([a,b,c,d])\n'''
                '''def fit_worker((cif, mtz, pdb, out)):\n'''
                '''    if fitmethod=="rhofit":\n'''
                '''        if os.path.exists(out):\n'''
                '''            os.system("rm -rf "+out)\n'''
                '''        command="rhofit -l %s -m %s -p %s -d %s" %(cif, mtz, pdb, out)\n'''
                '''        subprocess.call(command, shell=True) \n'''
                '''    if fitmethod=="ligfit":\n'''
                '''        out="/".join(out.split("/")[:-1])\n'''
                '''        if not os.path.exists(out):\n'''
                '''            os.makedirs(out)\n'''
                '''            command="cd %s && phenix.ligandfit data=%s model=%s ligand=%s fill=True clean_up=True" %(out,mtz, pdb, cif)    \n'''
                '''            subprocess.call(command, shell=True) \n'''
                '''def mp_handler():\n'''
                '''    p = multiprocessing.Pool(48)\n'''
                '''    if fitmethod=="ligfit":\n'''
                '''        p.map(fit_worker, inpdataP)\n'''
                '''    if fitmethod=="rhofit":\n'''
                '''        p.map(fit_worker, inpdataR)\n'''
                '''if __name__ == '__main__':\n'''
                '''    mp_handler()\n''')





    script=proj.data_path()+"/fragmax/scripts/autoligand.sh"
    if "True" in useRhoFit:
        with open(proj.data_path()+"/fragmax/scripts/autoligand.sh","w") as writeFile:
            writeFile.write('''#!/bin/bash\n'''
                    '''#!/bin/bash\n'''
                    '''#SBATCH -t 99:55:00\n'''
                    '''#SBATCH -J autoRhofit\n'''
                    '''#SBATCH --exclusive\n'''
                    '''#SBATCH -N1\n'''
                    '''#SBATCH --cpus-per-task=48\n'''
                    '''#SBATCH -o '''+proj.data_path()+'''/fragmax/logs/auto_rhofit_%j_out.txt\n'''
                    '''#SBATCH -e '''+proj.data_path()+'''/fragmax/logs/auto_rhofit_%j_err.txt\n'''
                    '''module purge\n'''
                    '''module load autoPROC BUSTER Phenix CCP4\n'''
                    '''python '''+proj.data_path()+'''/fragmax/scripts/autoligand.py '''+proj.data_path()+''' '''+proj.library+''' '''+proj.protein+''' rhofit\n''')
        command ='echo "module purge | module load BUSTER CCP4 | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)
    if "True" in useLigFit:
        with open(proj.data_path()+"/fragmax/scripts/autoligand.sh","w") as writeFile:
            writeFile.write('''#!/bin/bash\n'''
                    '''#!/bin/bash\n'''
                    '''#SBATCH -t 3:00:00\n'''
                    '''#SBATCH -J autoLigfit\n'''
                    '''#SBATCH --exclusive\n'''
                    '''#SBATCH -N1\n'''
                    '''#SBATCH --cpus-per-task=48\n'''
                    '''#SBATCH -o '''+proj.data_path()+'''/fragmax/logs/auto_ligfit_%j_out.txt\n'''
                    '''#SBATCH -e '''+proj.data_path()+'''/fragmax/logs/auto_ligfit_%j_err.txt\n'''
                    '''module purge\n'''
                    '''module load autoPROC BUSTER Phenix CCP4\n'''
                    '''python '''+proj.data_path()+'''/fragmax/scripts/autoligand.py '''+proj.data_path()+''' '''+proj.library+''' '''+proj.protein+''' ligfit\n''')
        command ='echo "module purge | module load CCP4 Phenix | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)





###############################
def scrsplit(a, n):
    k, m = divmod(len(a), n)
    return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))

def split_b(target,ini,end):
    return target.split(ini)[-1].split(end)[0]
