import os
import time
import xmltodict
import threading
import subprocess
from os import path
from django.shortcuts import render
from fragview.projects import current_project, project_script, project_xml_files
from fragview import hpc
from .utils import scrsplit

update_script = "/data/staff/biomax/webapp/static/scripts/update_status.py"


def datasets(request):
    proj = current_project(request)

    allprc = str(request.GET.get("submitallProc"))
    dtprc = str(request.GET.get("submitdtProc"))
    if allprc != "None":
        userinputs = allprc.split(";;")
        dpSW = list()
        dpSW.append("xdsapp") if ("true" in userinputs[3]) else False
        dpSW.append("xdsxscale") if ("true" in userinputs[2]) else False
        dpSW.append("dials") if ("true" in userinputs[1]) else False
        dpSW.append("autoproc") if ("true" in userinputs[4]) else False
        if dpSW == []:
            dpSW = [""]

        rfSW = list()
        rfSW.append("dimple") if ("true" in userinputs[12]) else False
        rfSW.append("fspipeline") if ("true" in userinputs[13]) else False
        rfSW.append("buster") if ("true" in userinputs[14]) else False
        if rfSW == []:
            rfSW = [""]

        lfSW = list()
        lfSW.append("rhofit") if ("true" in userinputs[19]) else False
        lfSW.append("ligfit") if ("true" in userinputs[20]) else False
        if lfSW == []:
            lfSW = [""]

        PDBID = userinputs[18].split(":")[-1]

        spg = userinputs[5].split(":")[-1]
        pnodes = 10
        shell_script = project_script(proj, "processALL.sh")
        with open(shell_script, "w") as outp:
            outp.write(
                """#!/bin/bash \n"""
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
                """python """ + project_script(proj, "processALL.py") + """ '""" + proj.data_path() + """' '""" +
                proj.library + """' '""" + PDBID + """' '""" + spg + """' $1 $2 '""" + ",".join(dpSW) +
                """' '""" + ",".join(rfSW) + """' '""" + ",".join(lfSW) + """' \n""")

        for node in range(pnodes):
            command = 'echo "module purge | module load CCP4 autoPROC DIALS XDSAPP | sbatch ' + \
                      shell_script + " " + str(node) + " " + str(pnodes) + ' " | ssh -F ~/.ssh/ clu0-fe-1'
            subprocess.call(command, shell=True)
            time.sleep(0.2)
        return render(request, 'fragview/testpage.html', {
            'dpSW': "<br>".join(dpSW),
            'rfSW': "<br>".join(rfSW),
            'lfSW': "<br>".join(lfSW),
            "pdb": PDBID,
            "sym": spg
        })

    if dtprc != "None":
        dtprc_inp = dtprc.split(";")
        usedials = dtprc_inp[1].split(":")[-1]
        usexdsxscale = dtprc_inp[2].split(":")[-1]
        usexdsapp = dtprc_inp[3].split(":")[-1]
        useautproc = dtprc_inp[4].split(":")[-1]
        filters = dtprc_inp[-1].split(":")[-1]

        nodes = 3
        if filters != "ALL":
            nodes = 1
        if usexdsapp == "true":
            t = threading.Thread(target=run_xdsapp, args=(proj, nodes, filters))
            t.daemon = True
            t.start()
        if usedials == "true":
            t = threading.Thread(target=run_dials, args=(proj, nodes, filters))
            t.daemon = True
            t.start()

        if useautproc == "true":
            t = threading.Thread(target=run_autoproc, args=(proj, nodes, filters))
            t.daemon = True
            t.start()

        if usexdsxscale == "true":
            t = threading.Thread(target=run_xdsxscale, args=(proj, nodes, filters))
            t.daemon = True
            t.start()

        return render(
            request,
            "fragview/dataproc_datasets.html",
            {"allproc": "Jobs submitted using " + str(nodes) + " per method"})

    return render(request, "fragview/dataproc_datasets.html", {"allproc": ""})


