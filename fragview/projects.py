from glob import glob
from os import path
from shutil import copyfile
from django.conf import settings
from .proposals import get_proposals
import fabio
from fragview.versions import HZB_PYTHON

UPDATE_STATUS_SCRIPT = "update_status.py"
READ_MTZ_FLAGS = "read_mtz_flags.py"
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
    return proposal_dir(proposal_number)


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


def copy_missing_script(project, python_script):
    # This copy function should be removed after a few users copy files to their folders.

    if not path.exists(f"{project.data_path()}/fragmax/scripts/{python_script}"):
        copyfile(f"/data/staff/biomax/webapp/static/scripts/{python_script}",
                 f"{project.data_path()}/fragmax/scripts/{python_script}")


def project_read_mtz_flags(project, hklin):
    # This copy function should be removed after a few users copy files to their folders.

    copy_missing_script(project, READ_MTZ_FLAGS)
    return \
        project_script(project, READ_MTZ_FLAGS) + \
        f" {hklin}"


def project_pandda_worker(project, options):
    # This copy function should be removed after a few users copy files to their folders.

    copy_missing_script(project, PANDDA_WORKER)
    return "python " + \
        project_script(project, PANDDA_WORKER) + \
        f' {project.data_path()} {project.protein} "{options}"'


def project_update_status_script_cmds(project, sample, softwares):
    return f"{HZB_PYTHON} {project_update_status_script(project)} {sample} {project.proposal}/{project.shift}\n"


def shifts_raw_master_h5_files(project, shifts):
    """
    generate a list of .h5 image files from the 'raw' directory
    for specified shits

    shifts - list of shift
    """
    shift_dirs = [shift_dir(project.proposal, s) for s in shifts]
    for sdir in shift_dirs:
        for file in glob(f"{sdir}/raw/{project.protein}/*/*master.h5"):
            yield file


def project_raw_master_cbf_files(project):
    for file in glob(f"{project.data_path()}/raw/{project.protein}/{project.protein}*/{project.protein}*0001.cbf"):
        yield file


def project_raw_master_h5_files(project):
    return shifts_raw_master_h5_files(project, project.shifts())


def cbf_to_xml(project):
    """
    generate a XML file from CBF file. It is similar to what is genereated by MAX IV for ISPyB
    """
    raw_cbf_folder = f"/data/fragmaxrpc/user/{project.proposal}/raw/{project.protein}"

    fragmax_dir = path.join(project.data_path(), "fragmax")

    for dataset in sorted(glob(f"{raw_cbf_folder}/*"), key=lambda x: ("Apo" in x, x)):
        dts = dataset.split("/")[-1]
        runs = set([cbf_filename.split("_")[-2] for cbf_filename in
                    glob(f"{dataset}/{project.protein}*cbf")])
        for run in runs:
            dataset = f"{dts}_{run}"
            cbf_range = sorted(glob(f"{raw_cbf_folder}/{dts}/{dataset}_*.cbf"))
            print(dataset)
            print(f"{project.protein}-{project.library.name}")
            cbf_ini, cbf_end = cbf_range[::len(cbf_range)-1]
            file = path.join(fragmax_dir, "process", project.protein, dts, f"{dataset}.xml")
            _create_xml_file(project, dataset, cbf_ini, cbf_end)
            yield file


def shifts_xml_files(project, shifts):
    """
    generate a list of metadata collection xml files for
    the specified project's shifts

    shifts - list of shift
    """
    raw_cbf_folder = f"/data/fragmaxrpc/user/{project.proposal}/raw/{project.protein}"

    fragmax_dir = path.join(project.data_path(), "fragmax")

    for dataset in sorted(glob(f"{raw_cbf_folder}/*"), key=lambda x: ("Apo" in x, x)):
        dts = dataset.split("/")[-1]
        runs = set([cbf_filename.split("_")[-2] for cbf_filename in
                    glob(f"{dataset}/{project.protein}*cbf")])

        for run in runs:
            dataset = f"{dts}_{run}"
            cbf_range = sorted(glob(f"{raw_cbf_folder}/{dts}/{dataset}_*.cbf"))
            cbf_ini, cbf_end = cbf_range[::len(cbf_range)-1]
            file = path.join(fragmax_dir, "process", project.protein, dts, f"{dataset}.xml")
            _create_xml_file(project, dataset, cbf_ini, cbf_end)
            yield file
    # shift_dirs = [shift_dir(project.proposal, s) for s in shifts]
    # for sdir in shift_dirs:
    #     for file in glob(
    #             f"{sdir}**/process/{project.protein}/**/**/fastdp/cn**/"
    #             f"ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml"):
    #         yield file


def project_xml_files(project):
    return shifts_xml_files(project, project.shifts())


def project_fragment_cif(project, fragment):
    return path.join(project_fragments_dir(project), f"{fragment}.cif")


def project_fragment_pdb(project, fragment):
    return path.join(project_fragments_dir(project), f"{fragment}.pdb")


def project_model_path(project, pdb_file):
    return path.join(project.data_path(), "fragmax", "models", pdb_file)


def project_static_url(project):
    return path.join("/", "static", "fraghome", project.proposal)


