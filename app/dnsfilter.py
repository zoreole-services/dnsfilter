#!/usr/bin/env python3

import boto3
import os
from datetime import datetime

S3_OBJECT_KEY_PATH = os.getenv("S3_OBJECT_KEY_PATH")
S3_OBJECT_FILE_NAME = os.getenv("S3_OBJECT_FILE_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# RPZ Configuration
RPZ_FILE_PATH = "../zones/rpz.db"  # Update with your desired output path
RPZ_TTL = 60  # Time-to-live for RPZ entries

# S3 Information Configuration
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

# Function to get domain list from S3 bucket
def get_domain_list():
    try:
        data = s3_object.get()['Body'].read().decode('UTF-8').strip()
        return set(filter(None, data.split('\n')))  # Remove empty lines
    except Exception as e:
        print(f"Error fetching domains: {e}")
        return set()

# Function to generate RPZ zone file
def generate_rpz_file(domains):
    try:
        # Get the current serial in YYMMDDnn format
        serial = datetime.now().strftime("%y%m%d%H%M")
        # Write the RPZ zone file
        with open(RPZ_FILE_PATH, 'w') as rpz_file:
            rpz_file.write(f"$TTL {RPZ_TTL}\n")
            rpz_file.write(f"@            IN    SOA  localhost. root.localhost.  (\n")
            rpz_file.write(f"                      {serial}   ; serial\n")  # Dynamic serial
            rpz_file.write(f"                      3H  ; refresh\n")
            rpz_file.write(f"                      1H  ; retry\n")
            rpz_file.write(f"                      1W  ; expiry\n")
            rpz_file.write(f"                      1H) ; minimum\n")
            rpz_file.write(f"              IN    NS    localhost.\n")
            
            for domain in domains:
                rpz_file.write(f"{domain:<25} CNAME  .\n")
        
        print(f"RPZ file successfully written to {RPZ_FILE_PATH}")
    except Exception as e:
        print(f"Error writing RPZ file: {e}")



if __name__ == '__main__':
    print("Fetching domain list from S3...")
    domain_list = get_domain_list()
    if domain_list:
        print(f"Retrieved {len(domain_list)} domains.")
        generate_rpz_file(domain_list)
    else:
        print("No domains retrieved. Check S3 configuration or data.")
