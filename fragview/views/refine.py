import os
import time
import pyfastcopy  # noqa
import threading
from glob import glob
from django.shortcuts import render
from django.http import HttpResponseBadRequest
from fragview import hpc
from fragview.views import crypt_shell
from fragview.projects import current_project, project_script, project_update_status_script_cmds
from fragview.projects import project_update_results_script_cmds
from fragview.models import PDB
from fragview.forms import RefineForm
from .utils import Filter


def datasets(request):
    proj = current_project(request)

    form = RefineForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(f"invalid refinement arguments {form.errors}")

    pdbmodel = PDB.get(form.pdb_model)

    worker_args = (
        proj,
        form.use_dimple,
        form.use_fspipeline,
        form.use_buster,
        pdbmodel.file_path(),
        form.ref_space_group,
        form.datasets_filter,
        form.custom_dimple,
        form.custom_buster,
        form.custom_fspipe,
        form.run_aimless,
    )

    t1 = threading.Thread(target=run_structure_solving, args=worker_args)
    t1.daemon = True
    t1.start()

    return render(request, "fragview/jobs_submitted.html")


def run_structure_solving(
    proj,
    useDIMPLE,
    useFSP,
    useBUSTER,
    userPDB,
    spacegroup,
    filters,
    customrefdimple,
    customrefbuster,
    customreffspipe,
    aimless,
):
    # Modules list for HPC env
    softwares = "PReSTO autoPROC BUSTER Phenix/1.17.1-3660-Rosetta-3.10-5-PReSTO"
    customreffspipe = customreffspipe.split("customrefinefspipe:")[-1]
    customrefbuster = customrefbuster.split("customrefinebuster:")[-1]
    customrefdimple = customrefdimple.split("customrefinedimple:")[-1]
    argsfit = "none"

    filters = filters.split(":")[-1]
    if filters == "ALL":
        filters = ""
    if filters == "NEW":
        refinedDatasets = (
            glob(f"{proj.data_path()}/fragmax/results/{proj.protein}*/*/dimple")
            + glob(f"{proj.data_path()}/fragmax/results/{proj.protein}*/*/fspipeline")
            + glob(f"{proj.data_path()}/fragmax/results/{proj.protein}*/*/buster")
        )
        processedDatasets = set(["/".join(x.split("/")[:-2]) for x in refinedDatasets])
        allDatasets = [
            x.split("/")[-2]
            for x in sorted(glob(f"{proj.data_path()}/fragmax/process/{proj.protein}/{proj.protein}*/*/"))
        ]
        filters = ",".join(list(set(allDatasets) - set(processedDatasets)))

    if useFSP:
        argsfit += "fspipeline"
    if useDIMPLE:
        argsfit += "dimple"
    if useBUSTER:
        argsfit += "buster"

    datasetList = glob(f"{proj.data_path()}/fragmax/process/{proj.protein}/*/*/")
    datasetList = sorted(Filter(datasetList, filters.split(",")))

    proc2resOut = f"""#!/bin/bash
#!/bin/bash
#SBATCH -t 12:00:00
#SBATCH -J Refine_FragMAX
#SBATCH -N1
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=5000
"""  # noqa E128

    prepare_cmd = f"""WORK_DIR=$(mktemp -d)
cd $WORK_DIR

{crypt_shell.fetch_file(proj, userPDB, "model.pdb")}

module purge
module load gopresto {softwares}
"""  # noqa E128

    cleanup_cmd = """
# clean-up
cd
rm -rf $WORK_DIR
"""  # noqa E128

    for dataset in datasetList:
        sample = dataset.split("/")[-2]
        script = project_script(proj, f"proc2res_{sample}.sh")
        epoch = str(round(time.time()))
        slctd_sw = argsfit.replace("none", "")

        p2rOut = ""
        p2rOut += """#SBATCH -o """ + proj.data_path() + f"/fragmax/logs/{sample}_{slctd_sw}_{epoch}_%j_out.txt\n"
        p2rOut += """#SBATCH -e """ + proj.data_path() + f"/fragmax/logs/{sample}_{slctd_sw}_{epoch}_%j_err.txt\n"

        with open(script, "w") as outp:
            outp.write(proc2resOut)
            outp.write(p2rOut)
            outp.write(crypt_shell.crypt_cmd(proj))

            edna = find_edna(
                proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple
            )

            fastdp = find_fastdp(
                proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple
            )

            xdsapp = find_xdsapp(
                proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple
            )

            xdsxscale = find_xdsxscale(
                proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple
            )

            dials = find_dials(
                proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple
            )

            autoproc = find_autoproc(
                proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple
            )

            for part_cmd in [edna, fastdp, xdsapp, xdsxscale, dials, autoproc]:
                outp.write(f"{prepare_cmd}{part_cmd}{cleanup_cmd}")

            outp.write(project_update_status_script_cmds(proj, sample, softwares))
            outp.write(project_update_results_script_cmds(proj, sample, softwares))
            outp.write("\n\n")

        hpc.run_sbatch(script)
        # os.remove(script)


