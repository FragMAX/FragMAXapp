from fragview.sites import plugin


CCP4_INIT_FILE = "/soft/pxsoft/64/ccp4/ccp4-7.1/bin/ccp4.setup-csh"


class PipelineCommands(plugin.PipelineCommands):
    def get_xia_dials_commands(
        self, space_group, unit_cell, custom_parameters, friedel, image_file, num_images
    ):
        return (
            [
                f"source {CCP4_INIT_FILE}",
                f"xia2 pipeline=dials failover=true {space_group} {unit_cell} {custom_parameters} "
                f"nproc=16 {friedel} image={image_file}:1:{num_images} "
                f"multiprocessing.mode=serial multiprocessing.njob=1 multiprocessing.nproc=16",
            ],
            16,
        )

    def get_xia_xds_commands(
        self, space_group, unit_cell, custom_parameters, friedel, image_file, num_images
    ):
        return (
            [
                f"source {CCP4_INIT_FILE}",
                f"xia2 pipeline=3dii failover=true {space_group} {unit_cell} {custom_parameters} "
                f"nproc=16 {friedel} image={image_file}:1:{num_images} "
                f"multiprocessing.mode=serial multiprocessing.njob=1 multiprocessing.nproc=16",
            ],
            16,
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
            (
                f"/soft/pxsoft/64/xdsapp3/xdsit.py --image {image_file} {space_group} --range '1 {num_images}' "
                f"{custom_parameters} {friedel} --dir={output_dir}/xdsapp --jobs 1 --cpu 16"
            ),
            16,
        )

    def get_dimple_command(self, dstmtz, custom_parameters):
        return f"dimple {dstmtz} model.pdb dimple {custom_parameters}", 1

    def get_fspipeline_commands(self, pdb, custom_parameters):
        return (
            [
                'source "/soft/pxsoft/64/phenix/phenix-1.20.1-4487/phenix_env.csh"',
                f"/soft/pxsoft/64/anaconda3/bin/python /data/fragmaxbin/fspipeline/v20221121/fspipeline.py "
                f"--fragmaxapp --sa=false --refine={pdb} "
                f'--exclude="dimple fspipeline buster unmerged rhofit ligfit truncate" '
                f"--cpu=1 {custom_parameters}",
            ],
            1,
        )
