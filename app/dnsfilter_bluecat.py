import requests
import sys
import boto3
import os
import json
import argparse
import logging

# BLUECAT Information
BLUECAT_IPADDR = os.getenv("BLUECAT_IPADDR")
BLUECAT_USER = os.getenv("BLUECAT_USER")
BLUECAT_PWD = os.getenv("BLUECAT_PWD")
BLUECAT_TARGET_BDDS = os.getenv("BLUECAT_TARGET_BDDS")
BAM_URL = f"http://{BLUECAT_IPADDR}/api/v2"  


# S3 Information Configuration
S3_OBJECT_KEY_PATH = os.getenv("S3_OBJECT_KEY_PATH")
S3_OBJECT_FILE_NAME = os.getenv("S3_OBJECT_FILE_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_OBJECT_KEY = f"{S3_OBJECT_KEY_PATH}/{S3_OBJECT_FILE_NAME}"


# S3 Session Creation
s3_session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

# S3 Resource Creation
s3_resource = s3_session.resource('s3')
s3_object = s3_resource.Object(S3_BUCKET_NAME, S3_OBJECT_KEY)

# Parse the args 
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Get more debug informations (-v, -vv, -vvv)"
    )
    return parser.parse_args()

# Set the verbosity level
def setup_logger(verbosity: int):
    # Mapping between the args and the verbosity
    if verbosity == 0:
        level = logging.WARNING
    elif verbosity == 1:
        level = logging.INFO
    else:  # -vv ou plus
        level = logging.DEBUG

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=level,
    )


# Function to get domain list from S3 bucket
def get_domain_list():
    try:
        data = s3_object.get()['Body'].read().decode('UTF-8').strip()
        return set(filter(None, data.split('\n')))  # Remove empty lines
    except Exception as e:
        print(f"Error fetching domains: {e}")
        return set()

# Function to log in the Bluecat BAM server
def login():
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
        print("Login failed:", r.text)
        sys.exit(1)

    logging.info("Login OK")

    resp_json = r.json()
    token = resp_json.get("basicAuthenticationCredentials")
    return token


# Function to get the global configuration collection ID
def get_collection_id(token):
    
    headers = {
        "Authorization": f'Basic {token}',
        "accept": "application/hal+json",
        "Content-Type": "application/hal+json"
    }
    r = requests.get(url=f"{BAM_URL}/configurations", headers=headers, verify=False)

 
    resp = r.json()

    if resp.get("data") and len(resp["data"]) > 0:
        collection_id = resp["data"][0]["id"]
    else:
        logging.debug("No configuration found")

    return collection_id

# Function to get the RP Zone ID (if exists)
def get_rpz(token):

    headers = {
        "Authorization": f'Basic {token}',
        "accept": "application/hal+json",
        "Content-Type": "application/hal+json"
    }

    r = requests.get(url=f"{BAM_URL}/responsePolicies?fields=name%2Cconfiguration.id%2Cid&filter=name%3A%22dnsfilter_canal%22", headers=headers, verify=False)

    logging.debug(f" Result of get rpz method : {r.text}")
    resp_json = r.json()
    count = resp_json.get("count")

    if (count != 0):
        rpz_collection_id = resp_json["data"][0]["id"]
    else:
        rpz_collection_id = "None"

    return count,rpz_collection_id

# Function to create the RP Zone
def create_rpz(token,collection_id):

    headers = {
        "Authorization": f'Basic {token}',
        "accept": "application/hal+json",
        "Content-Type": "application/hal+json"
    }
    data = {
        "type": "ResponsePolicy",
        "name": "dnsfilter_canal",
        "policyType": "BLOCKLIST",
        "TTL": 3600
    }

    r = requests.post(url=f"{BAM_URL}/configurations/{collection_id}/responsePolicies", json=data, headers=headers, verify=False)
    resp_json = r.json()
    rpz_collection_id = resp_json.get("id")

    return rpz_collection_id


# Function to create the policy items that will be attached the RP Zone
def create_policy_items(token,rpz_collection_id,domain_list):
    headers = {
        "Authorization": f'Basic {token}',
        "accept": "application/hal+json",
        "Content-Type": "application/hal+json"
    }
    for domain in domain_list:
        data = {"name": domain}
        r = requests.post(url=f"{BAM_URL}/responsePolicies/{rpz_collection_id}/policyItems", json=data, headers=headers, verify=False)


# Function to delete the policy items attached to a RP Zone
def delete_policy_items(token,domain_list):
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


