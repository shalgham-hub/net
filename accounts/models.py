from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as _UserManager
from django.db import models
from django.db.models.constraints import UniqueConstraint
from django.utils.translation import gettext_lazy as _


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


class User(AbstractUser):
    email = models.EmailField(_("email address"), unique=True, max_length=50)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        from .xray_service import xray_activate_user, xray_deactivate_user

        if self.is_active:
            xray_activate_user(username=self.username)
        else:
            xray_deactivate_user(username=self.username)


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