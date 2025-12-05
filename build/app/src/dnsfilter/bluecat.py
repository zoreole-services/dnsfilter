import os
import requests
import logging
import json
from typing import List, Dict, Any, Set, Tuple

from exceptions import (
    BlueCatEnvError,
    BlueCatLoginError,
    BlueCatAPIError,
    BlueCatNotFoundError
)


def get_bluecat_env():
    """
    Retrieves BlueCat environment variables from the system's environment.

    This function fetches the required environment variables for connecting to BlueCat BAM:
    - BLUECAT_IPADDR: IP address of the BlueCat server.
    - BLUECAT_USER: Username for authentication.
    - BLUECAT_PWD: Password for authentication.
    - BLUECAT_TARGET_BDDS: Target BDDS server(s) for deployment.
    - BLUECAT_TENANT_NAME: Tenant name for multi-tenancy support.

    Returns:
        dict: A dictionary containing the BlueCat environment data:
            - user: BlueCat username.
            - password: BlueCat password.
            - target_bdds: Target BDDS server(s).
            - tenant_name: Tenant name.
            - bam_url: Base URL for BlueCat API (constructed from BLUECAT_IPADDR).

    Raises:
        BlueCatEnvError: If any required environment variable is missing or an unexpected error occurs.
    """
    try :
        # BLUECAT Data
        BLUECAT_IPADDR = os.getenv("BLUECAT_IPADDR")
        BLUECAT_USER = os.getenv("BLUECAT_USER")
        BLUECAT_PWD = os.getenv("BLUECAT_PWD")
        BLUECAT_TARGET_BDDS = os.getenv("BLUECAT_TARGET_BDDS")
        BLUECAT_TENANT_NAME = os.getenv("BLUECAT_TENANT_NAME")
        BAM_URL = f"http://{BLUECAT_IPADDR}/api/v2" 

        if None in (BLUECAT_IPADDR, BLUECAT_USER, BLUECAT_PWD, BLUECAT_TARGET_BDDS, BLUECAT_TENANT_NAME):
                    raise BlueCatEnvError("One or several variables is missing.")      
        env_data = {
            "user": BLUECAT_USER,
            "password": BLUECAT_PWD,
            "target_bdds": BLUECAT_TARGET_BDDS,
            "tenant_name": BLUECAT_TENANT_NAME,
            "bam_url": BAM_URL,
        }

        return env_data
    except Exception as e:
        logging.error(f"Get bluecat env failed: {e}")
        raise BlueCatEnvError(f"Error : {e}")


def login(BLUECAT_USER: str,BLUECAT_PWD: str,BAM_URL: str) -> str:
    """
    Authenticates with the BlueCat BAM server and retrieves an authentication token.

    Args:
        BLUECAT_USER (str): Username for BlueCat authentication.
        BLUECAT_PWD (str): Password for BlueCat authentication.
        BAM_URL (str): Base URL for the BlueCat API.

    Returns:
        str: Authentication token for subsequent API calls.

    Raises:
        BlueCatLoginError: If authentication fails, no token is returned, or an unexpected error occurs.
    """
    try:
        headers = {
            "accept": "application/hal+json",
            "Content-Type": "application/hal+json"
        }
        payload = {
            "username": BLUECAT_USER,
            "password": BLUECAT_PWD
        }

        r = requests.post(url=f"{BAM_URL}/sessions", json=payload, headers=headers, verify=False)

        if r.status_code != 201:
            raise BlueCatLoginError(f"Authentication failure : {r.text}")

        logging.info("Login OK")

        resp_json = r.json()
        token = resp_json.get("basicAuthenticationCredentials")
        if not token:
            raise BlueCatLoginError("No token retrieved.")
        return token

    except requests.exceptions.RequestException as e:
        logging.error(f"Request error : {e}")
        raise BlueCatLoginError(f"Request error : {e}")
    except Exception as e:
        logging.error(f"Unexpected error while login : {e}")
        raise BlueCatLoginError(f"Unexpected error: {e}")



def get_collection_id(token: str,BAM_URL: str) -> List[Dict[str, Any]]:
    """
    Retrieves the list of global configuration collections from BlueCat BAM.

    Args:
        token (str): Authentication token for BlueCat API.
        BAM_URL (str): Base URL for the BlueCat API.

    Returns:
        list: A list of configuration collections (each collection is a dictionary with 'id' and 'name').

    Raises:
        BlueCatNotFoundError: If no configurations are found.
        BlueCatAPIError: If an unexpected error occurs during the API request.
    """
    try: 
        headers = {
            "Authorization": f'Basic {token}',
            "accept": "application/hal+json",
            "Content-Type": "application/hal+json"
        }
        r = requests.get(url=f"{BAM_URL}/configurations?fields=id%2Cname", headers=headers, verify=False)

    
        resp = r.json()
        if not resp.get("data") or len(resp["data"]) == 0:
            raise BlueCatNotFoundError("No configuration found.")
        
        return resp["data"]
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error while fetching collection ID : {e}")
        raise BlueCatAPIError(f"Unexpected request : {e}")
    except Exception as e:
        logging.error(f"Unexpected error whicle fetching collection ID : {e}")
        raise BlueCatAPIError(f"Unexpected error : {e}")
    


