# DNS Filter

  

**DNS Filter** is a [Python](https://www.python.org) package that retrieves a list of domains from a file stored in an [S3](https://aws.amazon.com/s3/) bucket using the [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) library, filters them, and converts them into a rpz file that will be taken in account the DNS servers.

  

**DNS Filter** operates within a [Docker](https://www.docker.com) container, making it easy to deploy and manage.

  


## Prerequisites

  

Before you begin, ensure you have the following:

  

-  **Docker**: Follow the official Docker installation guide for your Linux distribution.

- [Docker Installation Guide for Debian](https://docs.docker.com/engine/install/debian/)

- [Docker Installation Guide for Rocky Linux](https://docs.rockylinux.org/gemstones/containers/docker/)

    

## Installation

  

1.  **Clone the Repository**:

  

```bash

git clone https://github.com/zoreole-services/dnsfilter.git

```

  
  

## Configuration

  

1.  **Docker Compose Configuration**:

  

We recommend using [Docker Compose](https://docs.docker.com/compose/) for managing the DNS Filter service. An example configuration is available in `docker-compose.yaml.example`. You can copy this file to `docker-compose.yaml` and modify it to adjust settings such as ports, volumes, or environment variables.

  

To configure DNS Filter, you'll need to add the following environment variables:

  

| Variable Name | Default Value | Required | Description |

|------------------------|------------------|----------|--------------------------------------------------|

| `AWS_ACCESS_KEY_ID` | - | Yes | Your AWS access key ID for accessing the S3 bucket. |

| `AWS_SECRET_ACCESS_KEY`| - | Yes | Your AWS secret access key for accessing the S3 bucket. |

| `AWS_REGION` | `eu-west-1` | No | The AWS region where the S3 bucket is located. |

| `S3_BUCKET_NAME` | - | Yes | The name of the S3 bucket where the IP list is stored. |

| `S3_OBJECT_KEY_PATH` | - | Yes | The path within the S3 bucket where IP list is located. |

| `S3_OBJECT_FILE_NAME` | - | Yes | The name of the file containing IP addresses to blackhole. |

| `MY_SUPERNETS` | - | Yes | Your public network's supernets. |

| `MAX_PREFIXES` | `2000` | No | Maximum number of routes to accept. |

| `BLACKHOLE_COMMUNITY` | `65535:666` | No | BGP community value for blackhole routes. |

| `POLLING_INTERVAL` | `30` | No | Interval (in seconds) for polling changes from S3 bucket. |

  




  
  

You can add these environment variables to the `environment` section of the `dnsfilter` service in the `docker-compose.yaml` file.

  

##

  

2.  **Bind9 configuration**:

  

You'll need to add those lines to your named.conf.local file:

  

```zone "rpz" {

type master;

file "/etc/bind/zones/rpz.db"; # Replace with the actual path

allow-query { none; }; # RPZ zones should not be directly queried

};

```

Then you’ll need to add those parameters to the named.conf.options file:

  

```recursion yes;

allow-query { any; };

response-policy { zone "rpz"; };

```

  

For more advanced configurations and additional parameters, refer to the documentation of Bind9.

  
  

3.  **Crontab configuration**:

  

We recommend to launch « crontab -e » command and edit the crontab file as following:

  
  

```

*/30 * * * * docker exec dnsfilter python3 dnsfilter.py && /usr/sbin/rndc reload

```

  

## Usage

  

Once the installation is complete and the configuration files are set up, you can use the following commands:

  

**Starting the Docker container**:

  

```bash

docker  compose  up  -d

```

  

**Stopping the Docker container**:

  

```bash

docker  compose  down

```

  

**Rebuilding the Docker image**:

  

```bash

docker  compose  build  dnsfilter

docker  compose  down && docker  compose  up  -d

```

  

## License

  

This project is licensed under the [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.txt).

  

## Issue

  

If you encounter any issues or have questions, please [submit an issue](https://github.com/zoreole-services/tvfilter/issues) on the GitHub repository.




  

# DNS Filter Bluecat

  

**DNS Filter Bluecat** is a [Python](https://www.python.org) package that retrieves a list of domains from a file stored in an [S3](https://aws.amazon.com/s3/) bucket using the [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) library, filters them, and add them to Bluecat server using it's REST API v2.

  

**DNS Filter Bluecat** operates within a [Docker](https://www.docker.com) container, making it easy to deploy and manage.

  
  ## Prerequisites

  

Before you begin, ensure you have the following:

  

-  **Docker**: Follow the official Docker installation guide for your Linux distribution.

- [Docker Installation Guide for Debian](https://docs.docker.com/engine/install/debian/)

- [Docker Installation Guide for Rocky Linux](https://docs.rockylinux.org/gemstones/containers/docker/)


## Installation

  

1.  **Clone the Repository**:

  

```bash

git clone https://github.com/zoreole-services/dnsfilter.git 
```
  

## Configuration

  

1.  **Docker Compose Configuration**:


To configure DNS Filter Bluecat, you'll need to add the following environment variables:

  
| Variable Name | Default Value | Required | Description | 
|--|--|--| -- |
| `BLUECAT_USER`  | - | Yes | Your user for accessing Bluecat BAM server.|
| `BLUECAT_PWD`  | - | Yes | Your secret password secret accessing Bluecat BAM server.|
| `BLUECAT_IPADDR`  | - | Yes | IP address of Bluecat BAM server.|
| `BLUECAT_TARGET_BDDS` | - | No | The name of the target Bluecat BDDS servers. |



You can add these environment variables to the `environment` section of the `dnsfilter` service in the `docker-compose.yaml` file.


2.  **Crontab configuration**:

  

We recommend to launch « crontab -e » command and edit the crontab file as following:

  
  

```

*/30 * * * * docker exec dnsfilter python3 dnsfilter_bluecat.py 
```




## Usage

  

Once the installation is complete and the configuration files are set up, you can use the following commands:

  

**Starting the Docker container**:

  

```bash

docker  compose  up  -d

```

  

**Stopping the Docker container**:

  

```bash

docker  compose  down

```

  

**Rebuilding the Docker image**:

  

```bash

docker  compose  build  dnsfilter

docker  compose  down && docker  compose  up  -d


## License

  

This project is licensed under the [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.txt).

  

## Issue

  

If you encounter any issues or have questions, please [submit an issue](https://github.com/zoreole-services/tvfilter/issues) on the GitHub repository.