def aimless_cmd(spacegroup, dstmtz):
    cmd = (
        f"echo 'choose spacegroup {spacegroup}' | pointless HKLIN {dstmtz} HKLOUT {dstmtz} | tee "
        f"pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "
        f"{dstmtz} HKLOUT {dstmtz} | tee aimless.log"
    )
    return cmd


def _upload_result_cmd(proj, res_dir):
    return (
        f"# upload results\n" + f"rm $WORK_DIR/model.pdb\n" + f"{crypt_shell.upload_dir(proj, '$WORK_DIR', res_dir)}"
    )


def find_autoproc(
    proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple
):

    srcmtz = None
    aimless_c = ""
    out_cmd = ""
    if glob(dataset + "autoproc/*mtz") != []:
        try:
            srcmtz = [x for x in glob(dataset + "autoproc/*mtz") if "staraniso" in x][0]
        except IndexError:
            try:
                srcmtz = [x for x in glob(dataset + "autoproc/*mtz") if "aimless" in x][0]
            except IndexError:
                srcmtz = [x for x in glob(dataset + "autoproc/*mtz")][0]

    res_dir = dataset.split("process/")[0] + "results/" + dataset.split("/")[-2] + "/autoproc/"
    dstmtz = dataset.split("/")[-2] + "_autoproc_merged.mtz"

    if srcmtz:
        cmd = aimless_cmd(spacegroup, dstmtz)
        copy = f"cp {srcmtz} {dstmtz}"
        if aimless:
            aimless_c = f"{cmd}"

        autoproc_cmd = copy + "\n" + aimless_c + "\n"
        refine_cmd = set_refine(
            argsfit, dataset, userPDB, customrefbuster, customreffspipe, customrefdimple, srcmtz, dstmtz
        )

        upload_cmd = _upload_result_cmd(proj, res_dir)
        out_cmd = f"{autoproc_cmd}\n{refine_cmd}\n{upload_cmd}"

    return out_cmd


def find_dials(
    proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple
):
    aimless_c = ""
    out_cmd = ""

    srcmtz = dataset + "dials/DEFAULT/scale/AUTOMATIC_DEFAULT_scaled.mtz"
    res_dir = dataset.split("process/")[0] + "results/" + dataset.split("/")[-2] + "/dials/"
    dstmtz = dataset.split("/")[-2] + "_dials_merged.mtz"

    if os.path.exists(srcmtz):
        cmd = aimless_cmd(spacegroup, dstmtz)
        copy = f"cp {srcmtz} {dstmtz}"
        if aimless:
            aimless_c = f"{cmd}"
        dials_cmd = copy + "\n" + aimless_c + "\n"
        refine_cmd = set_refine(
            argsfit, dataset, userPDB, customrefbuster, customreffspipe, customrefdimple, srcmtz, dstmtz
        )

        upload_cmd = _upload_result_cmd(proj, res_dir)

        out_cmd = f"{dials_cmd}\n{refine_cmd}\n{upload_cmd}"

    return out_cmd


def find_xdsxscale(
    proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple
):
    aimless_c = ""
    out_cmd = ""
    res_dir = dataset.split("process/")[0] + "results/" + dataset.split("/")[-2] + "/xdsxscale/"
    srcmtz = dataset + "xdsxscale/DEFAULT/scale/AUTOMATIC_DEFAULT_scaled.mtz"
    dstmtz = dataset.split("/")[-2] + "_xdsxscale_merged.mtz"
    if os.path.exists(srcmtz):
        cmd = aimless_cmd(spacegroup, dstmtz)
        copy = f"cp {srcmtz} {dstmtz}"
        if aimless:
            aimless_c = f"{cmd}"
        xdsxscale_cmd = copy + "\n" + aimless_c + "\n"
        refine_cmd = set_refine(
            argsfit, dataset, userPDB, customrefbuster, customreffspipe, customrefdimple, srcmtz, dstmtz
        )

        upload_cmd = _upload_result_cmd(proj, res_dir)

        out_cmd = f"{xdsxscale_cmd}\n{refine_cmd}\n{upload_cmd}"

    return out_cmd


