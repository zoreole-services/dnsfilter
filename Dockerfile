FROM alpine:3.22.1

LABEL maintainer="Alexandre GIRARD <alexandre@zoreole.com>, Benjamin PAYET <benjamin@zoreole.com>, Tristan SCANDELLA <tristan@zoreole.com>"
LABEL version="1.0.0"

RUN apk add --no-cache sudo python3 py3-pip bash bind supervisor

#Create named user
RUN if ! id named &>/dev/null; then \
        adduser -D -g 'BIND DNS Server' named; \
    fi

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
    && pip install --no-cache-dir boto3 requests

# Define the PATH
ENV PATH="/venv/bin:$PATH"

# COPY app directory
COPY ./app /usr/src/app

# COPY supervisord configuration file
COPY ./app/config/supervisord.conf /etc/supervisord.conf

#COPY named configuration file for BINDTRANSFER solution
COPY ./bind/solution_bindtransfer/named.conf /etc/bind/named.conf
RUN chown named:named /etc/bind/named.conf

USER named

WORKDIR /usr/src/app

ENV EXECUTION_INTERVAL="30"
ENV AWS_REGION="eu-west-1"
ENV VERBOSITY="1"

#CMD ["tail", "-f", "/dev/null"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
