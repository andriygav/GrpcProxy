FROM python:3.8.11-alpine3.13

COPY ./src/requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt \
    && rm -rf /tmp/* /root/.cache/*

COPY ./src /app/

RUN pip install /app/ \
    && rm -rf /root/.cache/*

COPY ./config/config.cfg /config/config.cfg

CMD ["python3", "-m", "grpc_proxy.service", "/config/config.cfg", "/config/setup.yaml"]
