from fragview.tools import ProcessOptions
from fragview.versions import DIALS_MOD
from fragview.projects import Project, project_log_path, project_script
from fragview.sites.plugin import BatchFile, Duration
from fragview.sites.current import get_hpc_runner, get_xia_dials_commands
from fragview.tools.xia2 import (
    get_space_group_argument,
    get_cell_argument,
    get_friedel_argument,
)


PRESTO_MODULES = ["gopresto", DIALS_MOD]


def generate_batch(project: Project, dataset, options: ProcessOptions) -> BatchFile:

    dials_commands, cpus = get_xia_dials_commands(
        get_space_group_argument(options.space_group),
        get_cell_argument(options.cell),
        options.custom_args,
        get_friedel_argument(options.friedel_law),
        project.get_dataset_master_image(dataset),
        dataset.images,
    )

    script_prefix = f"dials-{dataset.name}"
    batch = get_hpc_runner().new_batch_file(
        "DIALS",
        project_script(project, f"{script_prefix}.sh"),
        project_log_path(project, f"{script_prefix}_%j_out.txt"),
        project_log_path(project, f"{script_prefix}_%j_err.txt"),
        cpus,
    )

    batch.set_options(
        time=Duration(hours=168),
        exclusive=True,
        nodes=1,
    )

    batch.purge_modules()
    batch.load_modules(PRESTO_MODULES)

    dest_dir = project.get_dataset_process_dir(dataset)
    batch.add_commands(
        f"mkdir -p {dest_dir}/dials",
        f"cd {dest_dir}/dials",
        *dials_commands,
    )

    batch.add_commands(
        "echo 'remove .refl files, to conserve disk space'",
        f"rm -rfv {dest_dir}/dials/DataFiles/*.refl",
        f"rm -rfv {dest_dir}/dials/DEFAULT/scale/*.refl",
        f"rm -rfv {dest_dir}/dials/DEFAULT/SAD/*/*/*.refl",
    )

    return batch
