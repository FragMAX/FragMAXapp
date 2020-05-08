import os
import time
import xmltodict
import threading
import subprocess
from os import path
from django.shortcuts import render
from fragview.projects import current_project, project_script, project_xml_files, project_update_status_script_cmds
from fragview import hpc, versions
from .utils import scrsplit, Filter


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
                                                                                              """python """ + project_script(
                    proj, "processALL.py") + """ '""" + proj.data_path() + """' '""" +
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
        dtprc_inp = dtprc.split(";;")
        usedials = dtprc_inp[1].split(":")[-1]
        usexdsxscale = dtprc_inp[2].split(":")[-1]
        usexdsapp = dtprc_inp[3].split(":")[-1]
        useautproc = dtprc_inp[4].split(":")[-1]
        spacegroup = dtprc_inp[5].split(":")[-1]
        cellparam = dtprc_inp[6].split(":")[-1].replace("(", "").replace(")", "")
        filters = dtprc_inp[-1].split(":")[-1]
        options = {"spacegroup": spacegroup,
                   "cellparam": cellparam}
        nodes = 3
        if filters != "ALL":
            nodes = 1
        if usexdsapp == "true":
            t = threading.Thread(target=run_xdsapp, args=(proj, nodes, filters, options))
            t.daemon = True
            t.start()
        if usedials == "true":
            t = threading.Thread(target=run_dials, args=(proj, nodes, filters, options))
            t.daemon = True
            t.start()

        if useautproc == "true":
            t = threading.Thread(target=run_autoproc, args=(proj, nodes, filters, options))
            t.daemon = True
            t.start()

        if usexdsxscale == "true":
            t = threading.Thread(target=run_xdsxscale, args=(proj, nodes, filters, options))
            t.daemon = True
            t.start()

        return render(
            request,
            "fragview/dataproc_datasets.html",
            {"allproc": "Jobs submitted using " + str(nodes) + " per method"})

    return render(request, "fragview/dataproc_datasets.html", {"allproc": ""})


