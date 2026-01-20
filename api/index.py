import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ncps_site.settings')

import django
from django.conf import settings

# Configure settings if needed
if not settings.configured:
    settings.DEBUG = False
    settings.ALLOWED_HOSTS = ['*']

django.setup()

from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()
