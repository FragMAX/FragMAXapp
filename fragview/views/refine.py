import os
import time
import pyfastcopy  # noqa
import threading
from glob import glob
from django.shortcuts import render
from fragview import hpc
from fragview.projects import current_project, project_script, project_update_status_script_cmds
from fragview.models import PDB
from .utils import Filter


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

    db_id = userPDB.replace("pdbmodel:", "")
    pdbmodel = PDB.get(db_id)

    spacegroup = refspacegroup.replace("refspacegroup:", "")
    t1 = threading.Thread(target=run_structure_solving,
                          args=(proj, useDIMPLE, useFSP, useBUSTER, pdbmodel.file_path(),
                                spacegroup, filters, customrefdimple, customrefbuster, customreffspipe, aimlessopt))
    t1.daemon = True
    t1.start()
    outinfo = "<br>".join(userInput.split(";;"))

    return render(
        request,
        "fragview/jobs_submitted.html",
        {"command": outinfo})


def run_structure_solving(proj, useDIMPLE, useFSP, useBUSTER, userPDB, spacegroup, filters, customrefdimple,
                          customrefbuster, customreffspipe, aimlessopt):
    # Modules list for HPC env
    softwares = "PReSTO autoPROC BUSTER"
    customreffspipe = customreffspipe.split("customrefinefspipe:")[-1]
    customrefbuster = customrefbuster.split("customrefinebuster:")[-1]
    customrefdimple = customrefdimple.split("customrefinedimple:")[-1]
    aimlessopt = aimlessopt.split("aimlessopt:")[-1]
    argsfit = "none"

    filters = filters.split(":")[-1]
    if filters == "ALL":
        filters = ""
    if filters == "NEW":
        refinedDatasets = glob(f"{proj.data_path()}/fragmax/results/{proj.protein}*/*/dimple") + \
                          glob(f"{proj.data_path()}/fragmax/results/{proj.protein}*/*/fspipeline") + \
                          glob(f"{proj.data_path()}/fragmax/results/{proj.protein}*/*/buster")
        processedDatasets = set(["/".join(x.split("/")[:-2]) for x in refinedDatasets])
        allDatasets = [x.split("/")[-2] for x in
                       sorted(glob(f"{proj.data_path()}/fragmax/process/{proj.protein}/{proj.protein}*/*/"))]
        filters = ",".join(list(set(allDatasets) - set(processedDatasets)))
    if userPDB != "":
        if useFSP:
            argsfit += "fspipeline"
        if useDIMPLE:
            argsfit += "dimple"
        if useBUSTER:
            argsfit += "buster"

        datasetList = glob(f"{proj.data_path()}/fragmax/process/{proj.protein}/*/*/")
        datasetList = sorted(Filter(datasetList, filters.split(",")))
        epoch = str(round(time.time()))

        proc2resOut = ""
        proc2resOut += """#!/bin/bash\n"""
        proc2resOut += """#!/bin/bash\n"""
        proc2resOut += """#SBATCH -t 12:00:00\n"""
        proc2resOut += """#SBATCH -J Refine_FragMAX\n"""
        proc2resOut += """#SBATCH -N1\n"""
        proc2resOut += """#SBATCH --cpus-per-task=2\n"""
        proc2resOut += """#SBATCH --mem-per-cpu=5000\n"""

        aimless = bool(aimlessopt)
        for dataset in datasetList:
            sample = dataset.split("/")[-2]
            script = project_script(proj, f"proc2res_{sample}.sh")

            epoch = str(round(time.time()))
            slctd_sw = argsfit.replace("none", "")
            p2rOut = ""
            p2rOut += """#SBATCH -o """ + proj.data_path() + f"/fragmax/logs/{sample}_{slctd_sw}_{epoch}_%j_out.txt\n"
            p2rOut += """#SBATCH -e """ + proj.data_path() + f"/fragmax/logs/{sample}_{slctd_sw}_{epoch}_%j_err.txt\n"
            p2rOut += """module purge\n"""
            p2rOut += f"""module load {softwares}\n\n"""
            p2rOut += '''echo export TMPDIR=''' + proj.data_path() + '''/fragmax/logs/\n\n'''
            with open(script, "w") as outp:
                outp.write(proc2resOut)
                outp.write(p2rOut)
                edna = find_edna(proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster,
                                 customrefdimple)
                fastdp = find_fastdp(proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe,
                                     customrefbuster, customrefdimple)
                xdsapp = find_xdsapp(proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe,
                                     customrefbuster, customrefdimple)
                xdsxscale = find_xdsxscale(proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe,
                                           customrefbuster, customrefdimple)
                dials = find_dials(proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe,
                                   customrefbuster, customrefdimple)
                autoproc = find_autoproc(proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe,
                                         customrefbuster, customrefdimple)

                outp.write(edna)
                outp.write("\n\n")
                outp.write(fastdp)
                outp.write("\n\n")
                outp.write(xdsapp)
                outp.write("\n\n")
                outp.write(xdsxscale)
                outp.write("\n\n")
                outp.write(dials)
                outp.write("\n\n")
                outp.write(autoproc)
                outp.write("\n\n")
                outp.write(project_update_status_script_cmds(proj, sample, softwares))
                outp.write("\n\n")

            hpc.run_sbatch(script)
            # os.remove(script)
    else:
        userPDB = "-"