def run_xdsapp(proj, nodes, filters, options):
    # XDSAPP cmd options
    # -h, --help
    # show this help message and exit
    # --cmd
    # start the command line version of XDSAPP
    # --suffix=SUFFIX
    # give the suffix of your images, e.g. --suffix ".cbf" (just for multi mode)
    # -i IMAGE, --image=IMAGE
    # single mode: give one image of a dataset, this dataset will be processed, e.g. -i abcd_01_010.img
    # --xdsinp
    # genereate XDS.INP for this dataset, only in single mode
    # --index
    # index dataset, only in single mode
    # --range=RANGE
    # give datarange in format --range "start end"
    # --spotrange=SPOT_RANGE
    # give spotrange manually, can be 1-3 pairs, e.g. --spotrange "1 10 20 40 60 80"
    # --org=ORGXY
    # give orgx, orgy manually: --org "orgx orgy"
    # -f FRIEDEL, --fried=FRIEDEL
    # set friedel law, give "true" or "false", default: false
    # -s SG, --spacegroup=SG
    # give spacegroup and unit cell constants in format -s "sg a b c α β γ"
    # --dir=RESULT_DIR
    # give resultdir, e.g. --dir myresults, default: xdsit/surname
    # -r REINT, --reint=REINT
    # no of reintegration cycles, default: 2
    # --live=LIVE_NO
    # live processing, give last image no., e.g. --live 200
    # --ccstar=CCSTAR
    # do resolution cutoff based on ccstar
    # -a, --all
    # multi-mode: process all datasets in a dir (recursively)
    # --cont=ALLAROUND
    # multi-mode: look continuously for datasets and process them
    # -j JOBS_NO, --jobs=JOBS_NO
    # set number of parallel jobs for xds, default: 1
    # -c CPU_NO, --cpu=CPU_NO
    # set number of cpus for xds, default: all cpus of the machine
    # --nice=NICE_LEVEL
    # set nice level of xds, default: 19
    # --res=RESOLUTION
    # use data up to resolution
    # --delphi=DELPHI
    # give delphi manually
    # --norestest
    # do resolution test

    # Modules list for HPC env
    softwares = "CCP4 XDSAPP"
    if "filters:" in filters:
        filters = filters.split(":")[-1]

    if filters == "ALL":
        filters = ""
    epoch = str(round(time.time()))
    header = """#!/bin/bash\n"""
    header += """#!/bin/bash\n"""
    header += """#SBATCH -t 99:55:00\n"""
    header += """#SBATCH -J XDSAPP\n"""
    header += """#SBATCH --exclusive\n"""
    header += """#SBATCH -N1\n"""
    header += """#SBATCH --cpus-per-task=40\n"""
    # header+= """#SBATCH --mem=220000\n"""
    header += """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/multi_xdsapp_""" + epoch + """_%j_out.txt\n"""
    header += """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/multi_xdsapp_""" + epoch + """_%j_err.txt\n"""
    header += """module purge\n\n"""
    header += f"""module load {softwares}\n\n"""
    scriptList = list()

    # xml_files = sorted(x for x in project_xml_files(proj) if filters in x)
    xml_files = sorted(Filter(project_xml_files(proj), filters.split(",")))

    for xml in xml_files:
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc = doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir = path.join(proj.data_path(), "fragmax", "process", proj.protein, dtc["imagePrefix"],
                           dtc["imagePrefix"] + "_" + dtc["dataCollectionNumber"])
        h5master = dtc["imageDirectory"] + "/" + dtc["fileTemplate"].replace("%06d.h5", "") + "master.h5"
        nImg = dtc["numberOfImages"]
        sample = outdir.split("/")[-1]
        if options["spacegroup"] != "":
            cellpar = " ".join(options["cellparam"].split(","))
            spacegroup = options["spacegroup"]
            spg = f"--spacegroup='{spacegroup} {cellpar}'"
        else:
            spg = ""
        script = \
            f"mkdir -p {outdir}/xdsapp\n" \
            f"cd {outdir}/xdsapp\n" \
            f"xdsapp --cmd --dir={outdir}/xdsapp -j 8 -c 5 -i {h5master} {spg} --delphi=10 " \
            f"--fried=True --range=1\\ {nImg}\n" + \
            project_update_status_script_cmds(proj, sample, softwares)

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


def run_autoproc(proj, nodes, filters, options):
    # Modules list for HPC env
    softwares = "CCP4 autoPROC Durin"

    if "filters:" in filters:
        filters = filters.split(":")[-1]

    if filters == "ALL":
        filters = ""
    epoch = str(round(time.time()))
    header = """#!/bin/bash\n"""
    header += """#!/bin/bash\n"""
    header += """#SBATCH -t 99:55:00\n"""
    header += """#SBATCH -J autoPROC\n"""
    header += """#SBATCH --exclusive\n"""
    header += """#SBATCH -N1\n"""
    header += """#SBATCH --cpus-per-task=48\n"""
    # header+= """#SBATCH --mem=220000\n"""
    header += """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/multi_autoproc_""" + epoch +"""_%j_out.txt\n"""
    header += """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/multi_autoproc_""" + epoch +"""_%j_err.txt\n"""
    header += """module purge\n\n"""
    header += f"""module load {softwares}\n\n"""

    scriptList = list()

    # xml_files = sorted(x for x in project_xml_files(proj) if filters in x)
    xml_files = sorted(Filter(project_xml_files(proj), filters.split(",")))

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

        if options["spacegroup"] != "":
            spacegroup = options["spacegroup"]
            spg = f"symm = '{spacegroup}'"
        else:
            spg = ""
        if options["cellparam"] != "":
            cellpar = " ".join(options["cellparam"].split(","))
            unit_cell = f"cell='{cellpar}'"
        else:
            unit_cell = ""
        script = \
            f"mkdir -p {outdir}/\n" \
            f'''cd {outdir}\n''' + \
            f'''process -h5 {h5master} -noANO autoPROC_Img2Xds_UseXdsPlugins_DectrisHdf5="durin-plugin" ''' + \
            f'''autoPROC_XdsKeyword_LIB=\\$EBROOTDURIN/lib/durin-plugin.so ''' + \
            f'''autoPROC_XdsKeyword_ROTATION_AXIS='0  -1 0' autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_JOBS=8 ''' + \
            f'''autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_PROCESSORS=5 autoPROC_XdsKeyword_DATA_RANGE=1\\ ''' + \
            f'''{nImg} autoPROC_XdsKeyword_SPOT_RANGE=1\\ {nImg} {spg} {unit_cell} -d {outdir}/autoproc\n''' + \
            project_update_status_script_cmds(proj, sample, softwares)

        scriptList.append(script)

    chunkScripts = [header + "".join(x) for x in list(scrsplit(scriptList, nodes))]

    for num, chunk in enumerate(chunkScripts):
        time.sleep(0.2)

        script = project_script(proj, f"autoproc_fragmax_part{num}.sh")
        with open(script, "w") as outfile:
            outfile.write(chunk)

        hpc.run_sbatch(script)


