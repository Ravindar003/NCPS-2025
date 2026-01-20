from django.core.management.base import BaseCommand
from conference.models import ThemeAdmin
import random


class Command(BaseCommand):
    help = "Ensure each ThemeAdmin has exactly one ScientificTheme assigned."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview changes without saving.')
        parser.add_argument('--strategy', choices=['first', 'random'], default='first', help='Which theme to keep when multiple exist.')
        parser.add_argument('--limit', type=int, help='Limit number of admins to process.')
        parser.add_argument('--exclude-admins', type=str, help='Comma-separated usernames to exclude.')
        parser.add_argument('--only-multi', action='store_true', help='Only process admins with more than one theme.')

    def handle(self, *args, **options):
        dry = options.get('dry_run')
        strategy = options.get('strategy')
        limit = options.get('limit')
        exclude = options.get('exclude_admins')
        only_multi = options.get('only_multi')

        excludes = set([u.strip() for u in (exclude or '').split(',') if u.strip()])

        admins = list(ThemeAdmin.objects.select_related('user').all())
        if not admins:
            self.stdout.write(self.style.WARNING('No ThemeAdmin records found.'))
            return

        if limit:
            admins = admins[:limit]

        processed = 0
        changed = 0
        for a in admins:
            username = a.user.username if a.user else '(unknown)'
            if username in excludes:
                continue

            current = list(a.themes.all())
            if only_multi and len(current) <= 1:
                continue

            processed += 1
            if len(current) <= 1:
                continue

            if strategy == 'first':
                keep = current[0]
            else:
                keep = random.choice(current)

            keep_name = keep.name
            remove_names = ', '.join([t.name for t in current if t.id != keep.id])

            if dry:
                self.stdout.write(f"DRY: {username}: keep '{keep_name}', remove [{remove_names}]")
                continue

            # Apply change
            a.themes.set([keep.id])
            changed += 1
            self.stdout.write(f"Updated {username}: kept '{keep_name}', removed [{remove_names}]")

        if dry:
            self.stdout.write(self.style.SUCCESS('Dry run complete. No changes saved.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Processed {processed} admins, updated {changed}.'))
