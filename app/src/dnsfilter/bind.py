import logging
import os
import socket
import json
from typing import Set, List
from pathlib import Path
from exceptions import (
    BindConnectionError,
    BindEnvError,
    BindRPZError,
    
)
from datetime import datetime


def save_domain_list(domain_list: List[str], file_path: str = "/usr/src/app/zones/domain_list.json") -> None:
    """
    Save the list of domains to a JSON file.

    Args:
        domain_list (List[str]): List of domains to save.
        file_path (str): Path to the JSON file. Defaults to "/usr/src/app/zones/domain_list.json".

    Raises:
        IOError: If there is an error writing the file.
        Exception: For any other unexpected errors.
    """
    try:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(sorted(domain_list), f)
    except IOError as e:
        logging.error(f"IO error while saving domain list: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error while saving domain list: {e}")
        raise

def load_domain_list(file_path: str = "/usr/src/app/zones/domain_list.json") -> Set[str]:
    """
    Load the list of domains from a JSON file.

    Args:
        file_path (str): Path to the JSON file. Defaults to "/usr/src/app/zones/domain_list.json".

    Returns:
        Set[str]: A set of domains loaded from the file. Returns an empty set if the file does not exist or is invalid.
    """
    try:
        with open(file_path, 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        logging.debug(f"Domain list file not found: {file_path}")
        return set()
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding domain list JSON: {e}")
        return set()
    except Exception as e:
        logging.error(f"Unexpected error while loading domain list: {e}")
        return set()

def has_domain_list_changed(new_domain_list: List[str], file_path: str = "/usr/src/app/zones/domain_list.json") -> bool:
    """
    Check if the domain list has changed compared to the previously saved list.

    Args:
        new_domain_list (List[str]): The new list of domains to compare.
        file_path (str): Path to the JSON file. Defaults to "/usr/src/app/zones/domain_list.json".

    Returns:
        bool: True if the domain list has changed, False otherwise.
    """
    try:
        old_domain_list = load_domain_list(file_path)
        new_domain_list_sorted = set(sorted(new_domain_list))
        return new_domain_list_sorted != old_domain_list
    except Exception as e:
        logging.error(f"Unexpected error while checking domain list changes: {e}")
        raise

def is_bind_running():
    """
    Check if the BIND server is running by attempting to connect to port 53.

    Returns:
        bool: True if BIND is running, False otherwise.

    Raises:
        BindConnectionError: If there is an unexpected connection error.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('127.0.0.1', 53))
        return True
    except ConnectionRefusedError:
        return False
    except socket.error as e:
        logging.error(f"Unexpected socket error while checking BIND status: {e}")
        raise BindConnectionError(f"Socket error: {e}")
    finally:
        s.close()

def get_bind_env():
    """
    Retrieve the BIND environment variables.

    Returns:
        str: The BIND slave IP address.

    Raises:
        BindEnvError: If the BIND_SLAVE_IPADDR environment variable is missing.
    """
    BIND_SLAVE_IPADDR = os.getenv("BIND_SLAVE_IPADDR")
    if not BIND_SLAVE_IPADDR:
        raise BindEnvError("BIND_SLAVE_IPADDR environment variable is not set.")
    return BIND_SLAVE_IPADDR



def generate_rpz_file(domains: list[str], rpz_file_path: str = "/usr/src/app/zones/rpz.db")  -> None:
    """
    Generate an RPZ (Response Policy Zone) file for BIND.

    Args:
        domains (list[str]): List of domain names to include in the RPZ file.
        rpz_file_path (str): Path to the output RPZ file. If the file exists, it will be overwritten.

    Raises:
        BindRPZError: Raised if the RPZ file cannot be written due to an I/O error or other unexpected exceptions.
    """
    try:
        RPZ_TTL = 60  
        serial = datetime.now().strftime("%y%m%d%H%M")
        # Write the RPZ zone file
        with open(rpz_file_path, 'w') as rpz_file:
            rpz_file.write(f'; UPDATE: 1\n')
            rpz_file.write(f"$TTL {RPZ_TTL}\n")
            rpz_file.write(f"@            IN    SOA  localhost. root.localhost.  (\n")
            rpz_file.write(f"                      {serial}   ; serial\n")
            rpz_file.write(f"                      2M  ; refresh\n")
            rpz_file.write(f"                      1M  ; retry\n")
            rpz_file.write(f"                      5M  ; expiry\n")
            rpz_file.write(f"                      1M) ; minimum\n")
            rpz_file.write(f"              IN    NS    localhost.\n")
            for domain in domains:
                rpz_file.write(f"{domain:<25} CNAME  .\n")

        logging.info(f"RPZ file successfully written to {rpz_file_path}")

    except IOError as e:
        logging.error(f"IO error while writing RPZ file: {e}")
        raise BindRPZError(f"IO error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error while writing RPZ file: {e}")
        raise BindRPZError(f"Unexpected error: {e}")
