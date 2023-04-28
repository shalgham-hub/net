from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as _UserAdmin
from django.contrib.auth.forms import UsernameField
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from .models import TrafficPolicy, User
from .services import reset_users_data_usage


class UserCreationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("email", 'username')
        field_classes = {"username": UsernameField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._meta.model.USERNAME_FIELD in self.fields:
            self.fields[self._meta.model.USERNAME_FIELD].widget.attrs["autofocus"] = True

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(None)
        if commit:
            user.save()
        return user


@admin.register(User)
class UserAdmin(_UserAdmin):
    ordering = ['email']
    list_display = ('email', 'username', 'is_active', 'is_staff', 'traffic_policy')
    list_editable = ['traffic_policy']
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
                'fields': ('email', 'username', 'traffic_policy'),
            },
        ),
    )

    actions = ["action_reset_usage"]

    add_form = UserCreationForm

    @admin.action(description="Reset Traffic Usage")
    def action_reset_usage(self, request, queryset) -> None:
        users = list(queryset)
        reset_users_data_usage(users=users)
        self.message_user(request, gettext("Data usage reset for selected users."), messages.SUCCESS)


class UserInline(admin.StackedInline):
    model = User
    fk_name = 'traffic_policy'
    fields = ['username']
    readonly_fields = ['email', 'username']
    raw_id_fields = ['traffic_policy']

    def has_add_permission(self, *args, **kwargs) -> bool:
        return False

    def has_change_permission(self, *args, **kwargs) -> bool:
        return False

    def has_delete_permission(self, *args, **kwargs) -> bool:
        return False


@admin.register(TrafficPolicy)
class TrafficPolicyAdmin(admin.ModelAdmin):
    fields = ['name', 'quota']
    inlines = [UserInline]
