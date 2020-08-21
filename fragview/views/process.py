import os
import time
import threading
from os import path
from django.shortcuts import render
from django.http import HttpResponseBadRequest
from fragview.projects import current_project, project_script
from fragview.projects import project_process_protein_dir, project_log_path
from fragview import versions
from fragview.filters import get_proc_datasets, get_xml_files
from fragview.forms import ProcessForm
from fragview.xsdata import XSDataCollection
from fragview.views.utils import add_update_status_script_cmds
from fragview.sites import SITE
from fragview.sites.plugin import Duration, DataSize


def datasets(request):
    proj = current_project(request)

    form = ProcessForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(f"invalid processing arguments {form.errors}")

    filters = form.datasets_filter
    nodes = form.hpc_nodes

    options = {
        "spacegroup": form.space_group,
        "cellparam": form.cell_params,
        "friedel_law": form.friedel_law,
        "customxds": form.custom_xds,
        "customautoproc": form.custom_autoproc,
        "customdials": form.custom_dials,
        "customxdsapp": form.custom_xdsapp,
    }

    if form.use_xdsapp:
        t = threading.Thread(target=run_xdsapp, args=(proj, nodes, filters, options))
        t.daemon = True
        t.start()

    if form.use_dials:
        t = threading.Thread(target=run_dials, args=(proj, nodes, filters, options))
        t.daemon = True
        t.start()

    if form.use_autoproc:
        t = threading.Thread(target=run_autoproc, args=(proj, nodes, filters, options))
        t.daemon = True
        t.start()

    if form.use_xdsxscale:
        t = threading.Thread(target=run_xds, args=(proj, nodes, filters, options))
        t.daemon = True
        t.start()

    return render(
        request, "fragview/dataproc_datasets.html", {"allproc": "Jobs submitted using " + str(nodes) + " per method"}
    )


def _as_buckets(elms, num_buckets):
    num_elms = len(elms)

    if num_buckets > num_elms:
        num_buckets = num_elms

    # number of elements in small bucket
    small = num_elms // num_buckets

    # number of elements in large bucket
    large = small + 1

    # bucket number where we switch from large buckets to small
    cutoff = num_elms % num_buckets

    start = 0

    for n in range(num_buckets):
        if n < cutoff:
            step = large
        else:
            step = small

        end = start + step
        yield elms[start:end]

        start = end


def _get_dataset_params(proj, xml_file):
    xsdata = XSDataCollection(xml_file)

    outdir = path.join(project_process_protein_dir(proj),
                       xsdata.imagePrefix,
                       f"{xsdata.imagePrefix}_{xsdata.dataCollectionNumber}")

    h5master = path.join(xsdata.imageDirectory, xsdata.fileTemplate.replace("%06d", "master"))

    sample = outdir.split("/")[-1]

    return outdir, h5master, sample, xsdata.numberOfImages


