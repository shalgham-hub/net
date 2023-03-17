from dataclasses import dataclass
from urllib.parse import urljoin

import requests
import urllib3
from django.conf import settings
from django.utils.crypto import get_random_string
from requests.auth import AuthBase

urllib3.disable_warnings()


class TokenAuth(AuthBase):
    def __init__(self, token: str) -> None:
        self._token = token

    def __call__(self, request):
        request.headers['Authorization'] = f"Bearer {self._token}"
        return request


_session = requests.Session()
if settings.XRAY_SERVER_CERTIFICATE_FILE:
    _session.verify = settings.XRAY_SERVER_CERTIFICATE_FILE
_session.auth = TokenAuth(settings.MARZBAN_ACCESS_TOKEN)
_base_url = settings.MARZBAN_BASE_URL


class XrayError(Exception):
    def __init__(self, details) -> None:
        self.details = details

    def __str__(self) -> str:
        return str(self.details)


@dataclass(frozen=True, slots=True)
class XrayUser:
    username: str
    shadowsocks_config: str
    used_traffic: int
    traffic_limit: int


def xray_create_user(username: str, traffic_limit: int):
    path = '/api/user'
    url = urljoin(_base_url, path)

    data = {
        "username": username,
        "proxies": {"shadowsocks": {"password": get_random_string(length=32)}},
        "inbounds": {"shadowsocks": ['SHADOWSOCKS_INBOUND']},
        "data_limit_reset_strategy": "no_reset",
        "data_limit": traffic_limit,
        "status": "active",
    }

    response = _session.post(url=url, json=data)
    if response.status_code not in [409, 200]:
        raise XrayError({'status': response.status_code, 'body': response.json()})

    data = response.json()
    link = [item for item in data['links'] if item.startswith('ss')]

    return XrayUser(
        username=username,
        shadowsocks_config=link[0],
        used_traffic=data['used_traffic'],
        traffic_limit=data['data_limit'],
    )


def xray_get_user(username: str) -> XrayUser | None:
    path = f'/api/user/{username}'
    url = urljoin(_base_url, path)
    response = _session.get(url)

    if response.status_code == 404:
        return None

    if response.status_code != 200:
        raise XrayError({'status': response.status_code, 'body': response.json()})

    data = response.json()
    link = [item for item in data['links'] if item.startswith('ss')]

    return XrayUser(
        username=username,
        shadowsocks_config=link[0],
        used_traffic=data['used_traffic'],
        traffic_limit=data['data_limit'],
    )


def xray_reset_user_credentials(username: str) -> None:
    path = f'/api/user/{username}'
    url = urljoin(_base_url, path)
    data = {"proxies": {'shadowsocks': {"password": get_random_string(length=32)}}}
    response = _session.put(url=url, json=data)
    if response.status_code not in [404, 200]:
        raise XrayError({'status': response.status_code, 'body': response.json()})


def xray_reset_user_usage(username: str) -> None:
    path = f'/api/user/{username}/reset'
    url = urljoin(_base_url, path)
    response = _session.post(url=url)
    if response.status_code == 404:
        return
    if response.status_code != 200:
        raise XrayError({'status': response.status_code, 'body': response.json()})


def xray_update_traffic_limit(username: str, traffic_limit: int) -> None:
    path = f'/api/user/{username}'
    url = urljoin(_base_url, path)
    data = {"data_limit": traffic_limit}
    response = _session.put(url=url, json=data)
    if response.status_code not in [404, 200]:
        raise XrayError({'status': response.status_code, 'body': response.json()})


def xray_activate_user(username: str) -> None:
    path = f'/api/user/{username}'
    url = urljoin(_base_url, path)
    data = {"status": "active"}
    response = _session.put(url=url, json=data)
    if response.status_code not in [404, 200]:
        raise XrayError({'status': response.status_code, 'body': response.json()})


def xray_deactivate_user(username: str) -> None:
    path = f'/api/user/{username}'
    url = urljoin(_base_url, path)
    data = {"status": "disabled"}
    response = _session.put(url=url, json=data)
    if response.status_code not in [404, 200]:
        raise XrayError({'status': response.status_code, 'body': response.json()})


def update_remarks(remark: set) -> None:
    path = "/api/hosts"
    url = urljoin(_base_url, path)

    response = _session.get(url=url)

    result = response.json()

    for inbound_tag, hosts in result.items():
        for host in hosts:
            host['remark'] = remark

    _session.put(url=url, json=result)