def run_xdsxscale(proj, nodes, filters, options):
    # atom=X
    # Tell xia2 to separate anomalous pairs i.e. I(+) ≠ I(−) in scaling.
    # pipeline=3d
    # Tell xia2 to use XDS and XSCALE.
    # pipeline=3dii
    # Tell xia2 to use XDS and XSCALE, indexing with peaks found from all images.
    # pipeline=dials
    # Tell xia2 to use DIALS.
    # pipeline=dials-aimless
    # Tell xia2 to use DIALS but scale with Aimless.
    # xinfo=some.xinfo
    # Use specific modified .xinfo input file.
    # image=/path/to/an/image.img
    # Process a specific scan.
    # Pass multiple image= parameters to include multiple scans.
    # image=/path/to/an/image.img:start:end
    # Process a specific image range within a scan. start and end are numbers denoting the image range, e.g.
    # image=/path/to/an/image.img:1:100 processes images 1–100 inclusive.
    # As above, one can pass multiple image= parameters.
    # small_molecule=true
    # Process in manner more suited to small molecule data.
    # space_group=sg
    # Set the spacegroup, e.g. P21.
    # unit_cell=a,b,c,α,β,γ
    # Set the cell constants.

    # Modules list for HPC env
    softwares = "PReSTO DIALS/2.1.1-1-PReSTO"
    if "filters:" in filters:
        filters = filters.split(":")[-1]

    if filters == "ALL":
        filters = ""
    epoch = str(round(time.time()))
    header = """#!/bin/bash\n"""
    header += """#!/bin/bash\n"""
    header += """#SBATCH -t 99:55:00\n"""
    header += """#SBATCH -J xdsxscale\n"""
    header += """#SBATCH --exclusive\n"""
    header += """#SBATCH -N1\n"""
    header += """#SBATCH --cpus-per-task=48\n"""
    # header+= """#SBATCH --mem=220000\n"""
    # header += """#SBATCH --mem-per-cpu=2000\n"""
    header += """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/multi_xia2XDS_""" + epoch + """_%j_out.txt\n"""
    header += """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/multi_xia2XDS_""" + epoch + """_%j_err.txt\n"""
    header += """module purge\n\n"""
    header += f"""module load {softwares}\n\n"""

    scriptList = list()

    # xml_files = sorted(x for x in project_xml_files(proj) if filters in x)
    xml_files = sorted(Filter(project_xml_files(proj), filters.split(",")))

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

        if options["spacegroup"] != "":
            spacegroup = options["spacegroup"]
            spg = f"space_group={spacegroup}"
        else:
            spg = ""
        if options["cellparam"] != "":
            cellpar = ",".join(options["cellparam"].split(","))
            unit_cell = f"unit_cell={cellpar}"
        else:
            unit_cell = ""
        script = \
            f"mkdir -p {outdir}/xdsxscale\n" \
            f"cd {outdir}/xdsxscale \n" \
            f"xia2 goniometer.axes=0,1,0  pipeline=3dii failover=true {spg} {unit_cell} nproc=40 image={h5master}:1:{nImg}" \
            f" multiprocessing.mode=serial multiprocessing.njob=1 multiprocessing.nproc=auto\n" + \
            project_update_status_script_cmds(proj, sample, softwares)
        scriptList.append(script)

    chunkScripts = [header + "".join(x) for x in list(scrsplit(scriptList, nodes))]

    for num, chunk in enumerate(chunkScripts):
        time.sleep(0.2)

        script = project_script(proj, f"xdsxscale_fragmax_part{num}.sh")
        with open(script, "w") as outfile:
            outfile.write(chunk)

        hpc.run_sbatch(script)


