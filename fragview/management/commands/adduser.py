import getpass
from django.core.management.base import BaseCommand, CommandError
from fragview.models import User


class Command(BaseCommand):
    help = "add local FragMAX user"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)

    def handle(self, *args, **options):
        username = options["username"]

        if User.objects.filter(username=username).exists():
            raise CommandError(f"user {username} already exist")

        try:
            passwd = getpass.getpass(prompt="Password: ")
        except (KeyboardInterrupt, EOFError):
            # user aborted password input
            return

        usr = User(username=username)
        usr.set_password(passwd)
        usr.save()

        print(f"user '{username}' added")