def run_xdsapp(proj, nodes, filters):
    if "filters:" in filters:
        filters = filters.split(":")[-1]

    if filters == "ALL":
        filters = ""

    header = """#!/bin/bash\n"""
    header += """#!/bin/bash\n"""
    header += """#SBATCH -t 99:55:00\n"""
    header += """#SBATCH -J XDSAPP\n"""
    header += """#SBATCH --exclusive\n"""
    header += """#SBATCH -N1\n"""
    header += """#SBATCH --cpus-per-task=40\n"""
    # header+= """#SBATCH --mem=220000\n"""
    header += """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/xdsapp_fragmax_%j_out.txt\n"""
    header += """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/xdsapp_fragmax_%j_err.txt\n"""
    header += """module purge\n\n"""
    header += """module load CCP4 XDSAPP\n\n"""

    scriptList = list()

    xml_files = sorted(x for x in project_xml_files(proj) if filters in x)

    for xml in xml_files:
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc = doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir = path.join(proj.data_path(), "fragmax", "process", proj.protein, dtc["imagePrefix"],
                           dtc["imagePrefix"] + "_" + dtc["dataCollectionNumber"])
        h5master = dtc["imageDirectory"] + "/" + dtc["fileTemplate"].replace("%06d.h5", "") + "master.h5"
        nImg = dtc["numberOfImages"]
        sample = outdir.split("/")[-1]
        script = \
            f"mkdir -p {outdir}/xdsapp\n" \
            f"cd {outdir}/xdsapp\n" \
            f"xdsapp --cmd --dir={outdir}/xdsapp -j 8 -c 5 -i {h5master} --delphi=10 " \
            f"--fried=True --range=1\\ {nImg}\n" + \
            f'''python {update_script} {sample} {proj.proposal}/{proj.shift}\n\n'''

        scriptList.append(script)
        os.makedirs(outdir, mode=0o760, exist_ok=True)
        os.makedirs(outdir + "/xdsapp", mode=0o760, exist_ok=True)

    chunkScripts = [header + "".join(x) for x in list(scrsplit(scriptList, nodes))]
    for num, chunk in enumerate(chunkScripts):
        time.sleep(0.2)

        script = project_script(proj, f"xdsapp_fragmax_part{num}.sh")
        with open(script, "w") as outfile:
            outfile.write(chunk)

        hpc.run_sbatch(script)


def run_autoproc(proj, nodes, filters):
    if "filters:" in filters:
        filters = filters.split(":")[-1]

    if filters == "ALL":
        filters = ""

    header = """#!/bin/bash\n"""
    header += """#!/bin/bash\n"""
    header += """#SBATCH -t 99:55:00\n"""
    header += """#SBATCH -J autoPROC\n"""
    header += """#SBATCH --exclusive\n"""
    header += """#SBATCH -N1\n"""
    header += """#SBATCH --cpus-per-task=40\n"""
    # header+= """#SBATCH --mem=220000\n"""
    header += """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/autoproc_fragmax_%j_out.txt\n"""
    header += """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/autoproc_fragmax_%j_err.txt\n"""
    header += """module purge\n\n"""
    header += """module load CCP4 autoPROC\n\n"""

    scriptList = list()

    xml_files = sorted(x for x in project_xml_files(proj) if filters in x)

    for xml in xml_files:
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc = doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir = path.join(proj.data_path(), "fragmax", "process", proj.protein, dtc["imagePrefix"],
                           dtc["imagePrefix"] + "_" + dtc["dataCollectionNumber"])
        h5master = dtc["imageDirectory"] + "/" + dtc["fileTemplate"].replace("%06d.h5", "") + "master.h5"
        nImg = dtc["numberOfImages"]
        os.makedirs(outdir, mode=0o760, exist_ok=True)
        sample = outdir.split("/")[-1]

        script = \
            f"mkdir -p {outdir}/\n" \
            f'''cd {outdir}\n''' + \
            f'''process -h5 {h5master} -noANO autoPROC_Img2Xds_UseXdsPlugins_DectrisHdf5="durin-plugin" ''' + \
            f'''autoPROC_XdsKeyword_LIB=\\$EBROOTNEGGIA/lib/dectris-neggia.so ''' + \
            f'''autoPROC_XdsKeyword_ROTATION_AXIS='0  -1 0' autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_JOBS=8 ''' + \
            f'''autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_PROCESSORS=5 autoPROC_XdsKeyword_DATA_RANGE=1\\ ''' + \
            f'''{nImg} autoPROC_XdsKeyword_SPOT_RANGE=1\\ {nImg} -d {outdir}/autoproc\n''' + \
            f'''python {update_script} {sample} {proj.proposal}/{proj.shift}\n\n'''

        scriptList.append(script)

    chunkScripts = [header + "".join(x) for x in list(scrsplit(scriptList, nodes))]

    for num, chunk in enumerate(chunkScripts):
        time.sleep(0.2)

        script = project_script(proj, f"autoproc_fragmax_part{num}.sh")
        with open(script, "w") as outfile:
            outfile.write(chunk)

        hpc.run_sbatch(script)


