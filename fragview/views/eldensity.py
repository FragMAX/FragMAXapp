from pathlib import Path
from fragview.views.utils import download_http_response, get_refine_result_by_id
from fragview.projects import current_project


def _density_filename(name, type):
    if type == "nat":
        return f"{name}_2mFo-DFc.ccp4"
    elif type == "mtz":
        return f"{name}.mtz"
    assert type == "dif"
    return f"{name}_mFo-DFc.ccp4"


def refined_map(request, result_id, type):
    project = current_project(request)
    result = get_refine_result_by_id(project, result_id)
    mtz_path = Path(
        project.get_refine_result_dir(result), _density_filename("final", type)
    )

    return download_http_response(mtz_path, f"{result.name}{mtz_path.suffix}")
