from fragview.sites import plugin


class PipelineCommands(plugin.PipelineCommands):
    def get_xia_dials_command(
        self, space_group, unit_cell, custom_parameters, friedel, image_file, num_images
    ):
        return (
            f"xia2 goniometer.axes=0,1,0 pipeline=dials failover=true {space_group} {unit_cell} {custom_parameters} "
            f"nproc=64 {friedel} image={image_file}:1:{num_images} multiprocessing.mode=serial multiprocessing.njob=1"
        )

    def get_xia_xdsxscale_command(
        self, space_group, unit_cell, custom_parameters, friedel, image_file, num_images
    ):
        return (
            f"xia2 goniometer.axes=0,1,0  pipeline=3dii failover=true {space_group} {unit_cell} {custom_parameters} "
            f"nproc=64 {friedel} image={image_file}:1:{num_images} multiprocessing.mode=serial multiprocessing.njob=1"
        )

    def get_xdsapp_command(
        self,
        output_dir,
        space_group,
        custom_parameters,
        friedel,
        image_file,
        num_images,
    ):
        return (
            f"xdsapp --cmd --dir={output_dir}/xdsapp -j 1 -c 64 -i {image_file} {space_group} "
            f"{custom_parameters} --delphi=10 {friedel} --range=1\\ {num_images}"
        )

    def get_autoproc_command(
        self,
        output_dir,
        space_group,
        unit_cell,
        custom_parameters,
        friedel,
        image_file,
        num_images,
    ):
        return (
            f"process -h5 {image_file} {friedel} {space_group} {unit_cell} "
            'autoPROC_Img2Xds_UseXdsPlugins_DectrisHdf5="durin-plugin" '
            "autoPROC_XdsKeyword_LIB=\\$EBROOTDURIN/lib/durin-plugin.so "
            "autoPROC_XdsKeyword_ROTATION_AXIS='0  -1 0' autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_JOBS=1 "
            "autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_PROCESSORS=64 autoPROC_XdsKeyword_DATA_RANGE=1\\ "
            f"{num_images} autoPROC_XdsKeyword_SPOT_RANGE=1\\ {num_images} {custom_parameters} -d {output_dir}/autoproc"
        )

    def get_dimple_command(self, dstmtz, custom_parameters):
        return f"dimple {dstmtz} model.pdb dimple {custom_parameters}"

    def get_fspipeline_command(self, pdb, custom_parameters):
        return (
            f"python /mxn/groups/biomax/wmxsoft/fspipeline/fspipeline.py --sa=false --refine={pdb} "
            f'--exclude="dimple fspipeline buster unmerged rhofit ligfit truncate" --cpu=2 {custom_parameters}'
        )

    def get_buster_command(self, dstmtz, pdb, custom_parameters):
        srcmtz = dstmtz
        dstmtz = dstmtz.replace("merged", "truncate")
        outdir = "/".join(dstmtz.split("/")[:-1])

        return (
            f'echo "truncate yes \\labout F=FP SIGF=SIGFP" | truncate hklin {srcmtz} hklout {dstmtz} '
            f"| tee {outdir} truncate.log\n"
            f"refine -L -p {pdb} -m {dstmtz} {custom_parameters} -TLS -nthreads 2 "
            f"StopOnGellySanityCheckError=no -d {outdir} buster\n"
        )