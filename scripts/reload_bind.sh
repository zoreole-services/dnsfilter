#!/bin/bash

# Path to the rpz.db file
RPZ_FILE="/etc/bind/dnsfilter_zones/rpz.db"
RNDC_PATH=$(command -v rndc || true)

if [ -z "${RNDC_PATH}" ]; then
    echo "Error: 'rndc' command not found in PATH."
    exit 1
fi

echo "Using rndc at: ${RNDC_PATH}"

# Check if the rpz.db file exists
if [ ! -f "${RPZ_FILE}" ]; then
    echo "Error: The file ${RPZ_FILE} does not exist."
    exit 1
fi

# Extract the UPDATE value
UPDATE_VALUE=$(grep -m 1 "^; UPDATE:" "${RPZ_FILE}" | cut -d':' -f2 | tr -d ' ')

# Check if UPDATE is set to 1
if [ "${UPDATE_VALUE}" = "1" ]; then
    echo "UPDATE=1 detected. Reloading BIND..."
    ${RNDC_PATH} reload
    if [ $? -eq 0 ]; then
        echo "BIND successfully reloaded."
        # Reset UPDATE to 0 to avoid unnecessary reloads
        sed -i 's/; UPDATE: 1/; UPDATE: 0/' "${RPZ_FILE}"
    else
        echo "Error reloading BIND."
        exit 1
    fi
else
    echo "UPDATE is not set to 1. No reload needed."
fi