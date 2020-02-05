import glob
from os import path
from django.conf import settings
from .proposals import get_proposals

UPDATE_STATUS_SCRIPT = "update_status.py"


def current_project(request):
    proposals = get_proposals(request)
    return request.user.get_current_project(proposals)


def have_pending_projects(request):
    proposals = get_proposals(request)
    return request.user.have_pending_projects(proposals)


def proposal_dir(proposal_number):
    return path.join(settings.PROPOSALS_DIR, proposal_number)


def shift_dir(proposal_number, shift):
    return path.join(proposal_dir(proposal_number), shift)


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


def project_results_dir(project):
    return path.join(project_fragmax_dir(project), "results")


def project_models_dir(project):
    return path.join(project_fragmax_dir(project), "models")


def project_model_file(project, model_file):
    return path.join(project_models_dir(project), model_file)


def project_process_protein_dir(project):
    return path.join(project_process_dir(project), project.protein)


def project_results_file(project):
    return path.join(project_process_protein_dir(project), "results.csv")


def project_all_status_file(project):
    return path.join(project_process_protein_dir(project), "allstatus.csv")


def project_script(project, script_file):
    """
    generate full path to a file named 'script_file' inside project's script directory
    """
    return path.join(project.data_path(), "fragmax", "scripts", script_file)


def project_update_status_script(project):
    return project_script(project, UPDATE_STATUS_SCRIPT)


def project_update_status_script_cmds(project, sample, softwares):
    return \
        "module purge\n" + \
        "module load GCCcore/8.3.0 Python/3.7.4\n" + \
        f"python3 {project_update_status_script(project)} {sample} {project.proposal}/{project.shift}\n" + \
        "module purge\n" + \
        f"module load {softwares}\n"


def project_raw_master_h5_files(project):
    for shift_dir in project_shift_dirs(project):
        for file in glob.glob(f"{shift_dir}/raw/{project.protein}/*/*master.h5"):
            yield file


def project_xml_files(project):
    for shift_dir in project_shift_dirs(project):
        for file in glob.glob(
                f"{shift_dir}**/process/{project.protein}/**/**/fastdp/cn**/"
                f"ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml"):
            yield file


def project_ligand_cif(project, ligand):
    return path.join(
        project.data_path(), "fragmax", "process", "fragment", project.library, ligand, f"{ligand}.cif")


def project_model_path(project, pdb_file):
    return path.join(project.data_path(), "fragmax", "models", pdb_file)


def project_static_url(project):
    return path.join("/", "static", "biomax", project.proposal, project.shift)
