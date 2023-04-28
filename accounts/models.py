from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as _UserManager
from django.core import validators
from django.db import models
from django.db.models.constraints import UniqueConstraint
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

from .utils import prettify_bytes


class UserManager(_UserManager):
    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email, and password.
        """
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


@deconstructible
class UnicodeUsernameValidator(validators.RegexValidator):
    regex = r"^[\w]+\Z"
    message = _("Enter a valid username. This value may contain only letters, numbers and _.")
    flags = 0


class User(AbstractUser):
    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_("Required. 150 characters or fewer. Letters, digits and _ only."),
        validators=[username_validator],
        error_messages={"unique": _("A user with that username already exists.")},
    )

    email = models.EmailField(_("email address"), unique=True, max_length=50)

    traffic_policy = models.ForeignKey(
        'accounts.TrafficPolicy',
        related_name="users",
        related_query_name="users",
        on_delete=models.PROTECT,
        null=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        from .services import sync_traffic_limit
        from .xray_service import xray_activate_user, xray_deactivate_user

        if not self.username:
            return

        if self.is_active:
            xray_activate_user(username=self.username)
        else:
            xray_deactivate_user(username=self.username)

        sync_traffic_limit(users=[self])


class TrafficResetLog(models.Model):
    date = models.DateTimeField(_("date"))
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="traffic_rest_logs",
        related_query_name="traffic_reset_logs",
    )

    class Meta:
        constraints = [UniqueConstraint(fields=["date", "user"], name="rest_log_user_date_uniq")]


class TrafficPolicy(models.Model):
    name = models.CharField(_("Policy Name"), max_length=128)
    quota = models.PositiveBigIntegerField(_('Quota (bytes)'))

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)

        from .services import sync_traffic_limit

        sync_traffic_limit(users=list(self.users.select_related('traffic_policy').all()))

    def __str__(self) -> str:
        return f"{self.name} ({prettify_bytes(self.quota)})"