def run_xdsapp(proj, nodes, filters, options):
    # XDSAPP cmd options
    # -h, --help
    # show this help message and exit
    # --cmd
    # start the command line version of XDSAPP
    # --suffix=SUFFIX
    # give the suffix of your images, e.g. --suffix ".cbf" (just for multi mode)
    # -i IMAGE, --image=IMAGE
    # single mode: give one image of a dataset, this dataset will be processed, e.g. -i abcd_01_010.img
    # --xdsinp
    # genereate XDS.INP for this dataset, only in single mode
    # --index
    # index dataset, only in single mode
    # --range=RANGE
    # give datarange in format --range "start end"
    # --spotrange=SPOT_RANGE
    # give spotrange manually, can be 1-3 pairs, e.g. --spotrange "1 10 20 40 60 80"
    # --org=ORGXY
    # give orgx, orgy manually: --org "orgx orgy"
    # -f FRIEDEL, --fried=FRIEDEL
    # set friedel law, give "true" or "false", default: false
    # -s SG, --spacegroup=SG
    # give spacegroup and unit cell constants in format -s "sg a b c α β γ"
    # --dir=RESULT_DIR
    # give resultdir, e.g. --dir myresults, default: xdsit/surname
    # -r REINT, --reint=REINT
    # no of reintegration cycles, default: 2
    # --live=LIVE_NO
    # live processing, give last image no., e.g. --live 200
    # --ccstar=CCSTAR
    # do resolution cutoff based on ccstar
    # -a, --all
    # multi-mode: process all datasets in a dir (recursively)
    # --cont=ALLAROUND
    # multi-mode: look continuously for datasets and process them
    # -j JOBS_NO, --jobs=JOBS_NO
    # set number of parallel jobs for xds, default: 1
    # -c CPU_NO, --cpu=CPU_NO
    # set number of cpus for xds, default: all cpus of the machine
    # --nice=NICE_LEVEL
    # set nice level of xds, default: 19
    # --res=RESOLUTION
    # use data up to resolution
    # --delphi=DELPHI
    # give delphi manually
    # --norestest
    # do resolution test

    # Modules list for HPC env
    softwares = ["gopresto", versions.CCP4_MOD, versions.XDSAPP_MOD]

    hpc = SITE.get_hpc_runner()
    epoch = str(round(time.time()))

    xml_files = list(get_xml_files(proj, get_proc_datasets(proj, filters)))
    for num, bucket in enumerate(_as_buckets(xml_files, nodes)):
        script_file_path = project_script(proj, f"xdsapp_fragmax_part{num}.sh")
        batch = hpc.new_batch_file(script_file_path)

        batch.set_options(time=Duration(hours=168), job_name="XDSAPP", exclusive=True, nodes=1,
                          cpus_per_task=64, partition="fujitsu", memory=DataSize(gigabyte=300),
                          stdout=project_log_path(proj, f"multi_xdsapp_{epoch}_%j_out.txt"),
                          stderr=project_log_path(proj, f"multi_xdsapp_{epoch}_%j_err.txt"))

        batch.purge_modules()
        batch.load_modules(softwares)

        for xml in bucket:
            outdir, h5master, sample, num_images = _get_dataset_params(proj, xml)

            os.makedirs(outdir, mode=0o760, exist_ok=True)
            os.makedirs(outdir + "/xdsapp", mode=0o760, exist_ok=True)

            if options["spacegroup"] != "":
                cellpar = " ".join(options["cellparam"].split(","))
                spacegroup = options["spacegroup"]
                spg = f"--spacegroup='{spacegroup} {cellpar}'"
            else:
                spg = ""

            customxdsapp = options["customxdsapp"]
            if options["friedel_law"] == "true":
                friedel = "--fried=True"
            else:
                friedel = "--fried=False"

            batch.add_commands(
                f"mkdir -p {outdir}/xdsapp",
                f"cd {outdir}/xdsapp",
                f"xdsapp --cmd --dir={outdir}/xdsapp -j 1 -c 64 -i {h5master} {spg} {customxdsapp} --delphi=10 "
                f"{friedel} --range=1\\ {num_images}\n")

            add_update_status_script_cmds(proj, sample, batch, softwares)

        batch.save()
        hpc.run_batch(script_file_path)


