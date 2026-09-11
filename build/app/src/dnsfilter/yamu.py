
import json
import urllib.parse
import urllib3
import requests
import logging
import os
import re
import itertools

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from exceptions import (
    YamuEnvError,
    YamuAPIError,
)


def get_yamu_env() -> list:
    """
    Retrieves and parses every Yamu environment defined via SRV<N> environment variables.

    Each SRV<N> variable describes one Yamu appliance (one set of credentials/protocol/IP), in this fixed field order (comma-separated):
        username,password,view_name,api_protocol,scope,ipaddr

    The view_name and scope fields may themselves each hold several values, separated by ";" -- one environment is generated for every
    combination.

    Example:
        SRV1="admin,xxxx,viewA;viewB,https,/global/default,10.0.0.1"
        -> 2 environments on the same appliance (1 scope x 2 views)

        SRV2="admin2,yyyy,viewXX,https,/global/a;/global/b,10.0.0.2"
        -> 2 environments on a second appliance (2 scopes x 1 view)
    Returns:
        list[dict]: One dict per environment, each containing:
            name, url, username, password, scope, view_name.

    Raises:
        YamuEnvError: If no SRV<N> variable is found, or if one is
        malformed (wrong number of fields, invalid protocol, empty field).
    """
    srv_pattern = re.compile(r"^SRV(\d+)$")
    srv_vars = sorted(
        (int(m.group(1)), name)
        for name in os.environ
        for m in [srv_pattern.match(name)] if m
    )

    if not srv_vars:
        raise YamuEnvError("No SRV<N> environment variable found (e.g. SRV1).")

    environments = []
    for _, var_name in srv_vars:
        raw_value = os.getenv(var_name, "")
        fields = [f.strip() for f in raw_value.split(",")]

        if len(fields) != 6:
            raise YamuEnvError(
                f"{var_name} must have exactly 6 comma-separated fields "
                f"(username,password,view_name,api_protocol,scope,ipaddr), "
                f"got {len(fields)}: {raw_value!r}"
            )

        username, password, view_name_field, api_protocol, scope_field, ipaddr = fields
        api_protocol = api_protocol.lower()

        if api_protocol not in ("http", "https"):
            raise YamuEnvError(
                f"{var_name}: api_protocol must be 'http' or 'https', got {api_protocol!r}"
            )

        view_names = [v.strip() for v in view_name_field.split(";") if v.strip()]
        scopes = [s.strip() for s in scope_field.split(";") if s.strip()]

        if not all([username, password, ipaddr]) or not view_names or not scopes:
            raise YamuEnvError(f"{var_name}: one or more fields are empty: {raw_value!r}")

        for scope, view_name in itertools.product(scopes, view_names):
            environments.append({
                "name": f"{var_name}:{ipaddr}{scope}/{view_name}",
                "url": f"{api_protocol}://{ipaddr}",
                "username": username,
                "password": password,
                "scope": scope,
                "view_name": view_name,
            })

    return environments

