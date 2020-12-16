import glob
from os import path
from pathlib import Path
from fragview.sites import SITE
from .proposals import get_proposals


UPDATE_STATUS_SCRIPT = "update_status.py"
UPDATE_RESULTS_SCRIPT = "update_results.py"
PANDDA_WORKER = "pandda_prepare_runs.py"


def current_project(request):
    proposals = get_proposals(request)
    return request.user.get_current_project(proposals)


def have_pending_projects(request):
    proposals = get_proposals(request)
    return request.user.have_pending_projects(proposals)


def proposal_dir(proposal_number):
    return path.join(SITE.PROPOSALS_DIR, proposal_number)


def shift_dir(proposal_number, shift):
    return path.join(proposal_dir(proposal_number), shift)


def parse_dataset_name(dset_name):
    """
    split full dataset name into sample name and run number

    e.g. 'Nsp10-apo33_1' becomes 'Nsp10-apo33' and 1
    """
    return dset_name.rsplit("_", 1)


def dataset_xml_file(project, data_set):
    set_name, _ = parse_dataset_name(data_set)

    return Path(project_process_protein_dir(project), set_name, f"{data_set}.xml")


def dataset_master_image(dataset):
    return SITE.dataset_master_image(dataset)


def protein_dir(proposal_number, shift, protein):
    return path.join(shift_dir(proposal_number, shift), "raw", protein)


def project_raw_protein_dir(project):
    return protein_dir(project.proposal, project.shift, project.protein)


def project_shift_dirs(project):
    for shift in project.shifts():
        yield shift_dir(project.proposal, shift)


def project_fragmax_dir(project):
    return path.join(project.data_path(), "fragmax")


def project_process_dir(project):
    return path.join(project_fragmax_dir(project), "process")


def project_fragments_dir(project):
    return path.join(project_fragmax_dir(project), "fragments")


def project_results_dir(project):
    return path.join(project_fragmax_dir(project), "results")


def project_models_dir(project):
    return path.join(project_fragmax_dir(project), "models")


def project_scripts_dir(project):
    return path.join(project.data_path(), "fragmax", "scripts")


def project_logs_dir(project):
    return path.join(project_fragmax_dir(project), "logs")


def project_pandda_results_dir(project):
    return path.join(project_fragmax_dir(project), "results", "pandda", project.protein)


def project_pandda_processed_dataset_dir(project, method, dataset):
    return Path(
        project_pandda_results_dir(project),
        method,
        "pandda",
        "processed_datasets",
        dataset,
    )


def project_model_file(project, model_file):
    return path.join(project_models_dir(project), model_file)


def project_process_protein_dir(project):
    return path.join(project_process_dir(project), project.protein)


def project_results_file(project):
    return path.join(project_process_protein_dir(project), "results.csv")


def project_all_status_file(project):
    return path.join(project_process_protein_dir(project), "allstatus.csv")


def project_data_collections_file(project):
    return path.join(project_process_protein_dir(project), "datacollections.csv")


def project_script(project, script_file):
    """
    generate full path to a file named 'script_file' inside project's script directory
    """
    return path.join(project_scripts_dir(project), script_file)


def project_log_path(project, log_file):
    """
    generate full path to a file name 'log_file' inside project's logs directory
    """
    return path.join(project_logs_dir(project), log_file)


def project_syslog_path(project, log_file):
    return path.join(project_logs_dir(project), "system", log_file)


def project_update_status_script(project):
    return project_script(project, UPDATE_STATUS_SCRIPT)


def project_update_results_script(project):
    return project_script(project, UPDATE_RESULTS_SCRIPT)


def project_update_status_script_cmds(project, sample, softwares):
    dataset, run = sample.split("_")
    return (
        "module purge\n"
        + "module load gopresto GCCcore/8.3.0 Python/3.7.4\n"
        + f"python3 {project_update_status_script(project)} {project.data_path()} {dataset} {run}\n"
        + "module purge\n"
        + f"module load gopresto {softwares}\n"
    )


def project_update_results_script_cmds(project, sample, softwares):
    return (
        "module purge\n"
        + "module load gopresto GCCcore/8.3.0 Python/3.7.4\n"
        + f"python3 {project_update_results_script(project)} {sample} {project.proposal}/{project.shift}\n"
        + "module purge\n"
        + f"module load gopresto {softwares}\n"
    )


def shifts_raw_master_h5_files(project, shifts):
    """
    generate a list of .h5 image files from the 'raw' directory
    for specified shits

    shifts - list of shift
    """
    shift_dirs = [shift_dir(project.proposal, s) for s in shifts]
    for sdir in shift_dirs:
        for file in glob.glob(f"{sdir}/raw/{project.protein}/*/*master.h5"):
            yield file


def project_raw_master_h5_files(project):
    return shifts_raw_master_h5_files(project, project.shifts())


def project_datasets(project):
    return SITE.get_project_datasets(project)


def shifts_xml_files(project, shifts):
    """
    generate a list of metadata collection xml files for
    the specified project's shifts

    shifts - list of shift
    """
    shift_dirs = [shift_dir(project.proposal, s) for s in shifts]
    for sdir in shift_dirs:
        for file in glob.glob(
            f"{sdir}**/process/{project.protein}/**/**/fastdp/cn**/"
            f"ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml"
        ):
            yield file


def project_xml_files(project):
    return shifts_xml_files(project, project.shifts())


def project_fragment_cif(project, fragment):
    return path.join(project_fragments_dir(project), f"{fragment}.cif")


def project_fragment_pdb(project, fragment):
    return path.join(project_fragments_dir(project), f"{fragment}.pdb")


def project_model_path(project, pdb_file):
    return path.join(project.data_path(), "fragmax", "models", pdb_file)


def project_static_url(project):
    return path.join("/", "static", "biomax", project.proposal, project.shift)


def get_update_results_command(project, dataset, run):
    return f"python3 {project_update_results_script(project)} {project.data_path()} {dataset} {run}"
