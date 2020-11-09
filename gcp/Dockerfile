FROM python:3.7-buster

ARG MAYOR_REVISION
ARG MINOR_REVISION
ARG BUILD_ID

#labeling
LABEL org.label-schema.name="uPyCO2 RestAPI Service" \
    org.label-schema.description="Docker running restapi service to access to the CO2 sensor data" \
    org.label-schema.url="https://lemariva.com" \
    org.label-schema.vcs-url="https://github.com/lemariva/uPyCO2" \
    org.label-schema.vendor="LeMaRiva|Tech info@lemariva.com" \
    org.label-schema.version="${MAYOR_REVISION}.${MINOR_REVISION}.${BUILD_ID}"

WORKDIR /home
COPY resources/requirements.txt /tmp/requirements.txt
COPY resources/service_account.json /home/service_account.json

RUN apt-get update \
    && apt-get install -y python-pip \
    && pip install -r /tmp/requirements.txt \
    && rm -rf /var/lib/apt/lists/*

COPY app /home/app
COPY resources/restapi-service.sh /etc/init.d/restapi-service.sh

CMD [ "sh", "/etc/init.d/restapi-service.sh" ]

EXPOSE 8080

STOPSIGNAL SIGTERM