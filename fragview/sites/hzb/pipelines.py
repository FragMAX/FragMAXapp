from fragview.sites import plugin


class PipelineCommands(plugin.PipelineCommands):
    def get_xia_dials_command(
        self, space_group, unit_cell, custom_parameters, friedel, image_file, num_images
    ):
        return (
            f"xia2 pipeline=dials failover=true {space_group} {unit_cell} {custom_parameters} "
            f"nproc=40 {friedel} image={image_file}:1:{num_images} "
            f"multiprocessing.mode=serial multiprocessing.njob=1 multiprocessing.nproc=40"
        )

    def get_xia_xdsxscale_command(
        self, space_group, unit_cell, custom_parameters, friedel, image_file, num_images
    ):
        return (
            f"xia2 pipeline=3dii failover=true {space_group} {unit_cell} {custom_parameters} "
            f"nproc=40 {friedel} image={image_file}:1:{num_images} "
            f"multiprocessing.mode=serial multiprocessing.njob=1 multiprocessing.nproc=40"
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
            f"/usr/bin/python2 /soft/pxsoft/run/xdsit/options.py --cmd --dir={output_dir}/xdsapp -j 8 -c 8 -i "
            f"{image_file} {space_group} {custom_parameters} {friedel} --range='1 {num_images}'"
        )

    def get_dimple_command(self, dstmtz, custom_parameters):
        return f"dimple {dstmtz} model.pdb dimple {custom_parameters}"

    def get_fspipeline_command(self, pdb, custom_parameters):
        return (
            f"/soft/pxsoft/64/pymol_2.1/bin/python /frag/fragmax/fm_bessy/fspipeline.py --sa=false --refine={pdb} "
            f'--exclude="dimple fspipeline buster unmerged rhofit ligfit truncate" --cpu=1 {custom_parameters}'
        )
