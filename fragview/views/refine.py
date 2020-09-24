import time
import pyfastcopy  # noqa
import threading
from os import path
from glob import glob
from django.shortcuts import render
from django.http import HttpResponseBadRequest
from fragview import versions
from fragview.views import crypt_shell
from fragview.views.utils import add_update_status_script_cmds, add_update_results_script_cmds
from fragview.projects import current_project, project_script, project_process_protein_dir
from fragview.projects import project_results_dir, project_log_path
from fragview.filters import get_refine_datasets
from fragview.pipeline_commands import get_dimple_command, get_fspipeline_command, get_buster_command
from fragview.models import PDB
from fragview.forms import RefineForm
from fragview.sites import SITE
from fragview.sites.plugin import Duration, DataSize


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
    softwares = ["gopresto", versions.BUSTER_MOD, versions.PHENIX_MOD]
    customreffspipe = customreffspipe.split("customrefinefspipe:")[-1]
    customrefbuster = customrefbuster.split("customrefinebuster:")[-1]
    customrefdimple = customrefdimple.split("customrefinedimple:")[-1]
    argsfit = "none"

    if useFSP:
        argsfit += "fspipeline"
    if useDIMPLE:
        argsfit += "dimple"
    if useBUSTER:
        argsfit += "buster"

    hpc = SITE.get_hpc_runner()

    for dset in get_refine_datasets(proj, filters, useFSP, useDIMPLE, useBUSTER):
        set_name, run = dset.rsplit("_", 2)

        epoch = str(round(time.time()))
        slctd_sw = argsfit.replace("none", "")

        script_file_path = project_script(proj, f"proc2res_{dset}.sh")
        batch = hpc.new_batch_file(script_file_path)
        batch.set_options(time=Duration(hours=12), job_name="Refine_FragMAX", nodes=1, cpus_per_task=2,
                          mem_per_cpu=DataSize(kilobyte=5),
                          stdout=project_log_path(proj, f"{dset}_{slctd_sw}_{epoch}_%j_out.txt"),
                          stderr=project_log_path(proj, f"{dset}_{slctd_sw}_{epoch}_%j_err.txt"))

        batch.add_commands(crypt_shell.crypt_cmd(proj))

        edna = find_edna(
            proj, set_name, run, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster,
            customrefdimple
        )

        fastdp = find_fastdp(
            proj, set_name, run, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster,
            customrefdimple
        )

        xdsapp = find_xdsapp(
            proj, set_name, run, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster,
            customrefdimple
        )

        xdsxscale = find_xdsxscale(
            proj, set_name, run, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster,
            customrefdimple
        )

        dials = find_dials(
            proj, set_name, run, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster,
            customrefdimple
        )

        autoproc = find_autoproc(
            proj, set_name, run, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster,
            customrefdimple
        )

        for part_cmd in [edna, fastdp, xdsapp, xdsxscale, dials, autoproc]:
            if part_cmd is None:
                # skip the tools, where no result was found
                continue

            batch.add_commands(
                "WORK_DIR=$(mktemp -d)",
                "cd $WORK_DIR",
                crypt_shell.fetch_file(proj, userPDB, "model.pdb"))

            batch.purge_modules()
            batch.load_modules(softwares)

            batch.add_commands(
                part_cmd,
                "cd",
                "rm -rf $WORK_DIR"
            )

        add_update_status_script_cmds(proj, dset, batch, softwares)
        add_update_results_script_cmds(proj, dset, batch, softwares)

        batch.save()
        hpc.run_batch(script_file_path)


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
    proj, dataset, run, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple
):
    srcmtz = None
    aimless_c = ""

    glob_exp = path.join(project_process_protein_dir(proj), dataset, f"{dataset}_{run}", "autoproc", "*mtz")
    if glob(glob_exp) != []:
        try:
            srcmtz = [x for x in glob(glob_exp) if "staraniso" in x][0]
        except IndexError:
            try:
                srcmtz = [x for x in glob(glob_exp) if "aimless" in x][0]
            except IndexError:
                srcmtz = [x for x in glob(glob_exp)][0]

    res_dir = path.join(project_results_dir(proj), f"{dataset}_{run}", "autoproc")
    dstmtz = f"{dataset}_{run}_autoproc_merged.mtz"

    if not srcmtz:
        # no autoproc results found
        return None

    cmd = aimless_cmd(spacegroup, dstmtz)
    copy = f"cp {srcmtz} {dstmtz}"
    if aimless:
        aimless_c = f"{cmd}"

    autoproc_cmd = copy + "\n" + aimless_c + "\n"
    refine_cmd = set_refine(
        argsfit, userPDB, customrefbuster, customreffspipe, customrefdimple, dstmtz
    )

    upload_cmd = _upload_result_cmd(proj, res_dir)
    return f"{autoproc_cmd}\n{refine_cmd}\n{upload_cmd}"


def find_dials(
    proj, dataset, run, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple
):
    aimless_c = ""

    srcmtz = path.join(project_process_protein_dir(proj), dataset, f"{dataset}_{run}",
                       "dials", "DEFAULT", "scale", "AUTOMATIC_DEFAULT_scaled.mtz")
    res_dir = path.join(project_results_dir(proj), f"{dataset}_{run}", "dials")
    dstmtz = f"{dataset}_{run}_dials_merged.mtz"

    if not path.exists(srcmtz):
        return None

    cmd = aimless_cmd(spacegroup, dstmtz)
    copy = f"cp {srcmtz} {dstmtz}"
    if aimless:
        aimless_c = f"{cmd}"
    dials_cmd = copy + "\n" + aimless_c + "\n"
    refine_cmd = set_refine(
        argsfit, userPDB, customrefbuster, customreffspipe, customrefdimple, dstmtz
    )
    upload_cmd = _upload_result_cmd(proj, res_dir)

    return f"{dials_cmd}\n{refine_cmd}\n{upload_cmd}"