def get_rpz(token: str, BAM_URL: str) -> Dict[str, Any]:
    """
    Retrieves the Response Policy Zone (RPZ) named 'dnsfilter_canal' from BlueCat BAM.

    Args:
        token (str): Authentication token for BlueCat API.
        BAM_URL (str): Base URL for the BlueCat API.

    Returns:
        dict: A dictionary containing:
            - count: Number of RPZs found.
            - rpz_collection_id: ID of the RPZ if found, otherwise "None".

    Raises:
        BlueCatNotFoundError: If the RPZ 'dnsfilter_canal' is not found.
        BlueCatAPIError: If an unexpected error occurs during the API request.
    """

    try:
        headers = {
            "Authorization": f'Basic {token}',
            "accept": "application/hal+json",
            "Content-Type": "application/hal+json"
        }

        r = requests.get(url=f"{BAM_URL}/responsePolicies?fields=name%2Cconfiguration.id%2Cid&filter=name%3A%22dnsfilter_canal%22", headers=headers, verify=False)

        logging.debug(f" Result of get rpz method: {r.text}")
        resp_json = r.json()
        count = resp_json.get("count")

        if (count != 0):
            rpz_collection_id = resp_json["data"][0]["id"]
        else:
            rpz_collection_id = "None"


        env_data = {
            "count": count,
            "rpz_collection_id": rpz_collection_id,
        }
        return env_data
    except IndexError:
        raise BlueCatNotFoundError("No RPZ named 'dnsfilter_canal' found.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error while fetching RPZ : {e}")
        raise BlueCatAPIError(f"Unexpected request: {e}")
    except Exception as e:
        logging.error(f"Unexpected error while fetching RPZ : {e}")
        raise BlueCatAPIError(f"Unexpected error: {e}")

def create_rpz(token: str, collection_id: str, BAM_URL: str, DNS_TTL: int) -> str:
    """
    Creates a new Response Policy Zone (RPZ) named 'dnsfilter_canal' in BlueCat BAM.

    Args:
        token (str): Authentication token for BlueCat API.
        collection_id (str): ID of the configuration collection where the RPZ will be created.
        BAM_URL (str): Base URL for the BlueCat API.

    Returns:
        str: ID of the newly created RPZ.

    Raises:
        BlueCatAPIError: If the RPZ creation fails or an unexpected error occurs.
    """
    try:
        headers = {
            "Authorization": f'Basic {token}',
            "accept": "application/hal+json",
            "Content-Type": "application/hal+json"
        }
        data = {
            "type": "ResponsePolicy",
            "name": "dnsfilter_canal",
            "policyType": "BLOCKLIST",
            "ttl": f'{DNS_TTL}'
        }

        r = requests.post(url=f"{BAM_URL}/configurations/{collection_id}/responsePolicies", json=data, headers=headers, verify=False)
        resp_json = r.json()
        rpz_collection_id = resp_json.get("id")
        if not rpz_collection_id:
            raise BlueCatAPIError("RPZ creation failed: no ID returned.")

        return rpz_collection_id
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error while creating RPZ: {e}")
        raise BlueCatAPIError(f"Request error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error whicle creating RPZ: {e}")
        raise BlueCatAPIError(f"Unexpected error: {e}")




def create_policy_items(token: str,rpz_collection_id: int,domain_list: List[str],BAM_URL: str) -> None:
    """
    Creates policy items (domains) and attaches them to the specified Response Policy Zone (RPZ).

    Args:
        token (str): Authentication token for BlueCat API.
        rpz_collection_id (str): ID of the RPZ to which the policy items will be attached.
        domain_list (list): List of domains to add as policy items.
        BAM_URL (str): Base URL for the BlueCat API.

    Raises:
        BlueCatAPIError: If a policy item creation fails or an unexpected error occurs.
    """

    try:
        headers = {
        "Authorization": f'Basic {token}',
        "accept": "application/hal+json",
        "Content-Type": "application/hal+json"
        }
        for domain in domain_list:
            data = {"name": domain}
            r = requests.post(url=f"{BAM_URL}/responsePolicies/{rpz_collection_id}/policyItems", json=data, headers=headers, verify=False)
            if r.status_code != 201:
                raise BlueCatAPIError(f"Polciy item creation failed for {domain} : {r.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error while creating policy items: {e}")
        raise BlueCatAPIError(f"Request error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error while creating policy items: {e}")
        raise BlueCatAPIError(f"Unexpected error: {e}")


