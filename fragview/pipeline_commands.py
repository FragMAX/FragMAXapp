from fragview.sites import SITE


def _get_pipe_cmds():
    return SITE.get_pipeline_commands()


def get_xia_dials_commands(
    space_group, unit_cell, custom_parameters, friedel, image_file, num_images
):
    return _get_pipe_cmds().get_xia_dials_commands(
        space_group, unit_cell, custom_parameters, friedel, image_file, num_images
    )


def get_xia_xdsxscale_commands(
    space_group, unit_cell, custom_parameters, friedel, image_file, num_images
):
    return _get_pipe_cmds().get_xia_xdsxscale_commands(
        space_group, unit_cell, custom_parameters, friedel, image_file, num_images
    )


def get_xdsapp_command(
    output_dir, space_group, custom_parameters, friedel, image_file, num_images
):
    return _get_pipe_cmds().get_xdsapp_command(
        output_dir, space_group, custom_parameters, friedel, image_file, num_images
    )


def get_autoproc_command(
    output_dir,
    space_group,
    unit_cell,
    custom_parameters,
    friedel,
    image_file,
    num_images,
):
    return _get_pipe_cmds().get_autoproc_command(
        output_dir,
        space_group,
        unit_cell,
        custom_parameters,
        friedel,
        image_file,
        num_images,
    )


def get_dimple_command(dstmtz, custom_parameters):
    return _get_pipe_cmds().get_dimple_command(dstmtz, custom_parameters)


def get_fspipeline_command(pdb, custom_parameters):
    return _get_pipe_cmds().get_fspipeline_command(pdb, custom_parameters)


def get_buster_command(dstmtz, pdb, custom_parameters):
    return _get_pipe_cmds().get_buster_command(dstmtz, pdb, custom_parameters)
