from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as _UserAdmin
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from .models import User
from .services import reset_users_data_usage


@admin.register(User)
class UserAdmin(_UserAdmin):
    ordering = ['email']
    list_display = ('email', 'username', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    list_display_links = ['email']

    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('email', 'password1', 'password2'),
            },
        ),
    )

    actions = ["action_reset_usage"]

    @admin.action(description="Reset Traffic Usage")
    def action_reset_usage(self, request, queryset) -> None:
        users = list(queryset)
        reset_users_data_usage(users=users)
        self.message_user(request, gettext("Data usage reset for selected users."), messages.SUCCESS)
