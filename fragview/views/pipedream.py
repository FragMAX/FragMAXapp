import os
import csv
import time
import pypdb
import shutil
import natsort
import xmltodict
import subprocess
from os import path
from glob import glob
from django.shortcuts import render
from fragview import hpc
from fragview.projects import current_project, project_raw_master_h5_files, project_process_protein_dir
from fragview.projects import project_shift_dirs, project_static_url, project_model_path, project_ligand_cif
from fragview.projects import project_script
from .utils import scrsplit


def processing_form(request):
    proj = current_project(request)

    datasetPathList = project_raw_master_h5_files(proj)
    datasetPathList = natsort.natsorted(datasetPathList,
                                        # sort by dataset names
                                        path.basename)

    datasetNameList = [i.split("/")[-1].replace("_master.h5", "") for i in datasetPathList if "ref-" not in i]
    datasetList = zip(datasetPathList, datasetNameList)

    return render(request, "fragview/pipedream.html", {"data": datasetList})


def results(request):
    proj = current_project(request)
    pipedream_csv = path.join(project_process_protein_dir(proj), "pipedream.csv")

    resync = str(request.GET.get("resync"))
    if "resyncresults" in resync:
        get_pipedream_results(proj, pipedream_csv)

    if not path.exists(pipedream_csv):
        get_pipedream_results(proj, pipedream_csv)

    if path.exists(pipedream_csv):
        with open(pipedream_csv, "r") as readFile:
            reader = csv.reader(readFile)
            lines = list(reader)[1:]

        return render(request, "fragview/pipedream_results.html", {"lines": lines})
    else:
        return render(request, "fragview/pipedream_results.html")


def get_pipedream_results(proj, pipedream_csv):
    with open(pipedream_csv, "w") as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow(
            ["sample", "summaryFile", "fragment", "fragmentLibrary", "symmetry", "resolution", "rwork", "rfree",
             "rhofitscore", "a", "b", "c", "alpha", "beta", "gamma", "ligsvg"])

        pipedreamXML = list()
        for shift_dir in project_shift_dirs(proj):
            xml_glob = f"{shift_dir}/fragmax/process/{proj.protein}/*/*/pipedream/summary.xml"
            pipedreamXML += glob(xml_glob)

        for summary in pipedreamXML:
            try:
                with open(summary, "r") as fd:
                    doc = xmltodict.parse(fd.read())

                sample = doc["GPhL-pipedream"]["setup"]["runfrom"].split("/")[-1]
                a = doc["GPhL-pipedream"]["refdata"]["cell"]["a"]
                b = doc["GPhL-pipedream"]["refdata"]["cell"]["b"]
                c = doc["GPhL-pipedream"]["refdata"]["cell"]["c"]
                alpha = doc["GPhL-pipedream"]["refdata"]["cell"]["alpha"]
                beta = doc["GPhL-pipedream"]["refdata"]["cell"]["beta"]
                gamma = doc["GPhL-pipedream"]["refdata"]["cell"]["gamma"]
                ligandID = doc["GPhL-pipedream"]["ligandfitting"]["ligand"]["@id"]
                symm = doc["GPhL-pipedream"]["refdata"]["symm"]
                rhofitscore = doc["GPhL-pipedream"]["ligandfitting"]["ligand"]["rhofitsolution"][
                    "correlationcoefficient"]
                R = doc["GPhL-pipedream"]["refinement"]["Cycle"][-1]["R"]
                Rfree = doc["GPhL-pipedream"]["refinement"]["Cycle"][-1]["Rfree"]
                resolution = doc["GPhL-pipedream"]["inputdata"]["table1"]["shellstats"][0]["reshigh"]
                ligsvg = \
                    f"{project_static_url(proj)}/fragmax/process/fragment/{proj.library}/{ligandID}/{ligandID}.svg"

                writer.writerow([
                    sample, summary.replace("/data/visitors/", "/static/").replace(".xml", ".out"), ligandID,
                    proj.library, symm, resolution, R, Rfree, rhofitscore, a, b, c, alpha, beta, gamma, ligsvg])

            except Exception:
                pass


