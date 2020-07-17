import os
import csv
import shutil
import natsort
import xmltodict
from os import path
from glob import glob
from django.shortcuts import render
from fragview import hpc
from fragview.projects import current_project, project_raw_master_h5_files, project_process_protein_dir
from fragview.projects import project_shift_dirs, project_static_url, project_model_path
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

    proj = current_project(request)
    ppdCMD = str(request.GET.get("ppdform"))
    empty, input_data, ap_spacegroup, ap_cellparam, ap_staraniso, ap_xbeamcent, ap_ybeamcent, ap_datarange, \
        ap_rescutoff, ap_highreslim, ap_maxrpim, ap_mincomplet, ap_cchalfcut, ap_isigicut, ap_custompar, \
        b_userPDBfile, b_userPDBcode, b_userMTZfile, b_refinemode, b_MRthreshold, b_chainsgroup, b_bruteforcetf, \
        b_reslimits, b_angularrf, b_sideaiderefit, b_sideaiderebuild, b_pepflip, b_custompar, rho_ligandsmiles, \
        rho_ligandcode, rho_ligandfromname, rho_copiestosearch, rho_keepH, rho_allclusters, rho_xclusters, \
        rho_postrefine, rho_occuprefine, rho_fittingproc, rho_scanchirals, rho_custompar, extras = ppdCMD.split(";;")

    nodes = 10
    PDBmodel = b_userPDBfile.replace("b_userPDBfile:", "").replace(".pdb", "")
    # Select one dataset or entire project

    if "ALL" not in input_data:
        input_data_list = input_data.replace("input_data:", "").split(",")

        def pipedream_single_dataset(_data):
            ppdoutdir = path.join(proj.data_path(), "fragmax", "results", _data, "pipedream")
            ppdprocessdir = path.join(project_process_protein_dir(proj), _data.split("_")[0], _data, "pipedream")

            os.makedirs(path.dirname(ppdoutdir), mode=0o775, exist_ok=True)
            os.makedirs(path.dirname(ppdprocessdir), mode=0o775, exist_ok=True)

            # we need to make sure that pipedream output directory does
            # not exist before invoking pipedream, as pipedream will
            # refuse to run if the directory already exists
            if path.exists(ppdoutdir):
                shutil.rmtree(ppdoutdir)

            userPDBpath = project_model_path(proj, f"{PDBmodel}.pdb")

            # STARANISO setting
            if "false" in ap_staraniso:
                useANISO = ""
            else:
                useANISO = " -useaniso"

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
            if "Apo" not in _data:
                ligand = _data.split("-")[-1].split("_")[0]
                lib = proj.library
                smiles = lib.get_fragment(ligand).smiles
                cif_out = f"{ppdprocessdir}/{ligand}"
                cif_cmd = f"mkdir -p {ppdprocessdir}\n" \
                          f"rm {cif_out}.cif {cif_out}.pdb\n" \
                          f"grade '{smiles}' -ocif {cif_out}.cif -opdb {cif_out}.pdb -nomogul\n"

                rhofitINPUT = f" -rhofit {cif_out}.cif"
            else:
                cif_cmd = ""
                ligand = ""
                rhofitINPUT = ""
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
            # singlePipedreamOut += """#SBATCH -p fujitsu\n"""
            singlePipedreamOut += """#SBATCH --cpus-per-task=48\n"""
            singlePipedreamOut += """#SBATCH --mem=220000\n"""
            singlePipedreamOut += \
                """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/pipedream_""" + ligand + """_%j_out.txt\n"""
            singlePipedreamOut += \
                """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/pipedream_""" + ligand + """_%j_err.txt\n"""
            singlePipedreamOut += """module purge\n"""
            singlePipedreamOut += """module load autoPROC BUSTER/20190607-3-PReSTO\n\n"""
            _data_path = [x for x in project_raw_master_h5_files(proj) if _data in x][0]
            chdir = f"mkdir -p {path.dirname(ppdoutdir)}; cd {path.dirname(ppdoutdir)}\n\n"
            ppd = \
                "pipedream -h5 " + _data_path + " -d " + ppdoutdir + " -xyzin " + \
                userPDBpath + rhofitINPUT + useANISO + refineMode + pdbREDO + keepH + clusterSearch + \
                fitrefineMode + postrefineMode + scanChirals + occRef + " -nofreeref -nthreads -1 -v"

            singlePipedreamOut += chdir + "\n"
            singlePipedreamOut += cif_cmd + "\n"
            singlePipedreamOut += """module purge\n"""
            singlePipedreamOut += """module load autoPROC BUSTER\n\n"""
            singlePipedreamOut += ppd

            script = project_script(proj, f"pipedream_{_data}.sh")
            with open(script, "w") as ppdsh:
                ppdsh.write(singlePipedreamOut)

            hpc.run_sbatch(script)

        for _input in input_data_list:
            pipedream_single_dataset(_input)

    if "ALL" in input_data:
        ppddatasetList = list(project_raw_master_h5_files(proj))
        ppddatasetList_s = [path.basename(x).replace("_master.h5", "") for x in ppddatasetList]
        ppdoutdirList = [path.join(proj.data_path(), "fragmax", "results", _data, "pipedream")
                         for _data in ppddatasetList_s]

        userPDBpath = project_model_path(proj, f"{PDBmodel}.pdb")

        # STARANISO setting
        if "false" in ap_staraniso:
            useANISO = ""
        else:
            useANISO = " -useaniso"

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
        header += """module load autoPROC BUSTER/20190607-3-PReSTO\n\n"""
        scriptList = list()

        for ppddata, ppdout in zip(ppddatasetList, ppdoutdirList):
            chdir = f"mkdir -p {path.dirname(ppdout)};\ncd {path.dirname(ppdout)}\n"
            _data = path.basename(ppddata).replace("_master.h5", "")
            ppdprocessdir = path.join(project_process_protein_dir(proj), _data.split("_")[0], _data, "pipedream")
            if path.exists(ppdout):
                rmdir = f"rm -rf {ppdout}"
            else:
                rmdir = ""
            if "apo" not in ppddata.lower():
                ligand = _data.split("-")[-1].split("_")[0]
                lib = proj.library
                smiles = lib.get_fragment(ligand).smiles
                cif_out = f"{ppdprocessdir}/{ligand}"
                cif_cmd = f"mkdir -p {ppdprocessdir}\n" \
                          f"rm {cif_out}.cif {cif_out}.pdb\n" \
                          f"grade '{smiles}' -ocif {cif_out}.cif -opdb {cif_out}.pdb -nomogul"

                rhofitINPUT = f" -rhofit {cif_out}.cif {keepH} {clusterSearch} " \
                              f"{fitrefineMode} {postrefineMode} {scanChirals} {occRef}"

            else:
                rhofitINPUT = ""
                cif_cmd = ""
            ppd = \
                "pipedream -h5 " + ppddata + " -d " + ppdout + " -xyzin " + userPDBpath + rhofitINPUT + useANISO + \
                refineMode + pdbREDO + " -nofreeref -nthreads -1 -v"

            allPipedreamOut = f"{chdir}"
            allPipedreamOut += "module purge\n"
            allPipedreamOut += "module load autoPROC BUSTER/20190607-3-PReSTO\n"
            allPipedreamOut += f"{cif_cmd}\n"
            allPipedreamOut += f"{rmdir}\n"
            allPipedreamOut += "module purge\n"
            allPipedreamOut += "module load autoPROC BUSTER\n"
            allPipedreamOut += ppd + "\n\n"

            scriptList.append(allPipedreamOut)
        chunkScripts = [header + "".join(x) for x in list(scrsplit(scriptList, nodes))]

        for num, chunk in enumerate(chunkScripts):
            script = project_script(proj, f"pipedream_part{num}.sh")
            with open(script, "w") as outfile:
                outfile.write(chunk)

            hpc.run_sbatch(script)

    return render(
        request,
        "fragview/jobs_submitted.html",
        {"command": "<br>".join(ppdCMD.split(";;"))})
