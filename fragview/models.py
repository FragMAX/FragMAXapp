




class Project(models.Model):
    protein = models.TextField()
    library = models.TextField()
    proposal = models.TextField()
    shift = models.TextField()
    shift_list = models.TextField(blank=True)

    @staticmethod
    def user_projects():
        # for now, just return all projects,
        # TODO: only return projects that the current
        # TODO: user have access to
        return Project.objects.all()
