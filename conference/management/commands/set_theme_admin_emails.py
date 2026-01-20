from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from conference.models import ThemeAdmin

User = get_user_model()


class Command(BaseCommand):
    help = "Set ThemeAdmin user emails and passwords based on their assigned theme. Local-part can be generated from theme code, id, name or slug."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show actions without saving')
        parser.add_argument('--password', default='theme123', help='Password to set for the users')
        parser.add_argument('--domain', default='test.com', help='Domain to use for generated emails')
        parser.add_argument('--format', choices=['code', 'id', 'name', 'slug'], default='slug', help='Format to use for local-part')

    def handle(self, *args, **options):
        dry = options['dry_run']
        password = options['password']
        domain = options['domain']
        fmt = options['format']

        updated = 0
        skipped = 0

        for ta in ThemeAdmin.objects.select_related('user').prefetch_related('themes').all():
            user = ta.user
            if user.is_superuser:
                self.stdout.write(self.style.WARNING(f"Skipping superuser {user.username}"))
                skipped += 1
                continue

            theme = ta.themes.first()
            if not theme:
                self.stdout.write(self.style.WARNING(f"ThemeAdmin(id={ta.id}, user={user.username}) has no themes; skipping"))
                skipped += 1
                continue

            if fmt == 'code' and getattr(theme, 'code', None):
                local = str(theme.code)
            elif fmt == 'id':
                local = str(theme.id)
            elif fmt == 'name':
                # unsafe raw name; will replace spaces with dots
                local = str(theme.name).lower().replace(' ', '.')
            else:  # slug
                local = slugify(str(theme.name)) or f"theme{theme.id}"

            new_email = f"{local}@{domain}"

            if dry:
                self.stdout.write(f"[DRY] Would set user={user.username} email={new_email} password={password}")
                continue

            # Apply changes
            user.email = new_email
            user.set_password(password)
            user.is_staff = True
            user.save()
            updated += 1
            self.stdout.write(self.style.SUCCESS(f"Updated user {user.username} -> {new_email}"))

        self.stdout.write(self.style.SUCCESS(f"Finished. {updated} users updated, {skipped} skipped."))
