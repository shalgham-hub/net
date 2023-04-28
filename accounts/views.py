from django import forms
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.auth.views import LoginView as _LoginView
from django.contrib.auth.views import LogoutView as _LogoutView
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import validate_email
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.crypto import constant_time_compare
from django.views import View
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Gauge, generate_latest

from .models import User
from .services import InvalidToken, add_user, reset_password, send_password_reset_token
from .xray_service import xray_create_user, xray_get_system_info, xray_get_user, xray_reset_user_credentials


class PasswordResetView(View):
    class Form(forms.Form):
        email = forms.EmailField()

    def get(self, request: HttpRequest) -> HttpResponse:
        form = self.Form()
        return render(request=request, template_name='accounts/password_reset.html', context={'form': form})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = self.Form(data=request.POST)
        if not form.is_valid():
            return render(
                request=request, template_name='accounts/password_reset.html', context={'form': form}
            )

        email = form.cleaned_data['email']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = None
        else:
            send_password_reset_token(user=user)

        return render(
            request=request,
            template_name='accounts/password_reset_message.html',
            context={'email': email},
        )


class VerifyPasswordResetView(View):
    class Form(forms.Form):
        password1 = forms.CharField(widget=forms.PasswordInput())
        password2 = forms.CharField(widget=forms.PasswordInput())

        def clean(self):
            password_1 = self.cleaned_data['password1']
            password_2 = self.cleaned_data['password2']
            if password_1 != password_2:
                raise ValidationError(message="Passwords do not match.")

    def get(self, request: HttpRequest, token: str) -> HttpResponse:
        form = self.Form()

        return render(
            request=request,
            template_name='accounts/verify_password_reset.html',
            context={"form": form, "token": token},
        )

    def post(self, request: HttpRequest, token: str) -> HttpResponse:
        form = self.Form(data=request.POST)
        if not form.is_valid():
            return render(
                request=request,
                template_name='accounts/verify_password_reset.html',
                context={'form': form, "token": token},
            )
        new_password = form.cleaned_data['password1']

        try:
            user = reset_password(token=token, new_password=new_password)
        except InvalidToken:
            return render(request=request, template_name="accounts/password_reset_invalid_token.html")

        return render(
            request=request,
            template_name='accounts/password_reset_success.html',
            context={"user": user},
        )


class LoginView(_LoginView):
    def dispatch(self, request: HttpRequest, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')

        return super().dispatch(request, *args, **kwargs)

    def get_redirect_url(self) -> str:
        return reverse('home')


class LogoutView(_LogoutView):
    def get_redirect_url(self) -> str:
        return reverse('login')


class HomeView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        user: User = request.user
        username = user.username
        xray_user = xray_get_user(username=username)
        if not xray_user:
            user_quota = settings.MONTHLY_TRAFFIC_LIMIT_BYTES
            if getattr(user, 'traffic_policy', None):
                user_quota = user.traffic_policy.quota
            xray_user = xray_create_user(username=username, traffic_limit=user_quota)
        return render(
            request=request,
            template_name='accounts/home.html',
            context={'user': request.user, 'xray_user': xray_user},
        )


class ConfigResetCredentials(LoginRequiredMixin, View):
    def post(self, request: HttpRequest) -> HttpResponse:
        username = request.user.username
        xray_reset_user_credentials(username=username)
        return redirect("home")


class AddAccounts(LoginRequiredMixin, View):
    class Form(forms.Form):
        info = forms.CharField(widget=forms.Textarea())

    def get(self, request: HttpRequest) -> HttpResponse:
        if not request.user.is_staff or not request.user.is_superuser:
            return self.handle_no_permission()

        form = self.Form()

        return render(request=request, template_name="accounts/add_accounts.html", context={'form': form})

    def post(self, request: HttpRequest) -> HttpResponse:
        if not request.user.is_staff or not request.user.is_superuser:
            return self.handle_no_permission()

        form = self.Form(data=request.POST)
        if not form.is_valid():
            return render(request=request, template_name="accounts/add_accounts.html", context={'form': form})

        info = form.cleaned_data['info']
        info_list = []
        validate_username = UnicodeUsernameValidator()
        try:
            for item in info.split('\n'):
                email, username = item.split(',')
                email, username = email.strip(), username.strip()
                validate_email(email)
                validate_username(username)
                info_list.append((email, username))
        except Exception:
            return render(request=request, template_name="accounts/add_accounts.html", context={'form': form})

        try:
            for email, username in info_list:
                add_user(email=email, username=username)
        except Exception as ex:
            message = str(ex)
            return render(
                request=request,
                template_name="accounts/add_accounts.html",
                context={'form': form, "error": message},
            )

        return HttpResponse(content="OK")


class MetricsView(View):
    def has_access(self, request) -> bool:
        """
        adopted from https://github.com/encode/django-rest-framework/blob/c9e7b68a4c1db1ac60e962053380acda549609f3/rest_framework/authentication.py
        """
        auth = request.META.get('HTTP_AUTHORIZATION', b'')
        if isinstance(auth, str):
            # Work around django test client oddness
            auth = auth.encode('iso-8859-1')
        auth = auth.split()

        if not auth or auth[0].lower() != 'bearer'.encode():
            return False

        if len(auth) == 1:
            return False

        elif len(auth) > 2:
            return False

        try:
            token = auth[1].decode()
        except UnicodeError:
            return False

        if settings.METRICS_ACCESS_TOKEN is None:
            return False

        if not constant_time_compare(token, settings.METRICS_ACCESS_TOKEN):
            return False

        return True

    def get(self, request: HttpRequest) -> HttpResponse:
        if not self.has_access(request=request):
            raise PermissionDenied()

        xray_system_info = xray_get_system_info()
        registry = CollectorRegistry(auto_describe=True)
        namespace = settings.METRICS_NAMESPACE or ""

        total_memory = Gauge(
            name='total_memory_bytes',
            documentation="Total available memory in system",
            namespace=namespace,
            registry=registry,
        )
        total_memory.set(xray_system_info.total_memory_bytes)

        used_memory = Gauge(
            name='used_memory_bytes',
            documentation="Used memory by all process in system",
            namespace=namespace,
            registry=registry,
        )
        used_memory.set(xray_system_info.used_memory_bytes)

        total_users_count = Gauge(
            name='total_users_count',
            documentation="Total users count",
            namespace=namespace,
            registry=registry,
        )
        total_users_count.set(xray_system_info.total_users_count)

        active_users_count = Gauge(
            name='active_users_count',
            documentation="Active users count",
            namespace=namespace,
            registry=registry,
        )
        active_users_count.set(xray_system_info.active_users_count)

        total_transmitted_traffic = Gauge(
            name='total_transmitted_traffic_bytes',
            documentation="Total transmitted data in bytes",
            namespace=namespace,
            registry=registry,
        )
        total_transmitted_traffic.set(xray_system_info.total_transmitted_traffic_bytes)

        total_received_traffic = Gauge(
            name='total_received_traffic_bytes',
            documentation="Total received data in bytes",
            namespace=namespace,
            registry=registry,
        )
        total_received_traffic.set(xray_system_info.total_received_traffic_bytes)

        metrics = generate_latest(registry=registry)

        return HttpResponse(content=metrics, content_type=CONTENT_TYPE_LATEST)
