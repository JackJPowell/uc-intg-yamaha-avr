FROM python:3.11-slim-bullseye

WORKDIR /app

COPY ./requirements.txt requirements.txt
RUN pip3 install --no-cache-dir --upgrade -r requirements.txt
RUN mkdir /config

ADD . .

ENV UC_DISABLE_MDNS_PUBLISH="false"
ENV UC_MDNS_LOCAL_HOSTNAME=""

ENV UC_INTEGRATION_INTERFACE="0.0.0.0"
ENV UC_INTEGRATION_HTTP_PORT="9090"

ENV UC_CONFIG_HOME="/config"
LABEL org.opencontainers.image.source https://github.com/jackjpowell/uc-intg-yamaha-avr

CMD ["python3", "-u", "intg-yamaha-avr/driver.py"]