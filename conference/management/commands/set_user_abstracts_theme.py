from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from conference.models import AbstractSubmission, ScientificTheme, Participant

User = get_user_model()


class Command(BaseCommand):
    help = "Set all abstracts for a user to the user's registered scientific theme."

    def add_arguments(self, parser):
        parser.add_argument('--username', help='User username to target')
        parser.add_argument('--email', help='User email to target')
        parser.add_argument('--full-name', help='Full name (First Last) to target')
        parser.add_argument('--dry-run', action='store_true', help='Show changes without saving')

    def handle(self, *args, **options):
        username = options.get('username')
        email = options.get('email')
        full_name = options.get('full_name')
        dry = options.get('dry_run')

        users_qs = User.objects.none()

        if username:
            users_qs = User.objects.filter(username__iexact=username)
        elif email:
            users_qs = User.objects.filter(email__iexact=email)
        elif full_name:
            parts = full_name.strip().split()
            if len(parts) >= 2:
                first, last = parts[0], parts[-1]
                users_qs = User.objects.filter(first_name__iexact=first, last_name__iexact=last)
            else:
                users_qs = User.objects.filter(first_name__iexact=full_name.strip())
        else:
            self.stdout.write(self.style.ERROR('Please supply --username or --email or --full-name'))
            return

        total_users = users_qs.count()
        if total_users == 0:
            self.stdout.write(self.style.ERROR('No matching user found'))
            return
        if total_users > 1:
            self.stdout.write(self.style.WARNING(f'Multiple users matched ({total_users}); processing all matches'))

        total_changed = 0
        total_skipped = 0
        for user in users_qs:
            try:
                participant = user.participant
            except Participant.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'User {user.username} has no Participant record; skipping'))
                total_skipped += 1
                continue

            theme_code = (participant.scientific_theme or '').strip()
            if not theme_code:
                self.stdout.write(self.style.WARNING(f'User {user.username} participant has no scientific_theme set; skipping'))
                total_skipped += 1
                continue

            theme_obj = ScientificTheme.objects.filter(code=theme_code).first()
            if not theme_obj:
                self.stdout.write(self.style.WARNING(f'User {user.username} theme code "{theme_code}" not found in ScientificTheme; skipping'))
                total_skipped += 1
                continue

            abstracts = AbstractSubmission.objects.filter(user=user)
            if not abstracts.exists():
                self.stdout.write(self.style.NOTICE(f'User {user.username} has no abstracts; skipping'))
                continue

            changed = 0
            # Use queryset update to avoid model full_clean validation that may require files
            to_update = abstracts.exclude(theme_id=theme_obj.id)
            if to_update.exists():
                for abs in to_update:
                    self.stdout.write(f"Would update abstract id={abs.id} title='{abs.title}' from theme_id={abs.theme_id} to {theme_obj.id}") if dry else None
                if not dry:
                    updated_count = to_update.update(theme=theme_obj)
                    changed += updated_count
            if changed:
                self.stdout.write(self.style.SUCCESS(f'Updated {changed} abstracts for user {user.username}'))
            else:
                self.stdout.write(self.style.NOTICE(f'No abstracts needed update for user {user.username}'))

            total_changed += changed

        self.stdout.write(self.style.SUCCESS(f'Done. Total abstracts updated: {total_changed}. Total skipped users: {total_skipped}'))
