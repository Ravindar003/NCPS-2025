from django.core.management.base import BaseCommand
from conference.models import ThemeAdmin, AbstractReview

class Command(BaseCommand):
    help = 'List AbstractReview assignments and ThemeAdmins'

    def handle(self, *args, **options):
        self.stdout.write('ThemeAdmins:')
        for ta in ThemeAdmin.objects.select_related('user').prefetch_related('themes').all():
            theme_names = [t.name for t in ta.themes.all()]
            self.stdout.write(f'  {ta.id} {ta.user.username} active={ta.is_active} themes={theme_names}')

        self.stdout.write('\nAbstractReviews:')
        for r in AbstractReview.objects.select_related('reviewer__user','assigned_by__user').all():
            assigned_by = r.assigned_by.user.username if r.assigned_by else None
            self.stdout.write(f'  Review {r.id} abstract_id={r.abstract_id} reviewer={r.reviewer.user.username} assigned_by={assigned_by} is_submitted={r.is_submitted}')

        self.stdout.write('\nPending assigned abstracts per reviewer:')
        for ta in ThemeAdmin.objects.select_related('user').all():
            revs = list(AbstractReview.objects.filter(reviewer=ta).values_list('abstract_id', flat=True))
            self.stdout.write(f'  {ta.user.username}: {revs}')
