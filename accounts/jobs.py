from zoneinfo import ZoneInfo

import jdatetime
from django.utils import timezone

from accounts.models import TrafficResetLog, User

from .services import reset_users_data_usage


def rest_usage():
    now = timezone.now().astimezone(ZoneInfo('Asia/Tehran'))
    persian_date = jdatetime.date.fromgregorian(date=now.date())
    if persian_date.day != 1:
        return

    now = now.replace(hour=0, minute=0, second=0, microsecond=0)

    users = list(User.objects.exclude(traffic_reset_logs__date=now))
    reset_users_data_usage(users=users)
    reset_log_list = [TrafficResetLog(user=user, date=now) for user in users]
    TrafficResetLog.objects.bulk_create(reset_log_list, ignore_conflicts=True)
