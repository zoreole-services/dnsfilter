import argparse
import logging
import boto3
import os
import subprocess
import re
import random
from subprocess import DEVNULL, STDOUT
import requests
import idna
from typing import List, Dict, Tuple, Set
from exceptions import (
    BindError,
    AWSError,
    ConfigError,
)

def is_reserved_domain(domain: str) -> bool:
    """
   Validate if domain is part of the IANA reserved domains.
    Returns:
        bool: result
    Raises:
        Exception: If unexpected result.    
    """
    reserved_domains: Set[str] = {
        "example", "test", "localhost", "invalid", "local", "onion", "arpa"
    }
    try:
        if (domain in reserved_domains):
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Failed to check whether the domain is reserved: {e}")

def is_valid_fqdn(domain: str) -> bool:
    """
    Validate if domain FQDN valid.
    Returns:
        bool: result
    """
    fqdn_regex = re.compile(
        r'^'
        r'(?!-)[A-Za-z0-9-]{1,63}(?<!-)'
        r'(\.[A-Za-z0-9-]{1,63}(?<!-))+'
        r'$'
    )
    return bool(fqdn_regex.match(domain))

def is_valid_tld(domain: str) -> bool:
    """
    Validate if domain is part of valid TLD domain list.
    Returns:
        bool: result
    """
    valid_tlds: Set[str] = set()
    tld_file_path = "/tmp/valid_tld.txt"
    try:
        response = requests.get("https://data.iana.org/TLD/tlds-alpha-by-domain.txt")
        if response.status_code == 200:
            tlds = response.text.splitlines()
            tlds = [tld.lower() for tld in tlds if tld and not tld.startswith("#")]
            valid_tlds=set(tlds)
            with open(tld_file_path, 'w') as f:
                f.write(response.text)
    except:
        try:
            if os.path.exists(tld_file_path):
                with open(tld_file_path, 'r') as f:
                    tlds = f.read().splitlines()
                    tlds = [tld.lower() for tld in tlds if tld and not tld.startswith("#")]
                    valid_tlds = set(tlds)
        except:
            valid_tlds: Set[str] = {
                "com", "org", "net", "int", "edu", "gov", "mil", "fr", "re",
                "io", "ai", "co", "uk", "de", "eu", "us", "ca", "au", "jp"
            }
    tld = domain.split('.')[-1].lower()
    if tld in valid_tlds:
        return True
    else:
        return False

def validate_domains(domain_list: List[str]) -> Tuple[List[Dict[str, List[str]]], List[str]]:
    """
   Validate if retrieved domain list.
    Returns:
        results (str): result messages
        new_domain_list (list): The new domain list without the invalid domains.
    """
    results = []
    new_domain_list = []
    DOMAIN_WHITELIST = get_domainwhitelist()
    for domain in domain_list:
        is_valid = True
        messages = []
        domain = domain.strip().lower()
        try:
            domain = idna.encode(domain).decode('ascii')
        except idna.IDNAError as e:
            is_valid = False
            messages.append(f"Domain: \"{domain}\" deleted from list. Reason: {e}")
            continue
        if is_reserved_domain(domain):
            is_valid = False
            messages.append(f"Domain: \"{domain}\" deleted from list. Reason: Domain is reserved by IANA")
        if not is_valid_fqdn(domain):
            is_valid = False
            messages.append(f"Domain: \"{domain}\" deleted from list. Reason: Invalid FQDN format")
        if not is_valid_tld(domain):
            is_valid = False
            messages.append(f"Domain: \"{domain}\" deleted from list. Reason: TLD '{domain.split('.')[-1]}' is invalid")       
        if domain in DOMAIN_WHITELIST:
            is_valid = False
            messages.append(f"Domain: \"{domain}\" deleted from list. Domain is part of the whitelist")
        
        if is_valid == False:
            results.append({
                "domain": domain,
                "messages": messages 
            })
        else:
            new_domain_list.append(domain)
    return results,new_domain_list,is_valid


def get_domainwhitelist():
    """
    Retrieves the DOMAIN_WHITELIST environment variable.
    Returns:
        str: The solution identifier.
    Raises:
        ConfigError: If DOMAIN_WHITELIST is not set.
    """
    DOMAIN_WHITELIST = os.getenv("DOMAIN_WHITELIST")
    if not DOMAIN_WHITELIST:
        raise ConfigError("DOMAIN_WHITELIST environment variable is not set.")
    return DOMAIN_WHITELIST

def run_bind() -> None:
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

def create_s3_objects(AWS_ACCESS_KEY_ID: str, AWS_SECRET_ACCESS_KEY: str, AWS_REGION: str, S3_BUCKET_NAME: str, S3_OBJECT_KEY: str) -> str:
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

def check_file_exists(file_path: str) -> bool:
    """
    Check if RPZ file exists.
    Args:
        file_path (str): Path to RPZ file. Default value is "/usr/src/app/zones/rpz.db".
    Returns:
        bool: True if RPZ file exists and False if not.
    """
    return os.path.isfile(file_path)

def get_solutionid_env() -> str:
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


def get_verbosity_env() -> str:
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

def get_interval_env() -> str:
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
        return int(EXECUTION_INTERVAL)
    except ValueError:
        raise ConfigError("EXECUTION_INTERVAL must be a valid integer.")


def update_named_config(BIND_SLAVE_IPADDR: str) -> None:
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

def get_aws_env() -> Tuple[str, str, str, str, str, str, str]:
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

def parse_args() -> argparse.Namespace:
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

def setup_logger(verbosity: int) -> None:
    """
    Configures the logging level based on verbosity.
    Args:
        verbosity (int): Verbosity level (0: WARNING, 1: INFO, 2+: DEBUG).
    """
    if verbosity == 0:
        level = logging.WARNING
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=level,
    )

def get_domain_list() -> Set[str]:
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