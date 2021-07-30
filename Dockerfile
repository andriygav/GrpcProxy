FROM python:3.8.9-slim

COPY ./src/requirements.txt /tmp/requirements.txt

RUN cat /tmp/requirements.txt | xargs --no-run-if-empty -l pip install \
     && rm -rf /tmp/* /root/.cache/*

COPY ./src /app/

RUN pip install /app/ \
    && rm -rf /root/.cache/*

COPY ./config/config.cfg /config/config.cfg

CMD ["python3", "-m", "grpc_proxy.service", "/config/config.cfg", "/config/setup.yaml"]
