from django.core.management.base import BaseCommand
from conference.models import ThemeAdmin, AbstractSubmission

class Command(BaseCommand):
    help = 'Report ThemeAdmin themes and related abstracts'

    def handle(self, *args, **options):
        for ta in ThemeAdmin.objects.select_related('user').prefetch_related('themes').all():
            self.stdout.write(f'ThemeAdmin: {ta.id} {ta.user.username} active={ta.is_active}')
            for t in ta.themes.all():
                cnt = AbstractSubmission.objects.filter(theme=t).count()
                self.stdout.write(f'  Theme: {t.id} {getattr(t, "code", "n/a")} {t.name} -> abstracts={cnt}')
            abs_qs = AbstractSubmission.objects.filter(theme__in=ta.themes.all())
            self.stdout.write(f'  Recent abstracts for admin: {abs_qs.count()}')
            for a in abs_qs.order_by('-submitted_at')[:20]:
                self.stdout.write(f'    {a.id} | {a.title} | theme_id={a.theme_id}')
            self.stdout.write('---')
