import logging
import time
import os
from pathlib import Path
from typing import Iterable, Dict, Set
from core import (
    setup_logger,
    parse_args,
    get_solutionid_env,
    get_interval_env,
    update_named_config,
    run_bind,
    get_domain_list,
    get_domain_list_test,
    check_file_exists,
    get_verbosity_env,
    validate_domains,
)
from bluecat import (
    login,
    get_rpz,
    get_bluecat_env,
    create_policy_items,
    get_collection_id,
    create_rpz,
    get_policy_items,
    delete_policy_items,
    deploy,
    get_server,
)
from bind import (
    generate_rpz_file,
    get_bind_env,
    is_bind_running,
    save_domain_list,
    has_domain_list_changed,
)
from exceptions import (
    BlueCatError,
    BindError,
    AWSError,
    ConfigError,
    CoreError,
)

def execute_bindlocal_or_transfer(SOLUTION_IDENTIFIER: str, BIND_SLAVE_IPADDR: str, domain_list: Iterable[str], rpz_file_path: str, DNS_TTL: int) -> None:
    """
    Execute BINDLOCAL or BINDTRANSFER solution.
    Args:
        SOLUTION_IDENTIFIER (str): Comma-separated solution identifiers.
        BIND_SLAVE_IPADDR (str): IP address of slave DNS server.
        domain_list (Iterable[str]): Domains to include in RPZ.
        rpz_file_path (str): Destination RPZ file path.
        domain_list_file_path (str): Domain list file path.

    Returns:
        None
    """
    solutions = [sol.strip() for sol in SOLUTION_IDENTIFIER.split(",")]
    if "BINDTRANSFER" in solutions :
        if is_bind_running():
            logging.info("Bind9 (named) is already running.")
        else:
            logging.info("Starting Bind9 (named)...")
            update_named_config(BIND_SLAVE_IPADDR)
            run_bind()
    
    generate_rpz_file(domain_list, DNS_TTL, rpz_file_path)

def execute_bluecat_api(get_bluecat_env_data: Dict[str, str], domain_list: Set[str], DNS_TTL: int) -> None:
    """
    Execute BLUECATAPI solution
    Args:
        get_bluecat_env_data (dict): BlueCat configuration dictionary containing:
            - "user": BAM login username.
            - "password": BAM login password.
            - "bam_url": URL of the BlueCat API.
            - "tenant_name": list of tenants.
            - "target_bdds": Target BDDS names.
        domain_list (set): Set of domains retrieved from AWS.
    Raises:
        BlueCatAPIError: If a BlueCat API request fails.
        KeyError: If a required configuration key is missing.
        Exception: For any unexpected error during processing.
    Returns:
        None
    """
    BLUECAT_USER = get_bluecat_env_data["user"]
    BLUECAT_PWD = get_bluecat_env_data["password"]
    BAM_URL = get_bluecat_env_data["bam_url"]
    BLUECAT_TENANT_NAME = get_bluecat_env_data["tenant_name"]
    BLUECAT_TARGET_BDDS = get_bluecat_env_data["target_bdds"]

    token = login(BLUECAT_USER, BLUECAT_PWD, BAM_URL)
    get_rpz_data = get_rpz(token, BAM_URL)
    count = get_rpz_data["count"]
    rpz_collection_id = get_rpz_data["rpz_collection_id"]
    tenant_list_bam = get_collection_id(token, BAM_URL)

    names = [n.strip() for n in BLUECAT_TENANT_NAME.split(",")]
    tenant_ids = [item["id"] for item in tenant_list_bam if item["name"] in names]

    for tenant_id in tenant_ids:
        logging.debug(f"Processing tenant ID: {tenant_id}")
        if count == 0:
            logging.info("No existing RPZ found. Creating a new one...")
            rpz_collection_id = create_rpz(token, tenant_id, BAM_URL, DNS_TTL)

        bluecat_domain_list = get_policy_items(token, rpz_collection_id, BAM_URL)
        aws_domain_list = domain_list

        add_domain_list = set(aws_domain_list) - set(bluecat_domain_list)
        delete_domain_list = set(bluecat_domain_list) - set(aws_domain_list)

        logging.info(f"Domains to add: {add_domain_list}")
        logging.info(f"Domains to delete: {delete_domain_list}")

        if len(add_domain_list) > 0:
            create_policy_items(token,rpz_collection_id,add_domain_list,BAM_URL)
        if len(delete_domain_list) > 0:
            delete_policy_items(token,delete_domain_list,BAM_URL)

        bluecat_server_list = get_server(token, BAM_URL)
        target_names = [s.strip() for s in BLUECAT_TARGET_BDDS.split(",") if s.strip()]

        if BLUECAT_TARGET_BDDS == "ALL":
            bdds_ids = [srv_id for srv_id, _ in bluecat_server_list]
        else:
            bdds_ids = [srv_id for srv_id, srv_name in bluecat_server_list if srv_name in target_names]
            if len(bdds_ids) == 0:
                logging.error("The target BDDS servers don't match the configured servers.")

        if len(add_domain_list) > 0 or len(delete_domain_list) > 0:
            deploy(token,bdds_ids,BAM_URL)
            logging.info("Configuration deployed.")
        else:
            logging.info("No changes to deploy.")