def find_xdsxscale(
    proj, dataset, run, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple
):
    aimless_c = ""
    res_dir = path.join(project_results_dir(proj), f"{dataset}_{run}", "xdsxscale")
    srcmtz = path.join(project_process_protein_dir(proj), dataset, f"{dataset}_{run}",
                       "xdsxscale", "DEFAULT", "scale", "AUTOMATIC_DEFAULT_scaled.mtz")

    dstmtz = f"{dataset}_{run}_xdsxscale_merged.mtz"

    if not path.exists(srcmtz):
        # no xds results found
        return None

    cmd = aimless_cmd(spacegroup, dstmtz)
    copy = f"cp {srcmtz} {dstmtz}"
    if aimless:
        aimless_c = f"{cmd}"
    xdsxscale_cmd = copy + "\n" + aimless_c + "\n"
    refine_cmd = set_refine(
        argsfit, userPDB, customrefbuster, customreffspipe, customrefdimple, dstmtz
    )

    upload_cmd = _upload_result_cmd(proj, res_dir)

    return f"{xdsxscale_cmd}\n{refine_cmd}\n{upload_cmd}"


def find_xdsapp(
    proj, dataset, run, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple
):
    srcmtz = False
    dstmtz = None
    aimless_c = ""

    mtzoutList = glob(path.join(project_process_protein_dir(proj), dataset, f"{dataset}_{run}", "xdsapp", "*F.mtz"))

    if mtzoutList != []:
        srcmtz = mtzoutList[0]
        res_dir = path.join(project_results_dir(proj), f"{dataset}_{run}", "xdsapp")
        dstmtz = f"{dataset}_{run}_xdsapp_merged.mtz"

    if not srcmtz:
        # no xdsapp results found
        return None

    cmd = aimless_cmd(spacegroup, dstmtz)
    copy = f"cp {srcmtz} {dstmtz}"
    if aimless:
        aimless_c = f"{cmd}"

    xdsapp_cmd = copy + "\n" + aimless_c + "\n"
    refine_cmd = set_refine(
        argsfit, userPDB, customrefbuster, customreffspipe, customrefdimple, dstmtz
    )

    upload_cmd = _upload_result_cmd(proj, res_dir)

    return f"{xdsapp_cmd}\n{refine_cmd}\n{upload_cmd}"


def find_edna(
        proj, dataset, run, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple
):
    srcmtz = False
    dstmtz = None
    aimless_c = ""

    mtzoutList = glob(path.join(project_process_protein_dir(proj), dataset, "*", "edna", "*_noanom_aimless.mtz"))

    if mtzoutList != []:
        srcmtz = mtzoutList[0]
        res_dir = path.join(project_results_dir(proj), f"{dataset}_{run}", "edna")
        dstmtz = f"{dataset}_{run}_EDNA_merged.mtz"

    if not srcmtz:
        # no edna results found
        return None

    cmd = aimless_cmd(spacegroup, dstmtz)
    copy = f"cp {srcmtz} {dstmtz}"
    if aimless:
        aimless_c = f"{cmd}"
    edna_cmd = copy + "\n" + aimless_c + "\n"

    refine_cmd = set_refine(
        argsfit, userPDB, customrefbuster, customreffspipe, customrefdimple, dstmtz
    )

    upload_cmd = _upload_result_cmd(proj, res_dir)

    return f"{edna_cmd}\n{refine_cmd}\n{upload_cmd}"


def find_fastdp(
    proj, dataset, run, aimless, spacegroup, argsfit, userPDB, customreffspipe, customrefbuster, customrefdimple
):
    srcmtz = False
    dstmtz = None
    aimless_c = ""
    mtzoutList = glob(path.join(project_process_protein_dir(proj), dataset, "*", "fastdp", "*.mtz"))

    if mtzoutList != []:
        srcmtz = mtzoutList[0]
        res_dir = path.join(project_results_dir(proj), f"{dataset}_{run}", "fastdp")
        dstmtz = f"{dataset}_{run}_fastdp_merged.mtz"

    if not srcmtz:
        # no fastdp results found
        return None

    cmd = aimless_cmd(spacegroup, dstmtz)
    copy = f"cp {srcmtz} {dstmtz}"
    if aimless:
        aimless_c = f"{cmd}"
    fastdp_cmd = copy + "\n" + aimless_c + "\n"
    refine_cmd = set_refine(
        argsfit, userPDB, customrefbuster, customreffspipe, customrefdimple, dstmtz
    )
    upload_cmd = _upload_result_cmd(proj, res_dir)

    return f"{fastdp_cmd}\n{refine_cmd}\n{upload_cmd}"


def set_refine(argsfit, userPDB, customrefbuster, customreffspipe, customrefdimple, dstmtz):
    dimple_cmd = ""
    buster_cmd = ""
    fsp_cmd = ""

    if "dimple" in argsfit:
        dimple_cmd = get_dimple_command(dstmtz, customrefdimple)

    if "buster" in argsfit:
        buster_cmd = get_buster_command(dstmtz, userPDB, customrefbuster)

    if "fspipeline" in argsfit:
        fsp_cmd = get_fspipeline_command(userPDB, customreffspipe)

    return dimple_cmd + "\n" + buster_cmd + "\n" + fsp_cmd
