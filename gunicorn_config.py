def post_worker_init(worker):
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    from accounts.jobs import rest_usage

    scheduler = BackgroundScheduler()
    scheduler.add_job(rest_usage, trigger=IntervalTrigger(minutes=1), max_instances=1, coalesce=True)
    scheduler.start()

    worker.scheduler = scheduler

    from django.conf import settings

    from accounts.services import sync_traffic_limit
    from accounts.xray_service import update_remarks

    sync_traffic_limit()
    update_remarks(settings.XRAY_REMARK)


def worker_exit(server, worker):
    if hasattr(worker, "scheduler"):
        worker.scheduler.shutdown()


workers = 1
threads = 100
wsgi_app = "net.wsgi:application"