def run_autoproc(proj, nodes, filters, options):
    # Modules list for HPC env
    softwares = ["gopresto", versions.CCP4_MOD, versions.AUTOPROC_MOD, versions.DURIN_MOD]

    hpc = SITE.get_hpc_runner()
    epoch = str(round(time.time()))

    xml_files = list(get_xml_files(proj, get_proc_datasets(proj, filters)))
    for num, bucket in enumerate(_as_buckets(xml_files, nodes)):
        script_file_path = project_script(proj, f"autoproc_fragmax_part{num}.sh")
        batch = hpc.new_batch_file(script_file_path)

        batch.set_options(time=Duration(hours=168), job_name="autoPROC", exclusive=True, nodes=1,
                          cpus_per_task=64, partition="fujitsu", memory=DataSize(gigabyte=300),
                          stdout=project_log_path(proj, f"multi_autoproc_{epoch}_%j_out.txt"),
                          stderr=project_log_path(proj, f"multi_autoproc_{epoch}_%j_err.txt"))

        batch.purge_modules()
        batch.load_modules(softwares)

        for xml in bucket:
            outdir, h5master, sample, num_images = _get_dataset_params(proj, xml)

            os.makedirs(outdir, mode=0o760, exist_ok=True)

            if options["spacegroup"] != "":
                spacegroup = options["spacegroup"]
                spg = f"symm='{spacegroup}'"
            else:
                spg = ""
            if options["cellparam"] != "":
                cellpar = " ".join(options["cellparam"].split(","))
                cellpar = cellpar.replace("(", "").replace(")", "")
                unit_cell = f"cell='{cellpar}'"
            else:
                unit_cell = ""

            customautoproc = options["customautoproc"]
            if options["friedel_law"] == "true":
                friedel = "-ANO"
            else:
                friedel = "-noANO"

            batch.add_commands(
                f"rm -rf {outdir}/autoproc",
                f"mkdir -p {outdir}",
                f"cd {outdir}",
                f"process -h5 {h5master} {friedel} {spg} {unit_cell} "
                f"""autoPROC_Img2Xds_UseXdsPlugins_DectrisHdf5="durin-plugin" """
                f"""autoPROC_XdsKeyword_LIB=\\$EBROOTDURIN/lib/durin-plugin.so """
                f"""autoPROC_XdsKeyword_ROTATION_AXIS='0  -1 0' autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_JOBS=1 """
                f"""autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_PROCESSORS=64 autoPROC_XdsKeyword_DATA_RANGE=1\\ """
                f"""{num_images} autoPROC_XdsKeyword_SPOT_RANGE=1\\ {num_images} {customautoproc} """
                f"-d {outdir}/autoproc"
            )

            add_update_status_script_cmds(proj, sample, batch, softwares)

        batch.save()
        hpc.run_batch(script_file_path)


def run_xds(proj, nodes, filters, options):
    # atom=X
    # Tell xia2 to separate anomalous pairs i.e. I(+) ≠ I(−) in scaling.
    # pipeline=3d
    # Tell xia2 to use XDS and XSCALE.
    # pipeline=3dii
    # Tell xia2 to use XDS and XSCALE, indexing with peaks found from all images.
    # pipeline=dials
    # Tell xia2 to use DIALS.
    # pipeline=dials-aimless
    # Tell xia2 to use DIALS but scale with Aimless.
    # xinfo=some.xinfo
    # Use specific modified .xinfo input file.
    # image=/path/to/an/image.img
    # Process a specific scan.
    # Pass multiple image= parameters to include multiple scans.
    # image=/path/to/an/image.img:start:end
    # Process a specific image range within a scan. start and end are numbers denoting the image range, e.g.
    # image=/path/to/an/image.img:1:100 processes images 1–100 inclusive.
    # As above, one can pass multiple image= parameters.
    # small_molecule=true
    # Process in manner more suited to small molecule data.
    # space_group=sg
    # Set the spacegroup, e.g. P21.
    # unit_cell=a,b,c,α,β,γ
    # Set the cell constants.

    # Modules list for HPC env
    softwares = ["gopresto", versions.XDS_MOD, versions.DIALS_MOD]

    hpc = SITE.get_hpc_runner()
    epoch = str(round(time.time()))

    xml_files = list(get_xml_files(proj, get_proc_datasets(proj, filters)))
    for num, bucket in enumerate(_as_buckets(xml_files, nodes)):
        script_file_path = project_script(proj, f"xdsxscale_fragmax_part{num}.sh")
        batch = hpc.new_batch_file(script_file_path)

        batch.set_options(time=Duration(hours=168), job_name="XIA2/XDS", exclusive=True, nodes=1,
                          cpus_per_task=64, partition="fujitsu", memory=DataSize(gigabyte=300),
                          stdout=project_log_path(proj, f"multi_xia2XDS_{epoch}_%j_out.txt"),
                          stderr=project_log_path(proj, f"multi_xia2XDS_{epoch}_%j_err.txt"))

        batch.purge_modules()
        batch.load_modules(softwares)

        for xml in bucket:
            outdir, h5master, sample, num_images = _get_dataset_params(proj, xml)

            os.makedirs(outdir, mode=0o760, exist_ok=True)
            os.makedirs(outdir + "/xdsxscale", mode=0o760, exist_ok=True)

            if options["spacegroup"] != "":
                spacegroup = options["spacegroup"]
                spg = f"space_group={spacegroup}"
            else:
                spg = ""
            if options["cellparam"] != "":
                cellpar = ",".join(options["cellparam"].split(","))
                unit_cell = f"unit_cell={cellpar}"
            else:
                unit_cell = ""
            customxds = options["customxds"]

            if options["friedel_law"] == "true":
                friedel = "atom=X"
            else:
                friedel = ""

            batch.add_commands(
                f"mkdir -p {outdir}/xdsxscale",
                f"cd {outdir}/xdsxscale",
                f"xia2 goniometer.axes=0,1,0  pipeline=3dii failover=true {spg} {unit_cell} {customxds} "
                f"nproc=64 {friedel} image={h5master}:1:{num_images} "
                f"multiprocessing.mode=serial multiprocessing.njob=1"
            )

            add_update_status_script_cmds(proj, sample, batch, softwares)

        batch.save()
        hpc.run_batch(script_file_path)


