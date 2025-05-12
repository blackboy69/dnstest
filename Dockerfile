# Use an official Python runtime as a parent image
# Using a slim variant reduces the image size
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script into the container at /app
COPY dnstest.py .

# --- Important Notes on Running the Container ---
#
# 1. DNS for the Script's Test:
#    - This script *explicitly asks* the user for the DNS server(s) to test.
#    - It uses `dnspython` configured to query *those specific servers*, ignoring
#      the container's own /etc/resolv.conf for the actual performance test queries.
#
# 2. DNS for the Container (e.g., for downloading the domain list):
#    - By default, the container uses the DNS settings configured for the Docker daemon
#      (often inherited from the host).
#    - The `requests.get()` call in the script to download the Cisco Umbrella list
#      *will* use the container's configured DNS servers.
#    - If the default DNS doesn't work for downloading the list (e.g., in restricted networks),
#      you can specify DNS servers for the container at runtime using the '--dns' flag:
#      'docker run --dns 8.8.8.8 --dns 1.1.1.1 <image_name>'
#
# 3. Network Access:
#    - The container needs network access to:
#      a) Download the domain list (via HTTPS to s3-us-west-1.amazonaws.com).
#      b) Reach the DNS server(s) the user specifies for the test (via UDP/TCP port 53).
#    - Docker's default bridge network usually allows this for public IPs.
#    - If testing DNS servers on a private/local network (like the script's default 192.168.0.2),
#      ensure the Docker host can reach that IP and that Docker's network configuration
#      (or using '--network host') allows the container to reach it.


# Define the command to run the script when the container starts
# This allows 'docker run <image_name>' to execute the script directly.
ENTRYPOINT ["python", "dnstest.py"]