def _create_xml_file(project, dataset, cbf_ini, cbf_end):
    def format_e(n):
        a = '%E' % n
        return a.split('E')[0].rstrip('0').rstrip('.') + 'E' + a.split('E')[1]

    header_i = fabio.open(cbf_ini).header
    file_i = header_i["_array_data.header_contents"].splitlines()

    header_e = fabio.open(cbf_end).header
    file_e = header_e["_array_data.header_contents"].splitlines()

    cbf = [x.rstrip().replace("# ", "") for x in file_i]
    cbf_e = [x.rstrip().replace("# ", "") for x in file_e]

    axisEnd = 0
    axisStart = float(cbf[10].split()[1]) * float(cbf[7].split()[1])
    beamSizeAtSampleX = format_e(float(cbf[11].split()[1][1:-1]) / 1000)
    beamSizeAtSampleY = format_e(float(cbf[11].split()[2][:-1]) / 1000)
    dataCollectionNumer = cbf_ini.split("_")[-2]
    detectorDistance = format_e(float(cbf[16].split()[1]) * 1000)
    detectorModel = " ".join(cbf[0].split()[1:3]).replace(",", "")
    if detectorModel == "PILATUS3 2M":
        detectorType = "Hybrid Photon Counting"
        experimentBeamline = "BESSY II 14.2"
    elif detectorModel == "PILATUS3 6M":
        detectorType = "Hybrid Photon Counting"
        experimentBeamline = "BESSY II 14.2"
    else:
        detectorType = "Unknown"
        experimentBeamline = "Unknown"

    X = cbf[2].split()[1]
    Y = cbf[2].split()[4]
    detectorPixelSize = "{:.3f}".format(float(X) * 1000) + " mm x " + "{:.3f}".format(float(Y) * 1000) + " mm"
    endTime = cbf_e[1]
    exposureTime = format_e(float(cbf[12].split()[1]))
    fileTemplate = "_".join(cbf_ini.split("/")[-1].split("_")[:-1]) + "_%04d.cbf"
    flux = cbf[27].split()[1]
    imagePrefix = dataset.split("_")[0]
    imageDirectory = f"/data/fragmaxrpc/user/{project.proposal}/raw/{project.protein}/{imagePrefix}"
    numberOfImages = cbf[10].split()[1]
    resolution = format_e(float(cbf[16].split()[1]) * 8.178158027176648)
    slitGapHorizontal = "0.0"
    slitGapVertical = "0.0"
    startTime = cbf[1]
    synchrotronMode = ""
    transmission = format_e(float(cbf[25].split()[1]))
    wavelength = format_e(float(cbf[30].split()[1]))
    xtalSnapshotFullPath1 = "None"
    xtalSnapshotFullPath2 = "None"
    detector2theta = format_e(float(cbf[26].split()[1]))
    rotationAxis = cbf[4].split()[1]



    xml = f"""<?xml version="1.0" ?>
    <XSDataResultRetrieveDataCollection>
        <dataCollection>
            <actualCenteringPosition> sampx=0 sampy=0 phi=0.000000 focus=0 phiz=0 phiy=0</actualCenteringPosition>
            <detectorModel>{detectorModel}</detectorModel>
            <detectorType>{detectorType}</detectorType>
            <detectorPixelSize>{detectorPixelSize}</detectorPixelSize>
            <experimentBeamline>{experimentBeamline}</experimentBeamline>
            <axisEnd>{axisEnd}</axisEnd>
            <axisRange>0.000000e+00</axisRange>
            <axisStart>{axisStart}</axisStart>
            <beamShape>ellipse</beamShape>
            <beamSizeAtSampleX>{beamSizeAtSampleX}</beamSizeAtSampleX>
            <beamSizeAtSampleY>{beamSizeAtSampleY}</beamSizeAtSampleY>
            <centeringMethod>None</centeringMethod>
            <comments>None</comments>
            <crystalClass>None</crystalClass>
            <dataCollectionId>None</dataCollectionId>
            <dataCollectionNumber>{dataCollectionNumer}</dataCollectionNumber>
            <detector2theta>{detector2theta}</detector2theta>
            <detectorDistance>{detectorDistance}</detectorDistance>
            <detectorMode>None</detectorMode>
            <endTime>{endTime}</endTime>
            <exposureTime>{exposureTime}</exposureTime>
            <experimentType>None</experimentType>
            <fileTemplate>{fileTemplate}</fileTemplate>
            <flux>{flux}</flux>
            <imageDirectory>{imageDirectory}</imageDirectory>
            <imagePrefix>{imagePrefix}</imagePrefix>
            <imageSuffix>cbf</imageSuffix>
            <kappaStart>0.000000e+00</kappaStart>
            <numberOfImages>{numberOfImages}</numberOfImages>
            <numberOfPasses>1</numberOfPasses>
            <overlap>0.000000e+00</overlap>
            <phiStart>0.000000e+00</phiStart>
            <printableForReport>false</printableForReport>
            <resolution>{resolution}</resolution>
            <rotationAxis>{rotationAxis}</rotationAxis>
            <runStatus>Data collection successful</runStatus>
            <slitGapVertical>{slitGapVertical}</slitGapVertical>
            <slitGapHorizontal>{slitGapHorizontal}</slitGapHorizontal>
            <startImageNumber>1</startImageNumber>
            <startTime>{startTime}</startTime>
            <synchrotronMode>{synchrotronMode}</synchrotronMode>
            <transmission>{transmission}</transmission>
            <wavelength>{wavelength}</wavelength>
            <xbeam>0.00000e+00</xbeam>
            <xtalSnapshotFullPath1>{xtalSnapshotFullPath1}</xtalSnapshotFullPath1>
            <xtalSnapshotFullPath2>{xtalSnapshotFullPath2}</xtalSnapshotFullPath2>
            <xtalSnapshotFullPath3>None</xtalSnapshotFullPath3>
            <xtalSnapshotFullPath4>None</xtalSnapshotFullPath4>
            <ybeam>0.00000e+00</ybeam>
        </dataCollection>
    </XSDataResultRetrieveDataCollection>
    """
    dstxml = path.join(project.data_path(), "fragmax", "process", project.protein, imagePrefix, f"{dataset}.xml")

    with open(dstxml, "w") as xmlFile:
        xmlFile.write(xml)
