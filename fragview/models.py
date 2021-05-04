from django.contrib.auth.models import AbstractBaseUser
from fragview.projects import Project, get_project
from django.db.models import (
    Model,
    CharField,
    TextField,
    ForeignKey,
    BooleanField,
    OneToOneField,
    UniqueConstraint,
    SET_NULL,
    CASCADE,
)


class Library(Model):
    """
    Fragments Library
    """

    # public libraries are available to all projects
    name = TextField(unique=True)

    def get_fragments(self):
        return self.fragment_set.all()

    @staticmethod
    def get(library_name: str) -> "Library":
        return Library.objects.get(name=library_name)

    @staticmethod
    def get_by_id(library_id: str) -> "Library":
        return Library.objects.get(id=library_id)

    @staticmethod
    def get_all():
        return Library.objects.all()


class Fragment(Model):
    class Meta:
        constraints = [
            # enforce unique fragment codes inside same library
            UniqueConstraint(fields=["library", "code"], name="unique_codes")
        ]

    library = ForeignKey(Library, on_delete=CASCADE)
    code = TextField()

    # chemical structure of the fragment, in SMILES format
    smiles = TextField()

    @staticmethod
    def get(library_name: str, fragment_code: str) -> "Fragment":
        return Fragment.objects.get(
            library=Library.get(library_name), code=fragment_code
        )

    @staticmethod
    def get_by_id(fragment_id: str) -> "Fragment":
        return Fragment.objects.get(id=fragment_id)


class UserProject(Model):
    proposal = CharField(max_length=32)

    # 'encrypted mode' for data processing is enabled
    encrypted = BooleanField(default=False)

    @staticmethod
    def get_project(user_proposals, project_id):
        return UserProject.objects.filter(
            proposal__in=user_proposals, id=project_id
        ).first()

    @staticmethod
    def user_projects(user_proposals):
        pending_ids = PendingProject.get_project_ids()
        for user_proj in UserProject.objects.filter(
            proposal__in=user_proposals
        ).exclude(id__in=pending_ids):
            yield get_project(user_proj.id)

    def set_pending(self):
        PendingProject(project=self).save()

    def set_ready(self):
        PendingProject.remove_pending(self)


class PendingProject(Model):
    project = OneToOneField(UserProject, on_delete=CASCADE, primary_key=True)

    @staticmethod
    def remove_pending(project):
        pend = PendingProject.objects.filter(project=project.id)
        if not pend.exists():
            print(
                f"warning: project {project.id} not pending, ignoring request to remove pending state"
            )
            return

        pend.first().delete()

    @staticmethod
    def get_projects():
        """
        get pending projects, a list of Project objects
        """
        return [get_project(pend.project.id) for pend in PendingProject.objects.all()]

    @staticmethod
    def get_project_ids():
        """
        get pending projects IDs
        """
        return [pend.project.id for pend in PendingProject.objects.all()]


class User(AbstractBaseUser):
    username = CharField(max_length=150, unique=True)
    current_project = ForeignKey(UserProject, null=True, on_delete=SET_NULL)

    USERNAME_FIELD = "username"

    # def set_current_project(self, new_current_proj):
    #     self.current_project = new_current_proj
    #     self.save()
    #
    def get_current_project(self, proposals) -> Project:
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
            cur_proj = self.current_project

        if cur_proj is None:
            return next(UserProject.user_projects(proposals), None)

        return get_project(cur_proj.id)

    def set_current_project(self, new_current_proj):
        self.current_project = new_current_proj
        self.save()

    def have_pending_projects(self, proposals):
        for proj in PendingProject.get_projects():
            if proj.proposal in proposals:
                return True

        # no pending project for the user found
        return False