def run_dials(proj, nodes, filters, options):
    # atom=X
    # Tell xia2 to separate anomalous pairs i.e. I(+) ≠ I(−) in scaling.
    # pipeline=3d
    # Tell xia2 to use XDS and XSCALE.
    # pipeline=3dii
    # Tell xia2 to use XDS and XSCALE, indexing with peaks found from all images.
    # pipeline=dials
    # Tell xia2 to use DIALS.
    # pipeline=dials-aimless
    # Tell xia2 to use DIALS but scale with Aimless.
    # xinfo=some.xinfo
    # Use specific modified .xinfo input file.
    # image=/path/to/an/image.img
    # Process a specific scan.
    # Pass multiple image= parameters to include multiple scans.
    # image=/path/to/an/image.img:start:end
    # Process a specific image range within a scan. start and end are numbers denoting the image range, e.g.
    # image=/path/to/an/image.img:1:100 processes images 1–100 inclusive.
    # As above, one can pass multiple image= parameters.
    # small_molecule=true
    # Process in manner more suited to small molecule data.
    # space_group=sg
    # Set the spacegroup, e.g. P21.
    # unit_cell=a,b,c,α,β,γ
    # Set the cell constants.

    # Modules list for HPC env
    softwares = f"PReSTO {versions.DIALS_MOD}"
    if "filters:" in filters:
        filters = filters.split(":")[-1]

    if filters == "ALL":
        filters = ""

    epoch = str(round(time.time()))
    header = """#!/bin/bash\n"""
    header += """#!/bin/bash\n"""
    header += """#SBATCH -t 99:55:00\n"""
    header += """#SBATCH -J DIALS\n"""
    header += """#SBATCH --exclusive\n"""
    header += """#SBATCH -N1\n"""
    header += """#SBATCH --cpus-per-task=48\n"""
    # it seems we need around ~210G of RAM to process some datasets,
    # when we do a 48-way parallelization
    header += """#SBATCH --mem=210G\n"""
    header += """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/multi_xia2DIALS_""" + epoch + """_%j_out.txt\n"""
    header += """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/multi_xia2DIALS_""" + epoch + """_%j_err.txt\n"""
    header += """module purge\n\n"""
    header += f"""module load {softwares}\n\n"""

    scriptList = list()

    # xml_files = sorted(x for x in project_xml_files(proj) if filters in x)
    xml_files = sorted(Filter(project_xml_files(proj), filters.split(",")))

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
        if options["spacegroup"] != "":
            spacegroup = options["spacegroup"]
            spg = f"space_group={spacegroup}"
        else:
            spg = ""
        if options["cellparam"] != "":
            cellpar = ",".join(options["cellparam"].split(","))
            unit_cell = f"unit_cell={cellpar}"
        else:
            unit_cell = ""
        script = \
            f"mkdir -p {outdir}/dials\n" \
            f"cd {outdir}/dials \n" \
            f"xia2 goniometer.axes=0,1,0  pipeline=dials failover=true {spg} {unit_cell} nproc=48 image={h5master}:1:{nImg}" \
            f" multiprocessing.mode=serial multiprocessing.njob=1 multiprocessing.nproc=auto\n" + \
            project_update_status_script_cmds(proj, sample, softwares)
        scriptList.append(script)

    chunkScripts = [header + "".join(x) for x in list(scrsplit(scriptList, nodes))]

    for num, chunk in enumerate(chunkScripts):
        time.sleep(0.2)

        script = project_script(proj, f"dials_fragmax_part{num}.sh")
        with open(script, "w") as outfile:
            outfile.write(chunk)

        hpc.run_sbatch(script)
