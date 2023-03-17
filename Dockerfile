FROM python:3.10-slim

# installing need python packages
COPY requirements.txt /app/
RUN pip install --no-cache-dir -U pip setuptools \
    && pip install --no-cache-dir -r /app/requirements.txt


WORKDIR /app

# copy codes to container
COPY . /app

RUN cd /app && DJANGO_SETTINGS_MODULE=net.dummy_settings python manage.py collectstatic

ENV PYTHONIOENCODING utf8

ENTRYPOINT [ "/bin/bash", "-c"]
CMD [ "gunicorn -c gunicorn_config.py"]