def aimless_cmd(spacegroup, dstmtz):
    outdir = '/'.join(dstmtz.split('/')[:-1])
    cmd = f"echo 'choose spacegroup {spacegroup}' | pointless HKLIN {dstmtz} HKLOUT {dstmtz} | tee " \
        f"{outdir}/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN " \
        f"{dstmtz} HKLOUT {dstmtz} | tee {outdir}/aimless.log"
    return cmd


def find_autoproc(proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster,
                  customrefdimple):
    srcmtz = None
    dstmtz = None
    aimless_c = ""
    autoproc_cmd = ""
    refine_cmd = ""
    out_cmd = ""
    if glob(dataset + "autoproc/*mtz") != []:
        try:
            srcmtz = [x for x in glob(dataset + "autoproc/*mtz") if "staraniso" in x][0]
        except IndexError:
            try:
                srcmtz = [x for x in glob(dataset + "autoproc/*mtz") if "aimless" in x][0]
            except IndexError:
                srcmtz = [x for x in glob(dataset + "autoproc/*mtz")][0]
    dstmtz = proj.data_path() + "/fragmax/results/" + dataset.split("/")[-2] + "/autoproc/" + dataset.split("/")[
        -2] + "_autoproc_merged.mtz"
    if srcmtz:
        outdir = "/".join(dstmtz.split("/")[:-1])
        cdtooutdir = "cd " + outdir
        cmd = aimless_cmd(spacegroup, dstmtz)
        mkdir = f'mkdir -p {outdir}'
        copy = f'cp {srcmtz} {dstmtz}'
        if aimless:
            aimless_c = f'{cmd}'
        autoproc_cmd = mkdir + "\n" + cdtooutdir + "\n" + copy + "\n" + aimless_c + "\n"
        refine_cmd = set_refine(argsfit, dataset, userPDB, customrefbuster, customreffspipe, customrefdimple, srcmtz,
                                dstmtz)
        out_cmd = autoproc_cmd + "\n" + refine_cmd
    return out_cmd


