from django.core.management.base import CommandError
from fragview.models import Project


def get_project(project_id):
    """
    returns project's model object,
    or raises CommandError exception if no project
    with specified ID exists
    """
    try:
        return Project.get(project_id)
    except Project.DoesNotExist:
        raise CommandError(f"no project with ID '{project_id}' exist")
