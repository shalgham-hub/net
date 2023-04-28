import json
from base64 import urlsafe_b64encode
from hashlib import sha256
from typing import Optional
from urllib.parse import urljoin

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .xray_service import xray_reset_user_usage, xray_update_traffic_limit


def _get_fernet_key():
    return urlsafe_b64encode(sha256(settings.SECRET_KEY.encode()).digest())


_fernet = Fernet(_get_fernet_key())


def dict_encrypt(data: dict) -> str:
    encoded_data = json.dumps(data, ensure_ascii=False)
    encoded_data = encoded_data.encode()
    current_time = int(timezone.now().timestamp())
    encrypted_data = _fernet.encrypt_at_time(data=encoded_data, current_time=current_time)
    return encrypted_data.decode()


def dict_decrypt(string: str, ttl: Optional[int] = None) -> dict:
    encoded_data = _fernet.decrypt(token=string, ttl=ttl)
    encoded_data = encoded_data.decode()
    data = json.loads(encoded_data)
    return data


def send_password_reset_url_message(user: User, password_reset_url: str) -> None:
    email = user.email
    subject = settings.PASSWORD_RESET_SUBJECT
    message = f'<a href="{password_reset_url}">{password_reset_url}</a>'
    send_mail(subject=subject, message="", html_message=message, from_email=None, recipient_list=[email])


def send_password_reset_token(user: User) -> None:
    data = {'email': user.email}
    encrypted_token = dict_encrypt(data=data)
    BASE_URL = settings.WEB_BASE_URL
    password_reset_url_path = reverse('verify-password-reset-token', kwargs={"token": encrypted_token})
    url = urljoin(BASE_URL, password_reset_url_path)
    send_password_reset_url_message(user=user, password_reset_url=url)


def reset_password(token: str, new_password: str) -> User:
    data = dict_decrypt(token, ttl=300)
    email = data['email']
    user: User = User.objects.get(email=email)
    user.set_password(new_password)
    user.save()
    return user


def sync_traffic_limit(users: Optional[list[User]] = None) -> None:
    if users is None:
        users: list[User] = list(User.objects.select_related('traffic_policy').all())
    for user in users:
        if not user.username:
            continue

        user_quota = settings.MONTHLY_TRAFFIC_LIMIT_BYTES

        if user.traffic_policy:
            user_quota = user.traffic_policy.quota

        xray_update_traffic_limit(username=user.username, traffic_limit=user_quota)


def reset_users_data_usage(users: Optional[list[User]] = None) -> None:
    if users is None:
        users = list(User.objects.all())

    for user in users:
        xray_reset_user_usage(username=user.username)


__all__ = [
    'InvalidToken',
    'dict_encrypt',
    'dict_decrypt',
    'send_password_reset_token',
    'reset_password',
    'sync_traffic_limit',
]
