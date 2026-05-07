from . import base

for setting_name in dir(base):
    if setting_name.isupper():
        globals()[setting_name] = getattr(base, setting_name)

env = base.env
BASE_DIR = base.BASE_DIR


# Development defaults can be overridden from .env
SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-#8f5c47^*x@&ewh5el0m)((ojgz4iwq*+0a^1u=)2gssj665^c",
)
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}
