import argparse
import logging
import boto3
import os
import subprocess
import re
import random
from subprocess import DEVNULL, STDOUT

from exceptions import (
    BindError,
    AWSError,
    ConfigError,
)



def run_bind():
    """
    Starts the BIND9 DNS server in foreground mode.

    Raises:
        BindError: If BIND9 fails to start.
    """
    try:
        process = subprocess.Popen(
            ["/usr/sbin/named", "-f", "-c", "/etc/bind/named.conf", "-g"],
            stdout=DEVNULL,
            stderr=STDOUT
        )
        logging.info(f"BIND9 started with PID {process.pid}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error when trying to run bind9: {e}")
        raise BindError(f"BIND9 startup failed: {e}")
    except Exception as e:
        logging.error(f"Unexpected error when trying to run bind9: {e}")
        raise BindError(f"Unexpected error: {e}")



def create_s3_objects(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME, S3_OBJECT_KEY):
    """
    Creates an S3 object reference for accessing AWS S3 resources.

    Args:
        AWS_ACCESS_KEY_ID (str): AWS access key ID.
        AWS_SECRET_ACCESS_KEY (str): AWS secret access key.
        AWS_REGION (str): AWS region.
        S3_BUCKET_NAME (str): S3 bucket name.
        S3_OBJECT_KEY (str): S3 object key (path to the file).

    Returns:
        boto3.resources.factory.s3.Object: S3 object reference.

    Raises:
        AWSError: If S3 session creation fails.
    """
    try:
        s3_session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        s3_resource = s3_session.resource('s3')
        s3_object = s3_resource.Object(S3_BUCKET_NAME, S3_OBJECT_KEY)
        return s3_object
    except Exception as e:
        logging.error(f"Failed to create S3 object: {e}")
        raise AWSError(f"S3 session creation failed: {e}")


def check_file_exists(file_path):
    """
    Check if RPZ file exists.

    Args:
        file_path (str): Path to RPZ file. Default value is "/usr/src/app/zones/rpz.db".

    Returns:
        bool: True if RPZ file exists and False if not.
    """
    return os.path.isfile(file_path)

def get_solutionid_env():
    """
    Retrieves the SOLUTION_IDENTIFIER environment variable.

    Returns:
        str: The solution identifier.

    Raises:
        ConfigError: If SOLUTION_IDENTIFIER is not set.
    """
    SOLUTION_IDENTIFIER = os.getenv("SOLUTION_IDENTIFIER")
    if not SOLUTION_IDENTIFIER:
        raise ConfigError("SOLUTION_IDENTIFIER environment variable is not set.")
    return SOLUTION_IDENTIFIER


def get_verbosity_env():
    """
    Retrieves the SOLUTION_IDENTIFIER environment variable.

    Returns:
        str: The solution identifier.

    Raises:
        ConfigError: If SOLUTION_IDENTIFIER is not set.
    """
    VERBOSITY = os.getenv("VERBOSITY")
    if not VERBOSITY:
        raise ConfigError("VERBOSITY environment variable is not set.")
    return int(VERBOSITY)


def get_interval_env():
    """
    Retrieves and converts the EXECUTION_INTERVAL environment variable to seconds.

    Returns:
        int: Execution interval in seconds.

    Raises:
        ConfigError: If EXECUTION_INTERVAL is not set or is not a valid integer.
    """
    EXECUTION_INTERVAL = os.getenv("EXECUTION_INTERVAL")
    if not EXECUTION_INTERVAL:
        raise ConfigError("EXECUTION_INTERVAL environment variable is not set.")

    try:
        return int(EXECUTION_INTERVAL) * 60
    except ValueError:
        raise ConfigError("EXECUTION_INTERVAL must be a valid integer.")


def update_named_config(BIND_SLAVE_IPADDR):
    """
    Updates the BIND named.conf file with the provided slave IP address(es).

    Args:
        BIND_SLAVE_IPADDR (str): Comma-separated list of slave IP addresses or "any".

    Raises:
        ConfigError: If the named.conf file cannot be updated.
    """
    try:

        named_conf_path = "/etc/bind/named.conf"

        if BIND_SLAVE_IPADDR.lower() == "any":
            replacement = "any;"
        else:
            ips = [ip.strip() for ip in BIND_SLAVE_IPADDR.split(",") if ip.strip()]
            replacement = " ".join(f"{ip};" for ip in ips)

        with open(named_conf_path, "r") as f:
            content = f.read()

        updated_content = re.sub(
            r"(allow-(?:query|transfer)\s*{)\s*X\.X\.X\.X\s*;\s*(})",
            rf"\1 {replacement} \2",
            content
        )

        with open(named_conf_path, "w") as f:
            f.write(updated_content)

        logging.debug(f"Updated named.conf:\n{updated_content}")
    except Exception as e:
        logging.error(f"Failed to update named.conf: {e}")
        raise ConfigError(f"Failed to update named.conf: {e}")



