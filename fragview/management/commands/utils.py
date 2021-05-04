from django.core.management.base import CommandError
from django.conf import settings
from fragview import projects
from fragview.projects import Project, ProjectNotFound


def get_project(project_id) -> Project:
    """
    returns project's model object,
    or raises CommandError exception if no project
    with specified ID exists
    """
    try:
        return projects.get_project(settings.PROJECTS_DB_DIR, project_id)
    except ProjectNotFound:
        raise CommandError(f"no project with ID '{project_id}' exist")
