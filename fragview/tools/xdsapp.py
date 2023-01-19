from fragview.tools import ProcessOptions
from fragview.versions import XDSAPP_MOD
from fragview.projects import Project, project_log_path, project_script
from fragview.sites.plugin import BatchFile, Duration
from fragview.sites.current import get_hpc_runner, get_xdsapp_command

PRESTO_MODULES = ["gopresto", XDSAPP_MOD]


def _get_space_group_cell_argument(options: ProcessOptions):
    def _cell_arg():
        if options.cell is None:
            # no (aka 'auto') cell parameters specified
            return ""

        cell = options.cell
        return f" {cell.a} {cell.b} {cell.c} {cell.alpha} {cell.beta} {cell.gamma}"

    space_group = options.space_group
    if space_group is None:
        # no (aka 'auto') space group specified
        return ""

    return f"--spacegroup='{space_group.number}{_cell_arg()}'"


def _get_friedel_argument(options: ProcessOptions):
    val = "True" if options.friedel_law else "False"
    return f"--fried={val}"


def generate_batch(project: Project, dataset, options: ProcessOptions) -> BatchFile:
    dest_dir = project.get_dataset_process_dir(dataset)
    xdsapp_command, cpus = get_xdsapp_command(
        dest_dir,
        _get_space_group_cell_argument(options),
        options.custom_args,
        _get_friedel_argument(options),
        project.get_dataset_master_image(dataset),
        dataset.images,
    )

    script_prefix = f"xdsapp-{dataset.name}"
    batch = get_hpc_runner().new_batch_file(
        "XDSAPP",
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

    batch.add_commands(
        f"mkdir -p {dest_dir}/xdsapp",
        f"cd {dest_dir}/xdsapp",
        xdsapp_command,
    )

    return batch