def find_dials(proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple):
    srcmtz = None
    dstmtz = None
    aimless_c = ""
    dials_cmd = ""
    refine_cmd = ""
    out_cmd = ""
    srcmtz = dataset + "dials/DEFAULT/scale/AUTOMATIC_DEFAULT_scaled.mtz"
    dstmtz = dataset.split("process/")[0] + "results/" + dataset.split("/")[-2] + "/dials/" + dataset.split("/")[
        -2] + "_dials_merged.mtz"
    if os.path.exists(srcmtz):
        outdir = "/".join(dstmtz.split("/")[:-1])
        cdtooutdir = "cd " + outdir
        cmd = aimless_cmd(spacegroup, dstmtz)
        mkdir = f'mkdir -p {outdir}'
        copy = f'cp {srcmtz} {dstmtz}'
        if aimless:
            aimless_c = f'{cmd}'
        dials_cmd = mkdir + "\n" + cdtooutdir + "\n" + copy + "\n" + aimless_c + "\n"
        refine_cmd = set_refine(argsfit, dataset, userPDB, customrefbuster, customreffspipe, customrefdimple, srcmtz,
                                dstmtz)
        out_cmd = dials_cmd + "\n" + refine_cmd
    return out_cmd


def find_xdsxscale(proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster,
                   customrefdimple):
    srcmtz = None
    dstmtz = None
    aimless_c = ""
    xdsxscale_cmd = ""
    refine_cmd = ""
    out_cmd = ""
    srcmtz = dataset + "xdsxscale/DEFAULT/scale/AUTOMATIC_DEFAULT_scaled.mtz"
    dstmtz = dataset.split("process/")[0] + "results/" + dataset.split("/")[-2] + "/xdsxscale/" + dataset.split("/")[
        -2] + "_xdsxscale_merged.mtz"
    if os.path.exists(srcmtz):
        outdir = "/".join(dstmtz.split("/")[:-1])
        cdtooutdir = "cd " + outdir
        cmd = aimless_cmd(spacegroup, dstmtz)
        mkdir = f'mkdir -p {outdir}'
        copy = f'cp {srcmtz} {dstmtz}'
        if aimless:
            aimless_c = f'{cmd}'
        xdsxscale_cmd = mkdir + "\n" + cdtooutdir + "\n" + copy + "\n" + aimless_c + "\n"
        refine_cmd = set_refine(argsfit, dataset, userPDB, customrefbuster, customreffspipe, customrefdimple, srcmtz,
                                dstmtz)
        out_cmd = xdsxscale_cmd + "\n" + refine_cmd
    return out_cmd


def find_xdsapp(proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster,
                customrefdimple):
    srcmtz = False
    dstmtz = None
    aimless_c = ""
    xdsapp_cmd = ""
    refine_cmd = ""
    out_cmd = ""
    mtzoutList = glob(dataset + "xdsapp/*F.mtz")
    if mtzoutList != []:
        srcmtz = mtzoutList[0]
        dstmtz = dataset.split("process/")[0] + "results/" + dataset.split("/")[-2] + "/xdsapp/" + dataset.split("/")[
            -2] + "_xdsapp_merged.mtz"
    if srcmtz:
        outdir = "/".join(dstmtz.split("/")[:-1])
        cdtooutdir = "cd " + outdir
        cmd = aimless_cmd(spacegroup, dstmtz)
        mkdir = f'mkdir -p {outdir}'
        copy = f'cp {srcmtz} {dstmtz}'
        if aimless:
            aimless_c = f'{cmd}'
        xdsapp_cmd = mkdir + "\n" + cdtooutdir + "\n" + copy + "\n" + aimless_c + "\n"
        refine_cmd = set_refine(argsfit, dataset, userPDB, customrefbuster, customreffspipe, customrefdimple, srcmtz,
                                dstmtz)
        out_cmd = xdsapp_cmd + "\n" + refine_cmd
    return out_cmd


