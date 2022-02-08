from pathlib import Path
from fragview.views import crypt_shell
from fragview.tools import RefineOptions
from fragview.versions import BUSTER_MOD, PHENIX_MOD
from fragview.projects import Project, project_log_path, project_script
from fragview.sites.plugin import BatchFile, Duration, DataSize
from fragview.sites.current import get_hpc_runner, get_fspipeline_commands


PRESTO_MODULES = ["gopresto", BUSTER_MOD, PHENIX_MOD]


def generate_batch(
    project: Project, dataset, proc_tool: str, input_mtz: Path, options: RefineOptions
) -> BatchFile:

    cmds, cpus = get_fspipeline_commands(options.pdb_file, options.custom_args)

    script_prefix = f"fspipeline-{proc_tool}-{dataset.name}"
    batch = get_hpc_runner().new_batch_file(
        f"fspipeline",
        project_script(project, f"{script_prefix}.sh"),
        project_log_path(project, f"{script_prefix}_%j_out.txt"),
        project_log_path(project, f"{script_prefix}_%j_err.txt"),
        cpus,
    )

    batch.set_options(
        time=Duration(hours=12),
        nodes=1,
        mem_per_cpu=DataSize(gigabyte=5),
    )

    batch.add_commands(crypt_shell.crypt_cmd(project))

    batch.assign_variable("WORK_DIR", "`mktemp -d`")

    batch.add_commands(
        "cd $WORK_DIR",
        crypt_shell.fetch_file(project, options.pdb_file, "model.pdb"),
        crypt_shell.fetch_file(project, input_mtz, "input.mtz"),
    )

    # TODO: load tool specific modules?
    batch.load_modules(PRESTO_MODULES)

    results_dir = Path(project.get_dataset_results_dir(dataset), proc_tool)

    batch.add_commands(
        *cmds,
        "# upload results\n",
        f"rm $WORK_DIR/model.pdb\n",
        f"{crypt_shell.upload_dir(project, '$WORK_DIR', results_dir)}",
        "cd",
        "rm -rf $WORK_DIR",
    )

    return batch
