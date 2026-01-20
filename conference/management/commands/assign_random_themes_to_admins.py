from django.core.management.base import BaseCommand
from conference.models import ThemeAdmin, ScientificTheme
import random


class Command(BaseCommand):
    help = (
        "Assign random ScientificTheme memberships to ThemeAdmin records (for testing)."
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show changes without saving.')
        parser.add_argument('--seed', type=int, help='Optional random seed for reproducible assignment.')
        parser.add_argument('--min', type=int, default=1, help='Minimum number of themes per admin.')
        parser.add_argument('--max', type=int, default=3, help='Maximum number of themes per admin.')
        parser.add_argument('--limit', type=int, help='Limit number of admins to update (for testing).')
        parser.add_argument('--overwrite', action='store_true', help='Replace existing assignments instead of overwriting.')

    def handle(self, *args, **options):
        dry = options.get('dry_run')
        seed = options.get('seed')
        min_n = max(0, int(options.get('min') or 1))
        max_n = max(min_n, int(options.get('max') or min_n))
        limit = options.get('limit')
        overwrite = options.get('overwrite')

        if seed is not None:
            random.seed(seed)

        themes = list(ScientificTheme.objects.all())
        if not themes:
            self.stdout.write(self.style.WARNING('No ScientificTheme entries found. Nothing to assign.'))
            return

        admins = list(ThemeAdmin.objects.select_related('user').all())
        total_admins = len(admins)
        if total_admins == 0:
            self.stdout.write(self.style.WARNING('No ThemeAdmin records found.'))
            return

        if limit:
            admins = admins[:limit]

        changed = 0
        for a in admins:
            count = random.randint(min_n, min(max_n, len(themes)))
            chosen = random.sample(themes, count)
            chosen_ids = [t.id for t in chosen]
            chosen_names = ', '.join([t.name for t in chosen])

            current = list(a.themes.all())
            current_names = ', '.join([t.name for t in current]) if current else '(none)'

            if dry:
                self.stdout.write(f"DRY: {a.user.username}: {current_names} -> {chosen_names}")
                continue

            if overwrite:
                a.themes.set(chosen_ids)
            else:
                # replace with chosen set to avoid duplicates while preserving choice semantics
                a.themes.set(chosen_ids)

            changed += 1
            self.stdout.write(f"Updated {a.user.username}: assigned themes -> {chosen_names}")

        if dry:
            self.stdout.write(self.style.SUCCESS('Dry run completed. No changes saved.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Assigned random themes to {changed}/{len(admins)} ThemeAdmin records.'))