def run_dials(proj, nodes, filters, options):
    # atom=X
    # Tell xia2 to separate anomalous pairs i.e. I(+) ≠ I(−) in scaling.
    # pipeline=3d
    # Tell xia2 to use XDS and XSCALE.
    # pipeline=3dii
    # Tell xia2 to use XDS and XSCALE, indexing with peaks found from all images.
    # pipeline=dials
    # Tell xia2 to use DIALS.
    # pipeline=dials-aimless
    # Tell xia2 to use DIALS but scale with Aimless.
    # xinfo=some.xinfo
    # Use specific modified .xinfo input file.
    # image=/path/to/an/image.img
    # Process a specific scan.
    # Pass multiple image= parameters to include multiple scans.
    # image=/path/to/an/image.img:start:end
    # Process a specific image range within a scan. start and end are numbers denoting the image range, e.g.
    # image=/path/to/an/image.img:1:100 processes images 1–100 inclusive.
    # As above, one can pass multiple image= parameters.
    # small_molecule=true
    # Process in manner more suited to small molecule data.
    # space_group=sg
    # Set the spacegroup, e.g. P21.
    # unit_cell=a,b,c,α,β,γ
    # Set the cell constants.

    # Modules list for HPC env
    softwares = ["gopresto", versions.DIALS_MOD]

    hpc = SITE.get_hpc_runner()
    epoch = str(round(time.time()))

    xml_files = list(get_xml_files(proj, get_proc_datasets(proj, filters)))
    for num, bucket in enumerate(_as_buckets(xml_files, nodes)):
        script_file_path = project_script(proj, f"dials_fragmax_part{num}.sh")
        batch = hpc.new_batch_file(script_file_path)

        batch.set_options(time=Duration(hours=168), job_name="DIALS", exclusive=True, nodes=1,
                          cpus_per_task=64, partition="fujitsu", memory=DataSize(gigabyte=300),
                          stdout=project_log_path(proj, f"multi_xia2DIALS_{epoch}_%j_out.txt"),
                          stderr=project_log_path(proj, f"multi_xia2DIALS_{epoch}_%j_err.txt"))

        batch.purge_modules()
        batch.load_modules(softwares)

        for xml in bucket:
            outdir, h5master, sample, num_images = _get_dataset_params(proj, xml)

            os.makedirs(outdir, mode=0o760, exist_ok=True)
            os.makedirs(outdir + "/dials", mode=0o760, exist_ok=True)

            if options["spacegroup"] != "":
                spacegroup = options["spacegroup"]
                spg = f"space_group={spacegroup}"
            else:
                spg = ""
            if options["cellparam"] != "":
                cellpar = ",".join(options["cellparam"].split(","))
                cellpar = cellpar.replace("(", "").replace(")", "")
                unit_cell = f"unit_cell={cellpar}"
            else:
                unit_cell = ""
            customdials = options["customdials"]

            if options["friedel_law"] == "true":
                friedel = "atom=X"
            else:
                friedel = ""

            batch.add_commands(
                f"mkdir -p {outdir}/dials",
                f"cd {outdir}/dials",
                f"xia2 goniometer.axes=0,1,0 pipeline=dials failover=true {spg} {unit_cell} {customdials} "
                f"nproc=64 {friedel} image={h5master}:1:{num_images} "
                f"multiprocessing.mode=serial multiprocessing.njob=1")

            add_update_status_script_cmds(proj, sample, batch, softwares)

        batch.save()
        hpc.run_batch(script_file_path)
