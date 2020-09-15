from fragview.sites import SITE


def _get_pipe_cmds():
    return SITE.get_pipeline_commands()


def get_xia_dials_command(
    space_group, unit_cell, custom_parameters, friedel, image_file, num_images
):
    return _get_pipe_cmds().get_xia_dials_command(
        space_group, unit_cell, custom_parameters, friedel, image_file, num_images
    )


def get_xia_xdsxscale_command(
    space_group, unit_cell, custom_parameters, friedel, image_file, num_images
):
    return _get_pipe_cmds().get_xia_xdsxscale_command(
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