# Function to get the policy items related to a RP Zone
def get_policy_items(token,rpz_collection_id):
    bluecat_domain_list = set()
    headers = {
        "Authorization": f'Basic {token}',
        "accept": "application/hal+json",
        "Content-Type": "application/hal+json"
    }
    r = requests.get(url=f"{BAM_URL}/responsePolicies/{rpz_collection_id}/policyItems", headers=headers, verify=False)

    resp_json = r.json()
    for item in resp_json["data"]:
        
        bluecat_domain_list.add(item["name"])
    logging.debug(f" Bluecat Domain list : {bluecat_domain_list}")
    return bluecat_domain_list

 

# Function to get the BDDS server list
def get_server(token):
    headers = {
        "Authorization": f'Basic {token}',
        "accept": "application/hal+json",
        "Content-Type": "application/hal+json"
    }
    try:
        r = requests.get(url=f"{BAM_URL}/servers", headers=headers, verify=False)


        data = json.loads(r.text)

        # extraire la liste des (id, name)
        server_list = [(srv["id"], srv["name"]) for srv in data["data"]]

        return server_list
    except Exception as e:
        print(f"No server found: {e}")

# Function to deploy the configuration on the BDDS server(s)
def deploy(token,bdds_id):
    headers = {
        "Authorization": f'Basic {token}',
        "accept": "application/hal+json",
        "Content-Type": "application/hal+json"
    }

    data = {  
        "type": "DifferentialDeployment",
        "service": "DNS"
    }

    try:
        for id in bdds_id:
            requests.post(url=f"{BAM_URL}/servers/{id}/deployments", json=data, headers=headers, verify=False)
            logging.debug(f"Configuration deployed on BDDS server identified by id : {id}")
    except Exception as e:
        print(f"Deployment on bdds server failed : {e}")    


def main():
    # Parse the args and set the verbosity level
    args = parse_args()
    setup_logger(args.verbose)

    # Log in the Bluecat BAM server and retrieve a authentication token
    token = login()
    
    logging.debug(f"Token: {token}")

    # Get the RP Zone ID and the Tenant ID (Global configuration ID)
    count,rpz_collection_id = get_rpz(token)
    tenant_id = get_collection_id(token)

    logging.debug(f" >>> Number of RPZ: {count}")


    # If RPZ Zone doesn't exist we create it
    if(count == 0):
        print("tenant id", tenant_id)
        logging.debug(f" >>> Tenant (Global configuration) ID: {tenant_id}")

        rpz_collection_id = create_rpz(token,tenant_id)

    # Fetch the list of domains (Policy items) on Bluecat BAM server
    bluecat_domain_list = get_policy_items(token,rpz_collection_id)
  
    # Fetch the list of domains on AWS
    aws_domain_list = get_domain_list()
    
    # Fetch the domain list that exist on AWS but not on Bluecat server (to add)
    add_domain_list = aws_domain_list - bluecat_domain_list

    # Fetch the domain list that exist on Bluecat server but not on AWS (to delete)
    delete_domain_list = bluecat_domain_list - aws_domain_list

    logging.info(f" >>> Domain list added: {add_domain_list}")
    logging.info(f" >>> Domain list deleted: {delete_domain_list}")

    # If there's domains to add, add them
    if (len(add_domain_list) > 0 ):
        create_policy_items(token,rpz_collection_id,add_domain_list)
    # If there's domains to delete, delete them
    if (len(delete_domain_list) > 0 ):
        delete_policy_items(token,delete_domain_list)
    

    # Fetch the list of BDDS servers managed by the BAM    
    bluecat_server_list = get_server(token)

    # Fetch the BDDS server list defined in the environment variable
    servers_env = os.getenv("BLUECAT_TARGET_BDDS", "")
    target_names = [s.strip() for s in servers_env.split(",") if s.strip()]

    # Intersection → only keep the BDDS IDs whose names match the ones defined in the environment variable
    if (BLUECAT_TARGET_BDDS == "ALL"):
        bdds_ids = [srv_id for srv_id, _ in bluecat_server_list]
    else:
        bdds_ids = [srv_id for srv_id, srv_name in bluecat_server_list if srv_name in target_names]
        if(len(bdds_ids) == 0):
            print("The target bdds servers doesn't match the bdds servers configured")
    
    logging.debug(f" >>> BDDS IDs : {bdds_ids}")

    # Deploy the configuration on the BDDS servers
    if (len(add_domain_list) > 0 or len(delete_domain_list) > 0):
        deploy(token,bdds_ids)


if __name__ == "__main__":
    main()