from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from conference.models import Notification, AbstractSubmission

User = get_user_model()


class Command(BaseCommand):
    help = "Create a test Notification for a user."

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True, help='Target username or email')
        parser.add_argument('--title', required=True, help='Notification title')
        parser.add_argument('--message', required=True, help='Notification message')
        parser.add_argument('--abstract-id', type=int, help='Optional abstract id to link')
        parser.add_argument('--mark-read', action='store_true', help='Mark notification read')

    def handle(self, *args, **options):
        username = options['username']
        title = options['title']
        message = options['message']
        aid = options.get('abstract_id')
        mark_read = options.get('mark_read')

        # Allow passing email as username too
        user = None
        try:
            user = User.objects.filter(username=username).first()
            if not user:
                user = User.objects.filter(email=username).first()
        except Exception as e:
            raise CommandError(f"Error querying user: {e}")

        if not user:
            raise CommandError(f"User not found for '{username}'")

        abstract = None
        if aid:
            abstract = AbstractSubmission.objects.filter(id=aid).first()
            if not abstract:
                raise CommandError(f"Abstract with id={aid} not found")

        n = Notification.objects.create(
            user=user,
            abstract=abstract,
            title=title,
            message=message,
            is_read=bool(mark_read),
        )

        self.stdout.write(self.style.SUCCESS(f"Created notification id={n.id} for user={user.username}"))