def run_xdsxscale(proj, nodes, filters):
    if "filters:" in filters:
        filters = filters.split(":")[-1]

    if filters == "ALL":
        filters = ""

    header = """#!/bin/bash\n"""
    header += """#!/bin/bash\n"""
    header += """#SBATCH -t 99:55:00\n"""
    header += """#SBATCH -J xdsxscale\n"""
    header += """#SBATCH --exclusive\n"""
    header += """#SBATCH -N1\n"""
    header += """#SBATCH --cpus-per-task=40\n"""
    # header+= """#SBATCH --mem=220000\n"""
    header += """#SBATCH --mem-per-cpu=2000\n"""
    header += """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/xdsxscale_fragmax_%j_out.txt\n"""
    header += """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/xdsxscale_fragmax_%j_err.txt\n"""
    header += """module purge\n\n"""
    header += """module load PReSTO\n\n"""

    scriptList = list()

    with open(project_script(proj, "filter.txt"), "w") as inp:
        inp.write(filters)

    xml_files = sorted(x for x in project_xml_files(proj) if filters in x)

    for xml in xml_files:
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc = doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir = path.join(proj.data_path(), "fragmax", "process", proj.protein, dtc["imagePrefix"],
                           dtc["imagePrefix"] + "_" + dtc["dataCollectionNumber"])
        h5master = dtc["imageDirectory"] + "/" + dtc["fileTemplate"].replace("%06d.h5", "") + "master.h5"
        nImg = dtc["numberOfImages"]
        os.makedirs(outdir, mode=0o760, exist_ok=True)
        os.makedirs(outdir + "/xdsxscale", mode=0o760, exist_ok=True)
        sample = outdir.split("/")[-1]

        script = \
            f"mkdir -p {outdir}/xdsxscale\n" \
            f"cd {outdir}/xdsxscale \n" \
            f"xia2 goniometer.axes=0,1,0  pipeline=3dii failover=true  nproc=40 image={h5master}:1:{nImg}" \
            f" multiprocessing.mode=serial multiprocessing.njob=1 multiprocessing.nproc=auto\n" + \
            f"python {update_script} {sample} {proj.proposal}/{proj.shift}\n\n"
        scriptList.append(script)

    chunkScripts = [header + "".join(x) for x in list(scrsplit(scriptList, nodes))]

    for num, chunk in enumerate(chunkScripts):
        time.sleep(0.2)

        script = project_script(proj, f"xdsxscale_fragmax_part{num}.sh")
        with open(script, "w") as outfile:
            outfile.write(chunk)

        hpc.run_sbatch(script)


def run_dials(proj, nodes, filters):
    if "filters:" in filters:
        filters = filters.split(":")[-1]

    if filters == "ALL":
        filters = ""

    header = """#!/bin/bash\n"""
    header += """#!/bin/bash\n"""
    header += """#SBATCH -t 99:55:00\n"""
    header += """#SBATCH -J DIALS\n"""
    header += """#SBATCH --exclusive\n"""
    header += """#SBATCH -N1\n"""
    header += """#SBATCH --cpus-per-task=48\n"""
    # header+= """#SBATCH --mem=220000\n"""
    # header += """#SBATCH --mem-per-cpu=2000\n"""

    header += """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/dials_fragmax_%j_out.txt\n"""
    header += """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/dials_fragmax_%j_err.txt\n"""
    header += """module purge\n\n"""
    header += """module load CCP4 XDS DIALS/1.14.10-2-PReSTO\n\n"""

    scriptList = list()

    xml_files = sorted(x for x in project_xml_files(proj) if filters in x)

    for xml in xml_files:
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc = doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir = path.join(proj.data_path(), "fragmax", "process", proj.protein, dtc["imagePrefix"],
                           dtc["imagePrefix"] + "_" + dtc["dataCollectionNumber"])
        h5master = dtc["imageDirectory"] + "/" + dtc["fileTemplate"].replace("%06d.h5", "") + "master.h5"
        nImg = dtc["numberOfImages"]
        os.makedirs(outdir, mode=0o760, exist_ok=True)
        os.makedirs(outdir + "/dials", mode=0o760, exist_ok=True)
        sample = outdir.split("/")[-1]

        script = \
            f"mkdir -p {outdir}/dials\n" \
            f"cd {outdir}/dials \n" \
            f"xia2 goniometer.axes=0,1,0  pipeline=dials failover=true nproc=48 image={h5master}:1:{nImg}" \
            f" multiprocessing.mode=serial multiprocessing.njob=1 multiprocessing.nproc=auto\n" + \
            f'''python {update_script} {sample} {proj.proposal}/{proj.shift}\n\n'''
        scriptList.append(script)

    chunkScripts = [header + "".join(x) for x in list(scrsplit(scriptList, nodes))]

    for num, chunk in enumerate(chunkScripts):
        time.sleep(0.2)

        script = project_script(proj, f"dials_fragmax_part{num}.sh")
        with open(script, "w") as outfile:
            outfile.write(chunk)

        hpc.run_sbatch(script)
