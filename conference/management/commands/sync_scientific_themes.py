from django.core.management.base import BaseCommand
from conference.models import ScientificTheme
from conference.context_processors import theme_choices as get_theme_choices


class Command(BaseCommand):
    help = "Sync ScientificTheme DB entries with the registration theme catalog (creates/updates names)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview changes without saving')

    def handle(self, *args, **options):
        dry = options.get('dry_run')
        try:
            choices = get_theme_choices(None).get('theme_choices', [])
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to load theme choices: {e}'))
            return

        created = 0
        updated = 0
        for code, name in choices:
            st = ScientificTheme.objects.filter(code=code).first()
            if not st:
                if dry:
                    self.stdout.write(f'DRY: create {code} -> "{name}"')
                else:
                    ScientificTheme.objects.create(code=code, name=name)
                    created += 1
                    self.stdout.write(f'Created theme {code} -> "{name}"')
            else:
                if st.name != name:
                    if dry:
                        self.stdout.write(f'DRY: update {code} name "{st.name}" -> "{name}"')
                    else:
                        st.name = name
                        st.save()
                        updated += 1
                        self.stdout.write(f'Updated theme {code} name -> "{name}"')

        if dry:
            self.stdout.write(self.style.SUCCESS('Dry run complete.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Sync complete. Created: {created}, Updated: {updated}'))
