import base64
from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from .projects import shift_dir, project_model_file
from . import encryption


class Library(models.Model):
    """
    Fragments Library
    """
    # public libraries are available to all projects
    name = models.TextField()

    @staticmethod
    def get(lib_id):
        """
        get library by ID
        """
        return Library.objects.get(id=lib_id)

    def get_fragment(self, fragment_name):
        fragment = self.fragment_set.filter(name=fragment_name)
        if not fragment.exists():
            return None

        return fragment.first()


class Fragment(models.Model):
    library = models.ForeignKey(Library, on_delete=models.CASCADE)
    name = models.TextField()
    # chemical structure of the fragment, in SMILES format
    smiles = models.TextField()


class Project(models.Model):
    # number of unique project icons available
    PROJ_ICONS_NUMBER = 10

    protein = models.TextField()
    library = models.ForeignKey(Library, on_delete=models.CASCADE)
    proposal = models.TextField()
    shift = models.TextField()
    shift_list = models.TextField(blank=True)
    # 'encrypted mode' for data processing is enabled
    encrypted = models.BooleanField(default=False)

    @staticmethod
    def get(proj_id):
        """
        get project by ID
        """
        return Project.objects.get(id=proj_id)

    @staticmethod
    def user_projects(user_proposals):
        pending_ids = PendingProject.get_project_ids()
        return Project.objects.filter(proposal__in=user_proposals).exclude(id__in=pending_ids)

    @staticmethod
    def get_project(user_proposals, project_id):
        usr_proj = Project.user_projects(user_proposals)
        return usr_proj.filter(id=project_id).first()

    def set_ready(self):
        PendingProject.remove_pending(self)

    def set_pending(self):
        PendingProject(project=self).save()

    def icon_num(self):
        return self.id % self.PROJ_ICONS_NUMBER

    def data_path(self):
        return shift_dir(self.proposal, self.shift)

    def shifts(self):
        """
        get all shifts for this project, both the 'main' shift
        and any additional shifts if specified
        """

        # split the shift list on ',' and filter our any
        # potentially empty string that split generates
        aditional_shifts = [s for s in self.shift_list.split(",") if s]

        # create a union set between main shift and additional shifts,
        # to handle the case where same shift is listed multiple times
        all_shifts = set(aditional_shifts).union([self.shift])

        return list(all_shifts)

    def has_encryption_key(self):
        """
        convenience wrapper to check if this project have an encryption key uploaded
        """
        return self.encryption_key is not None

    @property
    def encryption_key(self):
        """
        convenience wrapper to get project's encryption key,
        if no key is uploaded, None is returned
        """
        return getattr(self, "encryptionkey", None)


class PendingProject(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, primary_key=True)

    @staticmethod
    def remove_pending(project):
        pend = PendingProject.objects.filter(project=project.id)
        if not pend.exists():
            print(f"warning: project {project.id} not pending, ignoring request to remove pending state")
            return

        pend.first().delete()

    @staticmethod
    def get_projects():
        """
        get pending projects, a list of Project objects
        """
        return [pend.project for pend in PendingProject.objects.all()]

    @staticmethod
    def get_project_ids():
        """
        get pending projects IDs
        """
        return [pend.project.id for pend in PendingProject.objects.all()]


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

    def have_pending_projects(self, proposals):
        for proj in PendingProject.get_projects():
            if proj.proposal in proposals:
                return True

        # no pending project for the user found
        return False


class PDB(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    filename = models.TextField()
    # the official PDB ID, as assigned by Protein Data Bank organization
    pdb_id = models.CharField(max_length=4)

    class Meta:
        unique_together = (("project", "filename"),)

    @staticmethod
    def get(id):
        """
        get PDB by our internal database ID
        """
        return PDB.objects.get(id=id)

    @staticmethod
    def project_pdbs(project):
        """
        fetch PDBs for the specified project
        """
        return PDB.objects.filter(project=project)

    def file_path(self):
        """
        returns full path to the PDB file in the 'fragmax' project directory
        """
        return project_model_file(self.project, self.filename)


class EncryptionKey(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, primary_key=True)
    key = models.BinaryField(max_length=encryption.KEY_SIZE)

    def as_base64(self):
        """
        get this encryption key as base64 encoded string
        """
        return base64.b64encode(self.key).decode()

    @staticmethod
    def from_base64(proj, b64_key):
        """
        create EncryptionKey model object from base64 encoded key
        """
        bin_key = base64.b64decode(b64_key)
        return EncryptionKey(project=proj, key=bin_key)


class AccessToken(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    token = models.BinaryField(max_length=encryption.TOKEN_SIZE)
    # TODO: add 'expiration time', e.g. time after which the token is no longer valid

    @staticmethod
    def add_token(project, token):
        tok = AccessToken(project=project, token=token)
        tok.save()

        return tok

    @staticmethod
    def get_from_base64(b64_token):
        tok = base64.b64decode(b64_token)
        return AccessToken.objects.get(token=tok)

    def as_base64(self):
        """
        get this token as base64 encoded string
        """
        return base64.b64encode(self.token).decode()


class ProjectDetails(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    protein_name = models.TextField()
    # the official PDB ID, as assigned by Protein Data Bank organization
    group_dep_id = models.TextField()


class HZB_user_details(models.Model):
    username = models.TextField()
    password = models.TextField()