from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from conference.models import ThemeAdmin

User = get_user_model()


class Command(BaseCommand):
    help = "Delete or deactivate a ThemeAdmin by user email or username."

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True, help='User email or username for the ThemeAdmin to remove')
        parser.add_argument('--soft', action='store_true', help='Soft-delete: deactivate ThemeAdmin and revoke staff access instead of deleting user')
        parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')

    def handle(self, *args, **options):
        identifier = options['email']
        soft = options['soft']
        skip = options['yes']

        user = User.objects.filter(email=identifier).first() or User.objects.filter(username=identifier).first()
        if not user:
            raise CommandError(f"No user found for '{identifier}'")

        theme_admin = ThemeAdmin.objects.filter(user=user).first()
        if not theme_admin:
            raise CommandError(f"User '{user.username}' is not a ThemeAdmin.")

        # Show summary
        self.stdout.write("Found ThemeAdmin:")
        self.stdout.write(f"  username: {user.username}")
        self.stdout.write(f"  email: {user.email}")
        themes = list(theme_admin.themes.all())
        if themes:
            self.stdout.write("  themes: " + ", ".join([t.name for t in themes]))
        else:
            self.stdout.write("  themes: (none)")
        self.stdout.write(f"  is_active: {theme_admin.is_active}")

        if not skip:
            confirm = input(f"Proceed to {'deactivate' if soft else 'delete'} this ThemeAdmin and user '{user.username}'? [y/N]: ")
            if confirm.lower() != 'y':
                self.stdout.write(self.style.WARNING('Aborted.'))
                return

        if soft:
            # Deactivate ThemeAdmin, revoke staff
            theme_admin.is_active = False
            theme_admin.save()
            user.is_staff = False
            user.save()
            self.stdout.write(self.style.SUCCESS(f"ThemeAdmin for '{user.username}' deactivated and staff access revoked."))
        else:
            # Delete ThemeAdmin then user
            theme_admin.delete()
            user.delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted ThemeAdmin and user '{identifier}'."))