def get_aws_env():
    """
    Retrieves AWS-related environment variables.

    Returns:
        tuple: (S3_OBJECT_KEY_PATH, S3_OBJECT_FILE_NAME, AWS_ACCESS_KEY_ID,
                AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME, S3_OBJECT_KEY)

    Raises:
        ConfigError: If any required AWS environment variable is missing.
    """
    try:
        S3_OBJECT_KEY_PATH = os.getenv("S3_OBJECT_KEY_PATH")
        S3_OBJECT_FILE_NAME = os.getenv("S3_OBJECT_FILE_NAME")
        AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
        AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
        AWS_REGION = os.getenv("AWS_REGION")
        S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

        if None in (S3_OBJECT_KEY_PATH, S3_OBJECT_FILE_NAME, AWS_ACCESS_KEY_ID,
                    AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME):
            raise ConfigError("One or more AWS environment variables are missing.")

        S3_OBJECT_KEY = f"{S3_OBJECT_KEY_PATH}/{S3_OBJECT_FILE_NAME}"
        return (S3_OBJECT_KEY_PATH, S3_OBJECT_FILE_NAME, AWS_ACCESS_KEY_ID,
                AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME, S3_OBJECT_KEY)
    except Exception as e:
        logging.error(f"Failed to retrieve AWS environment variables: {e}")
        raise ConfigError(f"AWS config error: {e}")



def parse_args():
    """
    Parses command-line arguments for verbosity level.

    Returns:
        argparse.Namespace: Parsed arguments with verbosity level.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Get more debug information (-v, -vv, -vvv)"
    )
    return parser.parse_args()

def setup_logger(verbosity: int):
    """
    Configures the logging level based on verbosity.

    Args:
        verbosity (int): Verbosity level (0: WARNING, 1: INFO, 2+: DEBUG).
    """
    # Mapping between verbosity and logging level
    if verbosity == 0:
        level = logging.WARNING
    elif verbosity == 1:
        level = logging.INFO
    else:  # -vv or more
        level = logging.DEBUG

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=level,
    )



def get_domain_list():
    """
    Retrieves the list of domains from an S3 bucket.

    Returns:
        set: A set of domains (empty set if an error occurs).

    Raises:
        AWSError: If there is an error fetching domains from S3.
    """
    try:
        (_, _, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION,
         S3_BUCKET_NAME, S3_OBJECT_KEY) = get_aws_env()

        s3_object = create_s3_objects(
            AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION,
            S3_BUCKET_NAME, S3_OBJECT_KEY
        )

        data = s3_object.get()['Body'].read().decode('UTF-8').strip()
        return set(filter(None, data.split('\n')))  # Remove empty lines

    except Exception as e:
        logging.error(f"Error fetching domains from S3: {e}")
        raise AWSError(f"Failed to fetch domains: {e}")


def get_domain_list_test():

    base_domains = {
        'mag.ott-hello.xyz', 'my.amazing-tv.com', 'lg.peces.biz', 'hosamir.net',
        'b.delta2022.xyz', 'es.greatott.me', 'ftyqvtyz.qastertv.xyz', 'fastopen.live',
        'panel.globesrv.net', 'line.krooba.cc', 'iptvmedia.live', 'sub.flood-wall.net'
    }
    domains_less = {
        'mag.ott-hello.xyz', 'my.amazing-tv.com', 'lg.peces.biz', 'hosamir.net',
        'b.delta2022.xyz', 'es.greatott.me', 'ftyqvtyz.qastertv.xyz', 'fastopen.live',
        'panel.globesrv.net', 'sub.flood-wall.net'
    }
    domains_more = {
        'mag.ott-hello.xyz', 'my.amazing-tv.com', 'lg.peces.biz', 'hosamir.net',
        'b.delta2022.xyz', 'es.greatott.me', 'ftyqvtyz.qastertv.xyz', 'fastopen.live',
        'panel.globesrv.net', 'line.krooba.cc', 'iptvmedia.live', 'sub.flood-wall.net', 'tata.com', 'toto.fr'
    }

    action = random.choice(['same', 'less', 'more'])

    if action == 'same':
        # Même liste
        return base_domains
    elif action == 'less':
        # Même liste
        return domains_less
    elif action == 'more':
        # Même liste
        return domains_more
