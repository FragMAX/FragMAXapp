from django.db import models
from django.contrib.auth.models import AbstractBaseUser


class Project(models.Model):
    protein = models.TextField()
    library = models.TextField()
    proposal = models.TextField()
    shift = models.TextField()
    shift_list = models.TextField(blank=True)

    @staticmethod
    def user_projects(user_proposals):
        return Project.objects.filter(proposal__in=user_proposals)

    @staticmethod
    def get_project(user_proposals, project_id):
        usr_proj = Project.user_projects(user_proposals)
        return usr_proj.filter(id=project_id).first()


class User(AbstractBaseUser):
    username = models.CharField(
        max_length=150,
        unique=True)

    current_project = models.ForeignKey(
        Project,
        null=True,
        on_delete=models.SET_NULL)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    def set_current_project(self, new_current_proj):
        self.current_project = new_current_proj
        self.save()

    def get_current_project(self, proposals):
        """
        get user's currently selected project

        proposals - list of proposal number for this user
        """
        cur_proj = None

        #
        # if user object have selected current_project, use that
        # otherwise use one of the user's project.
        #
        # User Project class methods for fetching all projects, so that
        # we only give access to project's included into current proposals
        # list.
        #

        if self.current_project is not None:
            cur_proj = Project.get_project(proposals, self.current_project.id)

        if cur_proj is None:
            cur_proj = Project.user_projects(proposals).first()

        return cur_proj