def delete_policy_items(token: str,domain_list: List[str],BAM_URL: str) -> None:
    """
    Deletes policy items (domains) from BlueCat BAM.

    Args:
        token (str): Authentication token for BlueCat API.
        domain_list (list): List of domains to delete.
        BAM_URL (str): Base URL for the BlueCat API.

    Raises:
        BlueCatAPIError: If an unexpected error occurs during the deletion process.
    """
    try:
        headers = {
            "Authorization": f'Basic {token}',
            "accept": "application/hal+json",
            "Content-Type": "application/hal+json"
        }
        for domain in domain_list:
            url = f"{BAM_URL}/policyItems?fields=id%2Cname&filter=name%3A%22{domain}%22"
            r = requests.get(url=url, headers=headers, verify=False)
        
            logging.debug(f" Result of get policy items method : {r.text}")

            data = r.json()

            if data.get("count", 0) > 0:
                item_id = data["data"][0]["id"]
            else:
                logging.info(f" Domain {domain} not found ")
            logging.debug(f" Item ID : {item_id}")

            requests.delete(url=f"{BAM_URL}/policyItems/{item_id}", headers=headers, verify=False)
    except requests.exceptions.RequestException as e:
        logging.error(f"Erreur de requête lors de la suppression des policy items : {e}")
        raise BlueCatAPIError(f"Erreur de requête : {e}")
    except Exception as e:
        logging.error(f"Erreur inattendue lors de la suppression des policy items : {e}")
        raise BlueCatAPIError(f"Erreur inattendue : {e}")



def get_policy_items(token: str,rpz_collection_id: int,BAM_URL: str) -> Set[str]:
    """
    Retrieves the list of policy items (domains) associated with a Response Policy Zone (RPZ).

    Args:
        token (str): Authentication token for BlueCat API.
        rpz_collection_id (str): ID of the RPZ.
        BAM_URL (str): Base URL for the BlueCat API.

    Returns:
        set: A set of domain names associated with the RPZ.

    Raises:
        BlueCatAPIError: If the API response is malformed or an unexpected error occurs.
    """
    try:
        bluecat_domain_list = set()
        headers = {
            "Authorization": f'Basic {token}',
            "accept": "application/hal+json",
            "Content-Type": "application/hal+json"
        }
        r = requests.get(url=f"{BAM_URL}/responsePolicies/{rpz_collection_id}/policyItems", headers=headers, verify=False)

        resp_json = r.json()
        if "data" not in resp_json:
            raise BlueCatAPIError("No 'data' field in the API response.")
        for item in resp_json["data"]:
            if "name" not in item:
                logging.warning(f"Policy item without 'name' field: {item}")
                continue
            bluecat_domain_list.add(item["name"])
        logging.debug(f" Bluecat Domain list : {bluecat_domain_list}")
        return bluecat_domain_list
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error while fetching policy items: {e}")
        raise BlueCatAPIError(f"Request error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error while fetching policy items: {e}")
        raise BlueCatAPIError(f"Unexpected error: {e}")
 

def get_server(token: str,BAM_URL: str) -> List[Tuple[int, str]]:
    """
    Retrieves the list of BDDS servers from BlueCat BAM.

    Args:
        token (str): Authentication token for BlueCat API.
        BAM_URL (str): Base URL for the BlueCat API.

    Returns:
        list: A list of tuples, where each tuple contains (server_id, server_name).

    Raises:
        BlueCatAPIError: If the API response is malformed or an unexpected error occurs.
    """
    try:
        headers = {
            "Authorization": f'Basic {token}',
            "accept": "application/hal+json",
            "Content-Type": "application/hal+json"
        }
        r = requests.get(url=f"{BAM_URL}/servers", headers=headers, verify=False)
        data = json.loads(r.text)
        if "data" not in data:
            raise BlueCatAPIError("No 'data' field in the API response.")
        server_list = [(srv["id"], srv["name"]) for srv in data["data"]]

        return server_list
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error while fetching servers: {e}")
        raise BlueCatAPIError(f"Request error: {e}")
    except KeyError as e:
        logging.error(f"Unexpected response format while fetching servers: {e}")
        raise BlueCatAPIError(f"Unexpected response format: {e}")
    except Exception as e:
        logging.error(f"Unexpected error while fetching servers: {e}")
        raise BlueCatAPIError(f"Unexpected error: {e}")


def deploy(token: str, bdds_id: List[int], BAM_URL: str) -> None:
    """
    Deploys the RPZ configuration to the specified BDDS server(s).

    Args:
        token (str): Authentication token for BlueCat API.
        bdds_id (list): List of BDDS server IDs to deploy to.
        BAM_URL (str): Base URL for the BlueCat API.

    Raises:
        BlueCatAPIError: If an unexpected error occurs during the deployment process.
    """
    try:
        headers = {
            "Authorization": f'Basic {token}',
            "accept": "application/hal+json",
            "Content-Type": "application/hal+json"
        }

        data = {  
            "type": "DifferentialDeployment",
            "service": "DNS"
        }

        for id in bdds_id:
            requests.post(url=f"{BAM_URL}/servers/{id}/deployments", json=data, headers=headers, verify=False)
            logging.debug(f"Configuration deployed on BDDS server identified by id : {id}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error while deploying configuration: {e}")
        raise BlueCatAPIError(f"Request error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error while deploying configuration: {e}")
        raise BlueCatAPIError(f"Unexpected error: {e}")