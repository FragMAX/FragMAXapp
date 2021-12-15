from typing import Iterable, Optional
import binascii
from base64 import b64encode, b64decode
from django.contrib.auth.models import AbstractBaseUser
from django.conf import settings
from fragview import encryption
from fragview.projects import Project, get_project
from fragview.encryption import generate_token, now_utc
from django.db.models import (
    Model,
    CharField,
    TextField,
    ForeignKey,
    BooleanField,
    BinaryField,
    DateTimeField,
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
            yield get_project(settings.PROJECTS_DB_DIR, user_proj.id)

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


class AccessToken(Model):
    class ParseError(Exception):
        pass

    # project = models.ForeignKey(Project, on_delete=models.CASCADE)
    project_id = TextField()
    token = BinaryField(max_length=encryption.TOKEN_SIZE)
    valid_until = DateTimeField()

    def is_valid(self, now=None) -> bool:
        if now is None:
            now = now_utc()

        return self.valid_until > now

    @staticmethod
    def _token_by_proj_id(project_id: str):
        return AccessToken.objects.filter(project_id=project_id)

    @staticmethod
    def _purge_old_tokens(project_id: str):
        now = now_utc()

        for token in AccessToken._token_by_proj_id(project_id):
            if not token.is_valid(now):
                token.delete()

    @staticmethod
    def get_project_token(project_id: str) -> Optional["AccessToken"]:
        AccessToken._purge_old_tokens(project_id)
        return AccessToken._token_by_proj_id(project_id).first()

    @staticmethod
    def create_new(project_id: str) -> "AccessToken":
        tok, valid_until = generate_token()
        return AccessToken.objects.create(
            project_id=project_id, token=tok, valid_until=valid_until
        )

    @staticmethod
    def get_from_base64(b64_token):
        try:
            tok = b64decode(b64_token)
        except (binascii.Error, ValueError):
            # could not parse base64 string
            raise AccessToken.ParseError()

        token = AccessToken.objects.get(token=tok)
        if token is None or not token.is_valid():
            return None

        return token

    def as_base64(self):
        """
        get this token as base64 encoded string
        """
        return b64encode(self.token).decode()


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
        # User Project class methods for fetching all projects, so that
        # we only give access to project's included into current proposals
        # list.
        #

        cur_proj = _get_current_project()

        if cur_proj is None:
            return next(UserProject.user_projects(proposals), None)

        return get_project(settings.PROJECTS_DB_DIR, cur_proj.id)

    def set_current_project(self, new_current_proj: UserProject):
        self.current_project = new_current_proj
        self.save()

    def have_pending_projects(self, proposals):
        for proj in PendingProject.get_projects():
            if proj.proposal in proposals:
                return True

        # no pending project for the user found
        return False
