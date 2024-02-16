from pathlib import Path
from fragview.projects import Project, project_script, project_log_path
from fragview.sites.plugin import DataSize, Duration, HPC
from fragview.sites.current import get_hpc_runner
from fragview.versions import CCP4_PANDDA_MOD, BUSTER_MOD
from fragview.views.utils import get_fragment_by_id
from fragview.tools.acedrg import get_ligand_restrains_commands
from jobs.client import JobsSet

# how many CPU should pandda job use
_CPUS = 40

# time limit for pandda jobs
_JOB_TIME = Duration(hours=48)


def _get_pandda_command():
    return (
        "pandda.analyse data_dirs=$_data_dir/* out_dir=$_out_dir "
        f"cpus={_CPUS} events.order_by=cluster_size pdb_style=final.pdb "
        "mtz_style=final.mtz low_resolution_completeness=90.0"
    )


def _get_copy_commands(project: Project, refine_results):
    def generate_copy_command():
        for refine_result in refine_results:
            dest_dir = f"$_data_dir/{refine_result.result.dataset.name}"
            res_dir = project.get_refine_result_dir(refine_result)
            final_files = "final.{pdb,mtz,mmcif}"
            yield f"mkdir {dest_dir}"
            yield f"cp --verbose {res_dir}/{final_files} {dest_dir}"

    return list(generate_copy_command())


def _get_ligand_files_command(refine_results):
    def generate_commands():
        for refine_result in refine_results:
            dataset = refine_result.result.dataset
            fragment = get_fragment_by_id(dataset.crystal.fragment_id)

            out = f"$_proc_dir/{dataset.name}/ligand_files/{dataset.name}"

            for cmd in get_ligand_restrains_commands(fragment.smiles, out):
                yield cmd
            yield f"rm -rf {out}_TMP"

    return list(generate_commands())


def _create_pandda_batch(
    project: Project,
    root_dir: Path,
    refine_results,
    hpc: HPC,
    job_name: str,
):
    batch = hpc.new_batch_file(
        job_name,
        project_script(project, f"{job_name}.sh"),
        project_log_path(project, f"{job_name}_%j_out.txt"),
        project_log_path(project, f"{job_name}_%j_err.txt"),
        cpus=_CPUS,
    )
    batch.set_options(
        exclusive=True, nodes=1, time=_JOB_TIME, memory=DataSize(gigabyte=104)
    )

    batch.load_modules(["gopresto", CCP4_PANDDA_MOD])

    data_dir = Path(root_dir, "input")
    out_dir = Path(root_dir, "result")

    batch.assign_variable("_data_dir", data_dir)
    batch.assign_variable("_out_dir", out_dir)
    batch.add_commands(
        "rm -rfv $_data_dir",
        "mkdir --parents $_data_dir",
        "rm -rfv $_out_dir",
        *_get_copy_commands(project, refine_results),
        _get_pandda_command(),
    )

    batch.save()
    return batch


def _create_ligands_batch(
    project: Project, root_dir: Path, refine_results, hpc: HPC, job_name: str
):
    #
    # commands to generate ligand restrains files
    #
    # note, these files are not used by PanDDa itself,
    # but are used for analysis in e.g. Coot later
    #

    batch = hpc.new_batch_file(
        job_name,
        project_script(project, f"{job_name}_ligands.sh"),
        project_log_path(project, f"{job_name}_ligands_%j_out.txt"),
        project_log_path(project, f"{job_name}_ligands_%j_err.txt"),
        cpus=_CPUS,
    )
    batch.set_options(exclusive=True, nodes=1, time=_JOB_TIME)

    batch.load_modules(["gopresto", BUSTER_MOD])

    proc_dir = Path(root_dir, "result", "processed_datasets")
    batch.assign_variable("_proc_dir", proc_dir)

    batch.add_commands(
        *_get_ligand_files_command(refine_results),
    )

    batch.save()
    return batch


def create_pandda_jobs(
    project: Project, proc_tool: str, refine_tool: str, refine_results
):
    hpc = get_hpc_runner()
    job_name = f"pandda-{proc_tool}-{refine_tool}"
    root_dir = Path(project.pandda_dir, f"{proc_tool}-{refine_tool}")

    pandda_batch = _create_pandda_batch(
        project, root_dir, refine_results, hpc, job_name
    )
    ligands_batch = _create_ligands_batch(
        project, root_dir, refine_results, hpc, job_name
    )

    jobs = JobsSet(project, job_name)
    jobs.add_job(pandda_batch)
    jobs.add_job(ligands_batch, run_after=[pandda_batch])
    jobs.submit()