def find_edna(proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple):
    srcmtz = False
    dstmtz = None
    aimless_c = ""
    edna_cmd = ""
    refine_cmd = ""
    out_cmd = ""
    mtzoutList = glob(proj.data_path() + "/fragmax/process/" + proj.protein + "/" + dataset.split("/")[
        -3] + "/*/edna/*_noanom_aimless.mtz")
    if mtzoutList != []:
        srcmtz = mtzoutList[0]
        dstmtz = dataset.split("process/")[0] + "results/" + dataset.split("/")[-2] + "/edna/" + dataset.split("/")[
            -2] + "_EDNA_merged.mtz"
    if srcmtz:
        outdir = "/".join(dstmtz.split("/")[:-1])
        cdtooutdir = "cd " + outdir
        cmd = aimless_cmd(spacegroup, dstmtz)
        mkdir = f'mkdir -p {outdir}'
        copy = f'cp {srcmtz} {dstmtz}'
        if aimless:
            aimless_c = f'{cmd}'
        edna_cmd = mkdir + "\n" + cdtooutdir + "\n" + copy + "\n" + aimless_c + "\n"
        refine_cmd = set_refine(argsfit, dataset, userPDB, customrefbuster, customreffspipe, customrefdimple, srcmtz,
                                dstmtz)
        out_cmd = edna_cmd + "\n" + refine_cmd
    return out_cmd


def find_fastdp(proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster,
                customrefdimple):
    srcmtz = False
    dstmtz = None
    aimless_c = ""
    fastdp_cmd = ""
    refine_cmd = ""
    out_cmd = ""
    mtzoutList = glob(
        proj.data_path() + "/fragmax/process/" + proj.protein + "/" + dataset.split("/")[-3] + "/*/fastdp/*.mtz")
    if mtzoutList != []:
        srcmtz = mtzoutList[0]
        dstmtz = dataset.split("process/")[0] + "results/" + dataset.split("/")[-2] + "/fastdp/" + dataset.split("/")[
            -2] + "_fastdp_merged.mtz"
    if srcmtz:
        outdir = "/".join(dstmtz.split("/")[:-1])
        cdtooutdir = "cd " + outdir
        cmd = aimless_cmd(spacegroup, dstmtz)
        mkdir = f'mkdir -p {outdir}'
        copy = f'cp {srcmtz} {dstmtz}'
        if aimless:
            aimless_c = f'{cmd}'
        fastdp_cmd = mkdir + "\n" + cdtooutdir + "\n" + copy + "\n" + aimless_c + "\n"
        refine_cmd = set_refine(argsfit, dataset, userPDB, customrefbuster, customreffspipe, customrefdimple, srcmtz,
                                dstmtz)
        out_cmd = fastdp_cmd + "\n" + refine_cmd
    return out_cmd


def set_refine(argsfit, dataset, userPDB, customrefbuster, customreffspipe, customrefdimple, srcmtz, dstmtz):
    dimple_cmd = ""
    buster_cmd = ""
    fsp_cmd = ""
    srcmtz = dstmtz
    outdir = "/".join(dstmtz.split("/")[:-1])
    fsp = '''python /data/staff/biomax/guslim/FragMAX_dev/fm_bessy/fspipeline.py --sa=false --refine=''' + userPDB + \
          ''' --exclude="dimple fspipeline buster unmerged rhofit ligfit truncate" --cpu=2 ''' + customreffspipe

    if "dimple" in argsfit:
        dimple_cmd += f"dimple {dstmtz} {userPDB} {outdir}/dimple {customrefdimple}"

    if "buster" in argsfit:
        dstmtz = dstmtz.replace("merged", "truncate")
        outdir = "/".join(dstmtz.split("/")[:-1])
        if os.path.exists(outdir + "/buster"):
            buster_cmd += "rm -rf " + outdir + "/buster\n"
        buster_cmd += \
            'echo "truncate yes \\labout F=FP SIGF=SIGFP" | truncate hklin ' + srcmtz + ' hklout ' + dstmtz + \
            " | tee " + outdir + "/truncate.log\n"

        buster_cmd += "refine -L -p " + userPDB + " -m " + dstmtz + " " + customrefbuster + \
                      " -TLS -nthreads 2 -d " + outdir + "/buster \n"

    if "fspipeline" in argsfit:
        fsp_cmd += "cd " + outdir + "\n"
        fsp_cmd += fsp + "\n"

    return dimple_cmd + "\n" + buster_cmd + "\n" + fsp_cmd
