reCAPTCHA Setup

1) Obtain keys
- Go to https://www.google.com/recaptcha/admin and register your site.
- Choose reCAPTCHA v2 ("I'm not a robot" checkbox) or v3 as needed.
- Copy the Site Key and Secret Key.

2) Configure locally (PowerShell)
- In PowerShell, set environment variables for the current session:

```powershell
$env:RECAPTCHA_SITE_KEY = "<your-site-key>"
$env:RECAPTCHA_SECRET_KEY = "<your-secret-key>"
python manage.py runserver
```

- To set them permanently on Windows, use System > Environment Variables or set via PowerShell profile.

3) Alternative (development only)
- You can temporarily hardcode keys in `ncps_site/settings.py` (not recommended for production):

```python
RECAPTCHA_SITE_KEY = "your-site-key"
RECAPTCHA_SECRET_KEY = "your-secret-key"
```

4) Restart server
- After setting env vars, restart the Django development server so `settings.py` picks them up.

5) Testing
- Visit /register/ and confirm the reCAPTCHA widget appears and completes verification during signup.

Notes
- Server-side verification uses `RECAPTCHA_SECRET_KEY`; both keys are required for full functionality.
- If you want, provide the keys and I can add them into `settings.py` for development (but do not commit secrets to source control).