def find_xdsapp(
    proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple
):

    srcmtz = False
    dstmtz = None
    aimless_c = ""
    out_cmd = ""
    mtzoutList = glob(dataset + "xdsapp/*F.mtz")

    if mtzoutList != []:
        srcmtz = mtzoutList[0]
        res_dir = dataset.split("process/")[0] + "results/" + dataset.split("/")[-2] + "/xdsapp/"
        dstmtz = dataset.split("/")[-2] + "_xdsapp_merged.mtz"

    if srcmtz:
        cmd = aimless_cmd(spacegroup, dstmtz)
        copy = f"cp {srcmtz} {dstmtz}"
        if aimless:
            aimless_c = f"{cmd}"

        xdsapp_cmd = copy + "\n" + aimless_c + "\n"
        refine_cmd = set_refine(
            argsfit, dataset, userPDB, customrefbuster, customreffspipe, customrefdimple, srcmtz, dstmtz
        )

        upload_cmd = _upload_result_cmd(proj, res_dir)

        out_cmd = f"{xdsapp_cmd}\n{refine_cmd}\n{upload_cmd}"
    return out_cmd


def find_edna(proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple):
    srcmtz = False
    dstmtz = None
    aimless_c = ""

    out_cmd = ""
    mtzoutList = glob(
        proj.data_path()
        + "/fragmax/process/"
        + proj.protein
        + "/"
        + dataset.split("/")[-3]
        + "/*/edna/*_noanom_aimless.mtz"
    )

    if mtzoutList != []:
        srcmtz = mtzoutList[0]
        res_dir = dataset.split("process/")[0] + "results/" + dataset.split("/")[-2] + "/edna/"
        dstmtz = dataset.split("/")[-2] + "_EDNA_merged.mtz"

    if srcmtz:
        cmd = aimless_cmd(spacegroup, dstmtz)
        copy = f"cp {srcmtz} {dstmtz}"
        if aimless:
            aimless_c = f"{cmd}"
        edna_cmd = copy + "\n" + aimless_c + "\n"

        refine_cmd = set_refine(
            argsfit, dataset, userPDB, customrefbuster, customreffspipe, customrefdimple, srcmtz, dstmtz
        )

        upload_cmd = _upload_result_cmd(proj, res_dir)

        out_cmd = f"{edna_cmd}\n{refine_cmd}\n{upload_cmd}"

    return out_cmd


def find_fastdp(
    proj, dataset, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple
):
    srcmtz = False
    dstmtz = None
    aimless_c = ""
    out_cmd = ""
    mtzoutList = glob(
        proj.data_path() + "/fragmax/process/" + proj.protein + "/" + dataset.split("/")[-3] + "/*/fastdp/*.mtz"
    )

    if mtzoutList != []:
        srcmtz = mtzoutList[0]
        res_dir = dataset.split("process/")[0] + "results/" + dataset.split("/")[-2] + "/fastdp/"
        dstmtz = dataset.split("/")[-2] + "_fastdp_merged.mtz"

    if srcmtz:
        cmd = aimless_cmd(spacegroup, dstmtz)
        copy = f"cp {srcmtz} {dstmtz}"
        if aimless:
            aimless_c = f"{cmd}"
        fastdp_cmd = copy + "\n" + aimless_c + "\n"
        refine_cmd = set_refine(
            argsfit, dataset, userPDB, customrefbuster, customreffspipe, customrefdimple, srcmtz, dstmtz
        )

        upload_cmd = _upload_result_cmd(proj, res_dir)

        out_cmd = f"{fastdp_cmd}\n{refine_cmd}\n{upload_cmd}"

    return out_cmd


def set_refine(argsfit, dataset, userPDB, customrefbuster, customreffspipe, customrefdimple, srcmtz, dstmtz):
    dimple_cmd = ""
    buster_cmd = ""
    fsp_cmd = ""
    srcmtz = dstmtz

    fsp = (
        """python /mxn/groups/biomax/wmxsoft/fspipeline/fspipeline.py --sa=false --refine="""
        + userPDB
        + """ --exclude="dimple fspipeline buster unmerged rhofit ligfit truncate" --cpu=2 """
        + customreffspipe
    )

    if "dimple" in argsfit:
        dimple_cmd += f"dimple {dstmtz} model.pdb dimple {customrefdimple}"

    if "buster" in argsfit:
        dstmtz = dstmtz.replace("merged", "truncate")
        outdir = "/".join(dstmtz.split("/")[:-1])
        if os.path.exists(outdir + "/buster"):
            buster_cmd += "rm -rf " + outdir + "/buster\n"
        buster_cmd += (
            'echo "truncate yes \\labout F=FP SIGF=SIGFP" | truncate hklin '
            + srcmtz
            + " hklout "
            + dstmtz
            + " | tee "
            + outdir
            + "truncate.log\n"
        )

        buster_cmd += (
            "refine -L -p "
            + userPDB
            + " -m "
            + dstmtz
            + " "
            + customrefbuster
            + " -TLS -nthreads 2 -d "
            + outdir
            + "buster \n"
        )

    if "fspipeline" in argsfit:
        fsp_cmd += fsp + "\n"

    return dimple_cmd + "\n" + buster_cmd + "\n" + fsp_cmd
