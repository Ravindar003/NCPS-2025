from django.core.management.base import BaseCommand
from conference.models import Participant, ScientificTheme
from conference.context_processors import theme_choices as get_theme_choices
import random


class Command(BaseCommand):
    help = "Assign random scientific_theme values to existing Participants (for testing)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show changes without saving.')
        parser.add_argument('--seed', type=int, help='Optional random seed for reproducible assignment.')
        parser.add_argument('--limit', type=int, help='Limit number of participants to update (for testing).')
        parser.add_argument('--only-old', action='store_true', help='Only update participants whose theme is not present in current registration choices.')

    def handle(self, *args, **options):
        dry = options.get('dry_run')
        seed = options.get('seed')
        limit = options.get('limit')

        if seed is not None:
            random.seed(seed)

        # Use the registration page's `theme_choices` as source-of-truth (context processor).
        try:
            reg_choices = get_theme_choices(None).get('theme_choices', [])
        except Exception:
            reg_choices = []

        if reg_choices:
            choices = [c[0] for c in reg_choices]
            name_map = {c[0]: c[1] for c in reg_choices}
        else:
            # Fallback to DB themes or static participant choices
            db_themes = list(ScientificTheme.objects.all())
            if db_themes:
                choices = [t.code for t in db_themes]
                name_map = {t.code: t.name for t in db_themes}
            else:
                choices = [c[0] for c in Participant.SCIENTIFIC_THEMES]
                name_map = {c[0]: c[1] for c in Participant.SCIENTIFIC_THEMES}

        qs = Participant.objects.select_related('user').all()
        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('No participants found.'))
            return

        if limit:
            qs = qs[:limit]

        only_old = options.get('only_old')
        valid_codes = set(choices)
        if only_old:
            qs = [p for p in qs if (p.scientific_theme not in valid_codes)]

        changed = 0
        for p in qs:
            new = random.choice(choices)
            if p.scientific_theme == new:
                continue
            if dry:
                left = name_map.get(p.scientific_theme, p.scientific_theme)
                right = name_map.get(new, new)
                self.stdout.write(f"DRY: {p.user.username}: {left} -> {right}")
            else:
                p.scientific_theme = new
                p.save()
                changed += 1
                self.stdout.write(f"Updated {p.user.username}: set theme -> {name_map.get(new, new)}")

        if dry:
            self.stdout.write(self.style.SUCCESS('Dry run completed. No changes saved.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Assigned random theme to {changed} participants.'))
