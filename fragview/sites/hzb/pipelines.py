from fragview.sites import plugin


class PipelineCommands(plugin.PipelineCommands):
    def get_xia_dials_commands(
        self, space_group, unit_cell, custom_parameters, friedel, image_file, num_images
    ):
        return [
            "source /soft/pxsoft/64/ccp4/ccp4-7.1/ccp4-7.1/bin/ccp4.setup-csh",
            f"xia2 pipeline=dials failover=true {space_group} {unit_cell} {custom_parameters} "
            f"nproc=40 {friedel} image={image_file}:1:{num_images} "
            f"multiprocessing.mode=serial multiprocessing.njob=1 multiprocessing.nproc=40",
        ]

    def get_xia_xdsxscale_commands(
        self, space_group, unit_cell, custom_parameters, friedel, image_file, num_images
    ):
        return [
            "source /soft/pxsoft/64/ccp4/ccp4-7.1/ccp4-7.1/bin/ccp4.setup-csh",
            f"xia2 pipeline=3dii failover=true {space_group} {unit_cell} {custom_parameters} "
            f"nproc=40 {friedel} image={image_file}:1:{num_images} "
            f"multiprocessing.mode=serial multiprocessing.njob=1 multiprocessing.nproc=40",
        ]

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
            f"/soft/pxsoft/run/xdsit/xdsappbeta/xdsit.py --image={image_file} --range='1 {num_images}' "
            f"{friedel} --dir={output_dir}/xdsapp  --jobs=8 --cpu=8"
        )

    def get_dimple_command(self, dstmtz, custom_parameters):
        return f"dimple {dstmtz} model.pdb dimple {custom_parameters}"

    def get_fspipeline_commands(self, pdb, custom_parameters):
        return [
            f"/soft/pxsoft/64/pymol_2.1/bin/python /frag/fragmax/fm_bessy/fspipeline.py --sa=false --refine={pdb} "
            f'--exclude="dimple fspipeline buster unmerged rhofit ligfit truncate" --cpu=1 {custom_parameters}',
        ]