def submit(request):
    def get_user_pdb_path():
        if len(b_userPDBcode.replace("b_userPDBcode:", "")) == 4:
            userPDB = b_userPDBcode.replace("b_userPDBcode:", "")
            userPDBpath = project_model_path(proj, f"{userPDB}.pdb")

            # Download and prepare PDB _file - remove waters and HETATM
            with open(userPDBpath, "w") as pdb:
                pdb.write(pypdb.get_pdb_file(userPDB, filetype='pdb'))

            preparePDB = \
                "pdb_selchain -" + pdbchains + " " + userPDBpath + " | pdb_delhetatm | pdb_tidy > " + \
                userPDBpath.replace(".pdb", "_tidy.pdb")
            subprocess.call(preparePDB, shell=True)
        else:
            if len(b_userPDBcode.split("b_userPDBcode:")) == 2:
                if proj.data_path() in b_userPDBcode.split("b_userPDBcode:")[1]:
                    userPDBpath = b_userPDBcode.split("b_userPDBcode:")[1]
                else:
                    userPDBpath = project_model_path(proj, b_userPDBcode.split("b_userPDBcode:")[1])

        return userPDBpath

    proj = current_project(request)
    ppdCMD = str(request.GET.get("ppdform"))
    empty, input_data, ap_spacegroup, ap_cellparam, ap_staraniso, ap_xbeamcent, ap_ybeamcent, ap_datarange, \
        ap_rescutoff, ap_highreslim, ap_maxrpim, ap_mincomplet, ap_cchalfcut, ap_isigicut, ap_custompar, \
        b_userPDBfile, b_userPDBcode, b_userMTZfile, b_refinemode, b_MRthreshold, b_chainsgroup, b_bruteforcetf, \
        b_reslimits, b_angularrf, b_sideaiderefit, b_sideaiderebuild, b_pepflip, b_custompar, rho_ligandsmiles, \
        rho_ligandcode, rho_ligandfromname, rho_copiestosearch, rho_keepH, rho_allclusters, rho_xclusters, \
        rho_postrefine, rho_occuprefine, rho_fittingproc, rho_scanchirals, rho_custompar, extras = ppdCMD.split(";;")

    nodes = 10
    # variables init
    ligand = "none"
    ppdoutdir = "none"
    ppd = "INITVALUE"

    pdbchains = "A"
    userPDBpath = ""
    # Select one dataset or entire project
    if "alldatasets" not in input_data:
        input_data = input_data.replace("input_data:", "")
        ppdoutdir = path.join(
            project_process_protein_dir(proj),
            input_data.split(proj.protein + "/")[-1].replace("_master.h5", ""),
            "pipedream")
        os.makedirs("/".join(ppdoutdir.split("/")[:-1]), mode=0o760, exist_ok=True)

        # we need to make sure that pipedream output directory does
        # not exist before invoking pipedream, as pipedream can potentionally
        # refuse to run if the directory already exists
        if path.exists(ppdoutdir):
            shutil.rmtree(ppdoutdir)

        userPDBpath = get_user_pdb_path()

        # STARANISO setting
        if "true" in ap_staraniso:
            useANISO = " -useaniso"
        else:
            useANISO = ""

        # BUSTER refinement mode
        if "thorough" in b_refinemode:
            refineMode = " -thorough"
        elif "quick" in b_refinemode:
            refineMode = " -quick"
        else:
            refineMode = " "

        # PDB_REDO options
        pdbREDO = ""
        if "true" in b_sideaiderefit:
            pdbREDO += " -remediate"
            refineMode = " -thorough"
        if "true" in b_sideaiderebuild:
            if "remediate" not in pdbREDO:
                pdbREDO += " -remediate"
            pdbREDO += " -sidechainrebuild"
        if "true" in b_pepflip:
            pdbREDO += " -runpepflip"

        # Rhofit ligand
        if "true" in rho_ligandfromname:
            ligand = input_data.split("/")[8].split("-")[-1]

        elif "false" in rho_ligandfromname:
            if len(rho_ligandcode) > 15:
                ligand = rho_ligandcode.replace("rho_ligandcode:", "")
            elif len(rho_ligandsmiles) > 17:
                ligand = rho_ligandsmiles.replace("rho_ligandsmiles:", "")

        rhofitINPUT = f" -rhofit {project_ligand_cif(proj, ligand)}"

        # Keep Hydrogen RhoFit
        keepH = ""
        if "true" in rho_keepH:
            keepH = " -keepH"

        # Cluster to search for ligands
        clusterSearch = ""
        ncluster = "1"
        if len(rho_allclusters) > 16:
            if "true" in rho_allclusters.split(":")[-1].lower():
                clusterSearch = " -allclusters"
            else:
                ncluster = rho_xclusters.split(":")[-1]
                if ncluster == "":
                    ncluster = 1
                clusterSearch = " -xcluster " + ncluster
        else:
            ncluster = rho_xclusters.split(":")[-1]
            if ncluster == "":
                ncluster = "1"
            clusterSearch = " -xcluster " + ncluster

        # Search mode for RhoFit
        if "thorough" in rho_fittingproc:
            fitrefineMode = " -rhothorough"
        elif "quick" in rho_fittingproc:
            fitrefineMode = " -rhoquick"
        else:
            fitrefineMode = " "
        # Post refine for RhoFit
        if "thorough" in rho_postrefine:
            postrefineMode = " -postthorough"
        elif "standard" in rho_postrefine:
            postrefineMode = " -postref"
        elif "quick" in rho_postrefine:
            postrefineMode = " -postquick"
        else:
            postrefineMode = " "

        scanChirals = ""
        if "false" in rho_scanchirals:
            scanChirals = " -nochirals"

        occRef = ""
        if "false" in rho_occuprefine:
            occRef = " -nooccref"

        singlePipedreamOut = ""
        singlePipedreamOut += """#!/bin/bash\n"""
        singlePipedreamOut += """#!/bin/bash\n"""
        singlePipedreamOut += """#SBATCH -t 99:55:00\n"""
        singlePipedreamOut += """#SBATCH -J pipedream\n"""
        singlePipedreamOut += """#SBATCH --exclusive\n"""
        singlePipedreamOut += """#SBATCH -N1\n"""
        singlePipedreamOut += """#SBATCH --cpus-per-task=48\n"""
        singlePipedreamOut += """#SBATCH --mem=220000\n"""
        singlePipedreamOut += \
            """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/pipedream_""" + ligand + """_%j_out.txt\n"""
        singlePipedreamOut += \
            """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/pipedream_""" + ligand + """_%j_err.txt\n"""
        singlePipedreamOut += """module purge\n"""
        singlePipedreamOut += """module load autoPROC BUSTER\n\n"""

        chdir = "cd " + "/".join(ppdoutdir.split("/")[:-1])
        ppd = \
            "pipedream -h5 " + input_data + " -d " + ppdoutdir + " -xyzin " + userPDBpath + rhofitINPUT + useANISO + \
            refineMode + pdbREDO + keepH + clusterSearch + fitrefineMode + postrefineMode + scanChirals + occRef + \
            " -nofreeref -nthreads -1 -v"

        singlePipedreamOut += chdir + "\n"
        singlePipedreamOut += ppd

        script = project_script(proj, f"pipedream_{ligand}.sh")
        with open(script, "w") as ppdsh:
            ppdsh.write(singlePipedreamOut)

        hpc.run_sbatch(script)

    if "alldatasets" in input_data:
        ppddatasetList = list(project_raw_master_h5_files(proj))

        ppdoutdirList = [
            f"{project_process_protein_dir(proj)}/" + x.split(proj.protein + "/")[-1].replace("_master.h5",
                                                                                              "") + "/pipedream"
            for x in ppddatasetList]

        userPDBpath = get_user_pdb_path()

        # STARANISO setting
        if "true" in ap_staraniso:
            useANISO = " -useaniso"
        else:
            useANISO = ""

        # BUSTER refinement mode
        if "thorough" in b_refinemode:
            refineMode = " -thorough"
        elif "quick" in b_refinemode:
            refineMode = " -quick"
        else:
            refineMode = " "

        # PDB_REDO options
        pdbREDO = ""
        if "true" in b_sideaiderefit:
            pdbREDO += " -remediate"
            refineMode = " -thorough"
        if "true" in b_sideaiderebuild:
            if "remediate" not in pdbREDO:
                pdbREDO += " -remediate"
            pdbREDO += " -sidechainrebuild"
        if "true" in b_pepflip:
            pdbREDO += " -runpepflip"

        # Keep Hydrogen RhoFit
        keepH = ""
        if "true" in rho_keepH:
            keepH = " -keepH"

        # Cluster to search for ligands
        clusterSearch = ""
        if len(rho_allclusters) > 16:
            if "true" in rho_allclusters.split(":")[-1].lower():
                clusterSearch = " -allclusters"
            else:
                ncluster = rho_xclusters.split(":")[-1]
                if ncluster == "":
                    ncluster = "1"
                clusterSearch = " -xcluster " + ncluster
        else:
            ncluster = rho_xclusters.split(":")[-1]
            if ncluster == "":
                ncluster = "1"
            clusterSearch = " -xcluster " + ncluster

        # Search mode for RhoFit
        if "thorough" in rho_fittingproc:
            fitrefineMode = " -rhothorough"
        elif "quick" in rho_fittingproc:
            fitrefineMode = " -rhoquick"
        else:
            fitrefineMode = " "
        # Post refine for RhoFit
        if "thorough" in rho_postrefine:
            postrefineMode = " -postthorough"
        elif "standard" in rho_postrefine:
            postrefineMode = " -postref"
        elif "quick" in rho_postrefine:
            postrefineMode = " -postquick"
        else:
            postrefineMode = " "

        scanChirals = ""
        if "false" in rho_scanchirals:
            scanChirals = " -nochirals"

        occRef = ""
        if "false" in rho_occuprefine:
            occRef = " -nooccref"

        header = ""
        header += """#!/bin/bash\n"""
        header += """#!/bin/bash\n"""
        header += """#SBATCH -t 99:55:00\n"""
        header += """#SBATCH -J pipedream\n"""
        header += """#SBATCH --exclusive\n"""
        header += """#SBATCH -N1\n"""
        header += """#SBATCH --cpus-per-task=40\n"""
        # header+= """#SBATCH --mem=220000\n"""
        header += """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/pipedream_allDatasets_%j_out.txt\n"""
        header += """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/pipedream_allDatasets_%j_err.txt\n"""
        header += """module purge\n"""
        header += """module load autoPROC BUSTER\n\n"""
        scriptList = list()

        for ppddata, ppdout in zip(ppddatasetList, ppdoutdirList):
            chdir = "cd " + "/".join(ppdout.split("/")[:-1])
            if "apo" not in ppddata.lower():
                ligand = ppddata.split("/")[8].split("-")[-1]
                rhofitINPUT = f" -rhofit {project_ligand_cif(proj, ligand)} {keepH}{clusterSearch}" \
                              f"{fitrefineMode}{postrefineMode}{scanChirals}{occRef}"
            if "apo" in ppddata.lower():
                rhofitINPUT = ""
            ppd = \
                "pipedream -h5 " + ppddata + " -d " + ppdout + " -xyzin " + userPDBpath + rhofitINPUT + useANISO + \
                refineMode + pdbREDO + " -nofreeref -nthreads -1 -v"

            allPipedreamOut = chdir + "\n"
            allPipedreamOut += chdir.replace("cd ", "rm -rf ") + "/pipedream/" + "\n"
            allPipedreamOut += ppd + "\n\n"

            scriptList.append(allPipedreamOut)
        chunkScripts = [header + "".join(x) for x in list(scrsplit(scriptList, nodes))]

        for num, chunk in enumerate(chunkScripts):
            time.sleep(0.2)
            script = project_script(proj, f"pipedream_part{num}.sh")
            with open(script, "w") as outfile:
                outfile.write(chunk)

            hpc.run_sbatch(script)

    return render(
        request,
        "fragview/jobs_submitted.html",
        {"command": "<br>".join(ppdCMD.split(";;"))})
