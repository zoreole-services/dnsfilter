
from datetime import datetime
import logging
import os
import socket
import subprocess
import json
from typing import Set, List
from pathlib import Path


from exceptions import (
    BindConnectionError,
    BindEnvError,
    BindRPZError,
    
)


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
        # Ensure the directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        # Save the sorted list of domains to a JSON file
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
        # Load the list of domains from the JSON file
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
        # Load the old domain list
        old_domain_list = load_domain_list(file_path)

        # Sort and convert the new domain list to a set for comparison
        new_domain_list_sorted = set(sorted(new_domain_list))

        # Check if the new domain list is different from the old one
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

 




def generate_rpz_file(domains, rpz_file_path="/usr/src/app/zones/rpz.db"):
    """
    Generate an RPZ (Response Policy Zone) file for BIND.

    Args:
        domains (list): List of domains to include in the RPZ.
        rpz_file_path (str): Path to the output RPZ file.

    Raises:
        BindRPZError: If there is an error writing the RPZ file.
    """
    try:
        RPZ_TTL = 60  # Time-to-live for RPZ entries

        # Generate serial in YYMMDDHHMM format
        serial = datetime.now().strftime("%y%m%d%H%M")



        # Write the RPZ zone file
        with open(rpz_file_path, 'w') as rpz_file:
            rpz_file.write(f'; UPDATE: 1\n')
            rpz_file.write(f"$TTL {RPZ_TTL}\n")
            rpz_file.write(f"@            IN    SOA  localhost. root.localhost.  (\n")
            rpz_file.write(f"                      {serial}   ; serial\n")
            rpz_file.write(f"                      5M  ; refresh\n")
            rpz_file.write(f"                      1M  ; retry\n")
            rpz_file.write(f"                      1W  ; expiry\n")
            rpz_file.write(f"                      1H) ; minimum\n")
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
