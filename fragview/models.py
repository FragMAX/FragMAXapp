from typing import Iterable, Optional, Dict
from django.contrib.auth.models import AbstractBaseUser
from fragview.projects import Project, get_project
from django.db.models import (
    Q,
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
    name = TextField()
    constraints = [UniqueConstraint(fields=["name", "project_id"], name="unique_names")]

    #
    # used to mark project private library
    # is project_id is None - public library
    # otherwise it's a library private to the specified project
    #
    project_id = TextField(null=True)

    def get_fragments(self):
        return self.fragment_set.all()

    def as_dict(self) -> Dict[str, str]:
        frags = {}
        for frag in self.get_fragments():
            frags[frag.code] = frag.smiles

        return frags

    @staticmethod
    def get_by_name(project: Project, library_name: str) -> "Library":
        return Library.get_all(project).get(name=library_name)

    @staticmethod
    def get_by_id(project: Project, library_id: str) -> "Library":
        return Library.get_all(project).get(id=library_id)

    @staticmethod
    def get_all(project: Optional[Project] = None):
        # include all public libraries
        query = Q(project_id=None)

        if project is not None:
            # include private libraries, if project is specified
            query = query | Q(project_id=project.id)

        return Library.objects.filter(query)

    @staticmethod
    def get_all_private(project_id):
        return Library.objects.filter(project_id=project_id)


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
    def get(project: Project, library_name: str, fragment_code: str) -> "Fragment":
        return Fragment.objects.get(
            library=Library.get_by_name(project, library_name), code=fragment_code
        )

    @staticmethod
    def get_by_id(fragment_id: str) -> "Fragment":
        return Fragment.objects.get(id=fragment_id)


class UserProject(Model):
    proposal = CharField(max_length=32)

    # 'encrypted mode' for data processing is enabled
    encrypted = BooleanField(default=False)

    @staticmethod
    def get(project_id) -> "UserProject":
        """
        get project by ID
        """
        return UserProject.objects.get(id=project_id)

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

    @staticmethod
    def create_new(protein: str, proposal: str) -> "UserProject":
        """
        create new project, and set it in 'pending' state
        """
        proj = UserProject(proposal=proposal)
        proj.save()
        proj.set_pending(protein)

        return proj

    def is_pending(self) -> bool:
        return PendingProject.objects.filter(project=self).exists()

    def set_pending(self, protein: str):
        PendingProject(project=self, protein=protein).save()

    def set_ready(self):
        PendingProject.remove_pending(self)

    def set_failed(self, error_message: str):
        self.pendingproject.set_failed(error_message)


class PendingProject(Model):
    project = OneToOneField(UserProject, on_delete=CASCADE, primary_key=True)

    # temporary store protein name here, as the project's
    # backing database for the project will not exist
    # right away for new pending project
    protein = TextField()

    #
    # if set, then the set-up of the project have failed
    #
    error_message = TextField(null=True)

    def set_failed(self, error_message: str):
        self.error_message = error_message
        self.save()

    def failed(self) -> bool:
        return self.error_message is not None

    def name(self) -> str:
        """
        return a short name of the project, used in UI
        """
        return f"{self.protein} ({self.project.proposal})"

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
    def get_projects() -> Iterable[UserProject]:
        return [pend.project for pend in PendingProject.objects.all()]

    @staticmethod
    def get_all() -> Iterable["PendingProject"]:
        return PendingProject.objects.all()

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

    def get_current_project(self, proposals) -> Optional[Project]:
        """
        get user's currently selected project

        proposals - list of proposal number for this user
        """

        def _get_current_project() -> Optional[UserProject]:
            """
            Get currently selected project, if any.
            Takes care of filtering out 'current project' that is in pending state.
            """
            if self.current_project is None:
                return None

            if self.current_project.is_pending():
                return None

            return UserProject.get_project(proposals, self.current_project.id)

        #
        # if user object have selected current_project, use that
        # otherwise use one of the user's project.
        #
        # Use Project class methods for fetching all projects, so that
        # we only give access to project's included into current proposals
        # list.
        #

        cur_proj = _get_current_project()

        if cur_proj is None:
            return next(UserProject.user_projects(proposals), None)

        return get_project(cur_proj.id)

    def set_current_project(self, new_current_proj: UserProject):
        self.current_project = new_current_proj
        self.save()

    def have_pending_projects(self, proposals):
        for proj in PendingProject.get_projects():
            if proj.proposal in proposals:
                return True

        # no pending project for the user found
        return False
