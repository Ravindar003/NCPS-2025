from django.core.management.base import BaseCommand
from conference.models import Participant


class Command(BaseCommand):
    help = "Populate participant_code for existing Participant records without one."

    def handle(self, *args, **options):
        qs = Participant.objects.filter(participant_code__isnull=True) | Participant.objects.filter(participant_code="")
        qs = qs.distinct()
        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('No participants need codes.'))
            return

        updated = 0
        for p in qs:
            # Trigger save() to generate code
            try:
                p.save()
                updated += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed for Participant id={p.id}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Populated participant_code for {updated}/{total} participants.'))