def main():
    try:
        DNS_TTL = os.getenv("DNS_TTL")
        domain_list_file_path = Path("/tmp/domain_list.json")
        rpz_file_path = Path("/usr/src/app/zones/rpz.db")

        VERBOSITY = get_verbosity_env()
        args = parse_args()
        if (args.verbose > VERBOSITY):
            setup_logger(args.verbose)
        else:
            setup_logger(VERBOSITY)

        SOLUTION_IDENTIFIER = get_solutionid_env()
        EXECUTION_INTERVAL = get_interval_env()
        
        #domain_list = get_domain_list()
        domain_list = get_domain_list_test()

        result,domain_list = validate_domains(domain_list)
        logging.info(f"Result {result}")
        logging.info(f"new domain list: {domain_list}")

        logging.info(f"Domain list retrieved: {domain_list}")

        solutions = [sol.strip() for sol in SOLUTION_IDENTIFIER.split(",")]
        
        for solution in solutions:

            logging.info(f"#### Solution: {solution} #####")
            if domain_list:

                logging.info(f"Retrieved {len(domain_list)} domains.")
                
                if check_file_exists(domain_list_file_path):
                    if has_domain_list_changed(domain_list, domain_list_file_path):
                        if solution == "BINDTRANSFER" or solution == "BINDLOCAL":
                            BIND_SLAVE_IPADDR = get_bind_env()
                            logging.info("Domain list has changed. Generating new RPZ file...")
                            execute_bindlocal_or_transfer(SOLUTION_IDENTIFIER, BIND_SLAVE_IPADDR, domain_list, rpz_file_path, DNS_TTL)
                        if solution == "BLUECATAPI":
                            BLUECAT_ENV_DATA = get_bluecat_env()
                            logging.info("Domain list has changed. Push modifications on BLUECAT Server")
                            execute_bluecat_api(BLUECAT_ENV_DATA, domain_list, DNS_TTL)
                    else:
                        logging.info("Domain list has not changed. No need to take actions.")
                
                else:
                    if solution == "BINDTRANSFER" or solution == "BINDLOCAL":
                        BIND_SLAVE_IPADDR = get_bind_env()
                        execute_bindlocal_or_transfer(SOLUTION_IDENTIFIER, BIND_SLAVE_IPADDR, domain_list, rpz_file_path, DNS_TTL)
                    if solution == "BLUECATAPI":
                        BLUECAT_ENV_DATA = get_bluecat_env()
                        execute_bluecat_api(BLUECAT_ENV_DATA, domain_list, DNS_TTL)

            else:
                logging.info("No domains retrieved.")
        save_domain_list(domain_list, domain_list_file_path)

        time.sleep(EXECUTION_INTERVAL)

    except BindError as e:
        logging.error(f"BIND error: {e}")
        return 1
    except AWSError as e:
        logging.error(f"AWS error: {e}")
        return 1
    except ConfigError as e:
        logging.error(f"Configuration error: {e}")
        return 1
    except CoreError as e:
        logging.error(f"Core error: {e}")
        return 1
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return 1

if __name__ == '__main__':
    main()
