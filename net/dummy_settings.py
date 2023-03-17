import os

os.environ.setdefault("SECRET_KEY", "fake")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("ALLOWED_HOSTS", "localhost")
os.environ.setdefault("DATABASE_DIR", "/app")
os.environ.setdefault("EMAIL_HOST", "localhost")
os.environ.setdefault("EMAIL_HOST_PASSWORD", "1")
os.environ.setdefault("EMAIL_HOST_USER", "user")
os.environ.setdefault("EMAIL_PORT", "1")
os.environ.setdefault("DEFAULT_FROM_EMAIL", "1")
os.environ.setdefault("PASSWORD_RESET_SUBJECT", "1")
os.environ.setdefault("WEB_BASE_URL", "http://localhost")
os.environ.setdefault("MARZBAN_ACCESS_TOKEN", "1")
os.environ.setdefault("MARZBAN_BASE_URL", "http://localhost")
os.environ.setdefault("MONTHLY_TRAFFIC_LIMIT_BYTES", "1")


from .settings import *  # noqa

MIDDLEWARE = []

DATABASES = {}