def delete_forced_resolution(domain_or_library: str, scope: str, url: str, username: str, password: str, view_name: str = "default", record_type: str = "A", entry_type: str = "domain") -> None:
    """
    Deletes an existing forced resolution rule from the Yamu appliance.
    Args:
        domain_or_library (str): Literal domain name, or domain library name.
        scope (str): Effect range scope for the rule.
        url (str): Base URL of the Yamu appliance.
        username (str): Basic Auth username.
        password (str): Basic Auth password.
        view_name (str, optional): DNS view name.
        record_type (str, optional): DNS record type.
        entry_type (str, optional): "domain" or "domainlibrary".
    Returns:
        None
    Raises:
        YamuAPIError: If a Yamu API request fails.
    """
    try: 
        encoded_domain = urllib.parse.quote(domain_or_library, safe="")
        path = (
            f"/openapi/secure/xforce/view/{urllib.parse.quote(view_name, safe='')}"
            f"/type/{urllib.parse.quote(entry_type, safe='')}"
            f"/qtype/{urllib.parse.quote(record_type, safe='')}"
            f"/domain/{encoded_domain}"
        )
    
        resp = requests.delete(
            url + path,
            json={"scope": scope},
            auth=(username, password),
            headers={"Content-Type": "application/json"},
            verify=False,
            timeout=10,
        )
        logging.info(f"Delete forced resolution function - Status code: {resp.status_code}")
        try:
            logging.info(f"Delete forced resolution function -  JSON: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
        except ValueError:
            logging.error(f"Delete forced resolution function -  RAW: {resp.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error : {e}")
        raise YamuAPIError(f"Request error : {e}")

 
def create_forced_resolution(url: str, domains: list[str], scope: str, view_name: str, username: str, password: str, record_type: str = "A", entry_type: str = "domain", ttl: int = 60, policyType: str = "nxdomain", remark: str ="C+ DNSFilter") -> None:
    """
    Create a forced resolution rule from the Yamu appliance.

    Args:
        url (str): Base URL of the Yamu appliance.
        domains (List[str]) Domains list to add.
        scope (str): Effect range scope for the rule.
        view_name (str, optional): DNS view name.
        username (str): Basic Auth username.
        password (str): Basic Auth password.
        record_type (str, optional): DNS record type.
        entry_type (str, optional): "domain" or "domainlibrary".
        ttl (int, optional): TTL of the new entries.
        policyType (str, optional): Enforcement action.
        remark (str, optional): Comments added to the new entries.
    Returns:
        None
    Raises:
        YamuAPIError: If a Yamu API request fails.
    """
    try: 
        if isinstance(domains, str):
            domains = [domains]
    
        payload = [{
            "scope": scope,
            "viewName": view_name,
            "type": entry_type,
            "domains": domains,
            "qtype": record_type,
            "policyType": policyType,
            "ttl": ttl,
            "enabled": True,
            "remark": remark,
        }]
    
        resp = requests.post(
            url + "/openapi/secure/xforce",
            json=payload,
            auth=(username, password),
            headers={"Content-Type": "application/json"},
            verify=False,
            timeout=10,
        )
        logging.info(f"Create forced resolution function - Status code: {resp.status_code}")
        try:
            logging.info(f"Create forced resolution function -  JSON: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
            
        except ValueError:
            logging.error(f"Create forced resolution function -  RAW: {resp.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error : {e}")
        raise YamuAPIError(f"Request error : {e}")        

def get_forced_resolution_domains(url: str, username: str, password: str, page_size: int = 50, scope: str = None, view_name: str = None) -> list:
    """
    Retrieves the Forced resolution domains names from Yamu appliance.

    Args:
        url (str): Base URL of the Yamu appliance.
        username (str): Basic Auth username.
        password (str): Basic Auth password.
        page_size (int, optional): Page size for pagination.
        scope (str, optional): If set, only keep entries matching this
            effect range scope (e.g. "/global/default").
        view_name (str, optional): If set, only keep entries matching
            this DNS view name.

    Returns:
        list[str]: Domain names.
    Raises:
        YamuAPIError: If a Yamu API request fails.
    """
    try:
        entries = get_forced_resolution_entries(url, username, password, page_size, scope, view_name)
        return [entry["domain"] for entry in entries if "domain" in entry]
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error : {e}")
        raise YamuAPIError(f"Request error : {e}")


def get_forced_resolution_entries(url: str, username: str, password: str, page_size: int = 50, scope: str = None, view_name: str = None) -> list:
    """
    Retrieves the Forced resolution entries from Yamu appliance.

    Args:
        url (str): Base URL of the Yamu appliance.
        username (str): Basic Auth username.
        password (str): Basic Auth password.
        page_size (int, optional): Page size for pagination.
        scope (str, optional): If set, only keep entries matching this
            effect range scope (e.g. "/global/default") -- essential once
            several scopes/views are managed on the same appliance, so a
            diff never mixes domains from different environments.
        view_name (str, optional): If set, only keep entries matching
            this DNS view name.

    Returns:
        list[dict]: Raw forced resolution rule entries.
    Raises:
        YamuAPIError: If a Yamu API request fails.
    """
    try:
        entries = []
        page = 1
        while True:
            resp = requests.get(
                url + "/openapi/secure/xforce",
                params={"page": page, "pageSize": page_size},
                auth=(username, password),
                headers={"Content-Type": "application/json"},
                verify=False,
                timeout=10,
            )
            try:
                data = resp.json()
            except ValueError:
                logging.info(f"RAW answer: {resp.text} ")
                break

            if data.get("rcode") != 0:
                logging.error(f"Erreur API: {json.dumps(data, indent=2, ensure_ascii=False)}")
                break

            page_entries = data.get("data", {}).get("list", [])
            entries.extend(page_entries)

            total = data.get("data", {}).get("total", 0)
            if not page_entries or page * page_size >= total:
                break
            page += 1

        if scope is not None:
            scope_parts = [p for p in scope.strip("/").split("/") if p]
            entries = [e for e in entries if e.get("effectRange") and e["effectRange"][0] == scope_parts]
        if view_name is not None:
            entries = [e for e in entries if e.get("viewName") == view_name]

        return entries
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error : {e}")
        raise YamuAPIError(f"Request error : {e}")