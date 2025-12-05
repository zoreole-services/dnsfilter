FROM alpine:3.23.0

LABEL maintainer="Alexandre GIRARD <alexandre@zoreole.com>, Benjamin PAYET <benjamin@zoreole.com>, Tristan SCANDELLA <tristan@zoreole.com>"
LABEL version="1.0.0"

ARG BOTO3_VERSION="1.42.3"
ARG REQUESTS_VERSION="2.32.5"

RUN apk add --no-cache \ 
    bash \
    bind \
    py3-pip \
    python3 \
    sudo \
    supervisor

#Create named user
#RUN adduser -D named;

# Create the required directory with the right permissions
RUN mkdir -p /usr/src/app/zones \
    && mkdir -p /var/cache/bind \
    && mkdir -p /etc/bind \
    && mkdir -p /var/log/supervisor \
    && chown -R named:named /usr/src/app/ /var/cache/bind /etc/bind /var/log/supervisor \
    && chmod 770 /var/cache/bind \
    && chmod 775 /usr/src/app/zones \
    && chmod 775 /var/log/supervisor


# Create the venv
RUN python3 -m venv /venv \
    && . /venv/bin/activate \
    && pip install --no-cache-dir \
    boto3==${BOTO3_VERSION} \
    requests==${REQUESTS_VERSION} 

# Define the PATH
ENV PATH="/venv/bin:$PATH"

COPY ./app /usr/src/app
COPY ./supervisord.conf /etc/supervisord.conf
COPY ./named.conf /etc/bind/named.conf

RUN chown named:named /etc/bind/named.conf

USER named

WORKDIR /usr/src/app

ENV EXECUTION_INTERVAL="30"
ENV AWS_REGION="eu-west-1"
ENV VERBOSITY="1"
ENV DNS_TTL="60"


# Expose DNS ports
EXPOSE 53/tcp
EXPOSE 53/udp

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
