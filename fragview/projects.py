import glob
from os import path
# from shutil import copyfile
from django.conf import settings
from .proposals import get_proposals

UPDATE_STATUS_SCRIPT = "update_status.py"
PANDDA_WORKER = "pandda_prepare_runs.py"


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


def project_fragments_dir(project):
    return path.join(project_fragmax_dir(project), "fragments")


def project_results_dir(project):
    return path.join(project_fragmax_dir(project), "results")


def project_models_dir(project):
    return path.join(project_fragmax_dir(project), "models")


def project_scripts_dir(project):
    return path.join(project.data_path(), "fragmax", "scripts")


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


def project_update_status_script(project):
    return project_script(project, UPDATE_STATUS_SCRIPT)


# def copy_missing_script(project, python_script):
#     # This copy function should be removed after a few users copy files to their folders.
#     if not path.exists(f"{project.data_path()}/fragmax/scripts/{python_script}"):
#         copyfile(f"/data/staff/biomax/webapp/static/scripts/{python_script}",
#                  f"{project.data_path()}/fragmax/scripts/{python_script}")
#
#
# def project_read_mtz_flags(project, hklin):
#     # This copy function should be removed after a few users copy files to their folders.
#
#     copy_missing_script(project, READ_MTZ_FLAGS)
#     return \
#         project_script(project, READ_MTZ_FLAGS) + \
#         f" {hklin}"


def project_pandda_worker(project, options):
    # This copy function should be removed after a few users copy files to their folders.

    # copy_missing_script(project, PANDDA_WORKER)
    return "python " + \
        project_script(project, PANDDA_WORKER) + \
        f' {project.data_path()} {project.protein} "{options}"'


def project_update_status_script_cmds(project, sample, softwares):
    return \
        "module purge\n" + \
        "module load GCCcore/8.3.0 Python/3.7.4\n" + \
        f"python3 {project_update_status_script(project)} {sample} {project.proposal}/{project.shift}\n" + \
        "module purge\n" + \
        f"module load {softwares}\n"


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
                f"ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml"):
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
