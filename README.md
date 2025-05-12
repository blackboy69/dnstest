# DNS Performance Tester

This Python script is designed to test the performance of DNS (Domain Name System) servers by sending a configurable number of DNS queries for popular domains and measuring the response times. It calculates various statistics, including average, median, min/max query times, and overall Queries Per Second (QPS).

The script can download the Cisco Umbrella top 1 million domains list or use a local fallback list if the download fails or is skipped. It utilizes asyncio for concurrent DNS queries to simulate a more realistic load and provide faster results.

## Features

-   **DNS Server Performance Testing**: Measure the speed and reliability of one or more DNS servers.
-   **Customizable Domain List**:
    -   Option to download and use the Cisco Umbrella top 1 million public domains list.
    -   Uses a local copy (`top-1m.csv`) if already downloaded.
    -   Falls back to a predefined list of common domains if the download fails or for small test runs.
    -   User can specify the number of top domains to query.
-   **Concurrent Queries**: Utilizes `asyncio` to send multiple DNS queries concurrently, improving testing efficiency.
-   **Configurable Query Parameters**:
    -   Specify DNS server IP addresses.
    -   Set the query type (e.g., 'A', 'AAAA', 'MX').
    -   Adjust query timeout.
    -   Control the number of concurrent requests.
-   **Detailed Statistics**:
    -   Total domains tested and processing time.
    -   Number of successful and failed lookups.
    -   Breakdown of errors by type (NXDOMAIN, NoAnswer, Timeout, etc.).
    -   For successful lookups:
        -   Average, median, minimum, and maximum query times (in milliseconds).
        -   Standard deviation of query times.
        -   Overall average QPS.
-   **Live Progress**: Displays real-time progress, including the percentage of domains tested, current QPS, and counts of successful/failed lookups.
-   **User-Friendly Input**: Prompts the user for the number of domains to test and the DNS server(s) to use.

## Requirements

The script requires Python 3.7+ and the following libraries:

-   `dnspython` (for DNS resolution)
-   `requests` (for downloading the domain list)

You can install them using pip:

    pip install dnspython requests

## How to Use

1.  **Save the script**: Save the code as a Python file (e.g., `dns_tester.py`).
2.  **Run the script**: Execute it from your terminal:

        python dns_tester.py

3.  **Enter Number of Domains**:
    -   The script will first attempt to download or locate the `top-1m.csv` file.
    -   It will then ask: `How many top domains do you want to test? (default: 10000):`
    -   Press Enter to use the default, or type a number and press Enter.
4.  **Enter DNS Servers**:
    -   Next, it will ask: `Enter DNS server(s) to test, separated by commas (default: 192.168.0.2):`
    -   Press Enter to use the default DNS server (`192.168.0.2`).
    -   To test other servers, enter their IP addresses separated by commas (e.g., `8.8.8.8,1.1.1.1`).

The test will then begin, showing live progress. Once completed, a summary of the results will be displayed.

## Configuration

The following variables at the beginning of the script can be modified to change its default behavior:

-   `CISCO_UMBRELLA_URL`: URL to download the Cisco Umbrella top 1 million domains list.
    -   Default: `"https://s3-us-west-1.amazonaws.com/umbrella-static/top-1m.csv.zip"`
-   `LOCAL_CSV_FILENAME`: Filename for the local copy of the domain list.
    -   Default: `"top-1m.csv"`
-   `DEFAULT_DOMAINS_TO_TEST_COUNT`: Default number of domains to test if the user doesn't specify.
    -   Default: `10000`
-   `FALLBACK_DOMAINS`: A small list of domains used if the main list cannot be downloaded/loaded or if a very small number of domains is requested.
-   `DEFAULT_DNS_SERVER`: Default DNS server IP if the user doesn't provide one.
    -   Default: `"192.168.0.2"`
-   `QUERY_TYPE`: Type of DNS record to query (e.g., 'A', 'AAAA', 'MX', 'CNAME', 'TXT').
    -   Default: `'A'`
-   `TIMEOUT`: Timeout in seconds for each individual DNS query.
    -   Default: `2.0`
-   `CONCURRENT_REQUESTS`: Number of DNS queries to perform concurrently.
    -   Default: `50`

## Output

After the test completes, the script will print a "Test Summary" including:

-   **DNS Servers Tested**: The IP addresses of the DNS servers used.
-   **Total Domains Tested**: The actual number of domains queried.
-   **Total Processing Time**: The duration of the querying phase.
-   **Successful Lookups**: Count of queries that received a valid response.
-   **Failed Lookups**: Count of queries that failed (timeout, NXDOMAIN, etc.).
-   **Error Breakdown** (if any errors):
    -   Lists each error type (e.g., `NXDOMAIN`, `Timeout`, `NoAnswer`) and the number of times it occurred.
-   **Performance Metrics** (for successful lookups):
    -   **Average Query Time**: Mean response time.
    -   **Median Query Time**: Midpoint response time, less affected by outliers.
    -   **Min Query Time**: Fastest response time.
    -   **Max Query Time**: Slowest response time.
    -   **Standard Deviation**: A measure of the dispersion of query times.
    -   **Overall Average QPS**: The total number of domains tested divided by the total processing time.

## Error Handling

The script includes handling for various potential issues:

-   **Domain List Download/Extraction Failure**: If downloading or extracting the Cisco Umbrella list fails, it will attempt to use the `FALLBACK_DOMAINS`.
-   **CSV File Issues**: If the `top-1m.csv` file is not found or is malformed, it will try the `FALLBACK_DOMAINS`.
-   **No Domains Loaded**: If no domains can be loaded from any source, it uses a minimal internal list and issues a critical warning.
-   **DNS Query Errors**: Catches common `dnspython` exceptions:
    -   `dns.resolver.NXDOMAIN`: Domain does not exist.
    -   `dns.resolver.NoAnswer`: The DNS server responded, but there were no records of the requested type.
    -   `dns.resolver.Timeout`: The query timed out.
    -   Other DNS-related exceptions are caught and their class name is reported.
-   **Invalid User Input**: Provides defaults if the user enters non-integer values for the number of domains.
-   **No DNS Servers**: Exits if no DNS servers are specified by the user and the default is empty or invalid.
-   **Keyboard Interrupt**: Allows the user to stop the test gracefully using `Ctrl+C`.

## Troubleshooting

-   **Firewall Issues**: Ensure your firewall is not blocking outgoing DNS queries (typically UDP port 53) to the specified DNS servers.
-   **Network Connectivity**: Verify you have an active internet connection, especially for downloading the domain list.
-   **`top-1m.csv` not found/downloaded**:
    -   Check for error messages during the download attempt.
    -   Ensure the script has write permissions in its current directory if it needs to download and extract the file.
    -   If the download URL (`CISCO_UMBRELLA_URL`) is outdated, you might need to find a new source for a top domains list and update the script.
-   **Low QPS or High Timeouts**:
    -   The target DNS server might be slow or overloaded.
    -   Your internet connection might be slow or unstable.
    -   `CONCURRENT_REQUESTS` might be too high for your system or network to handle reliably. Try reducing it.
    -   `TIMEOUT` might be too short for some queries. Consider increasing it if many legitimate queries are timing out.
-   **"No domains available to test. Exiting."**: This means neither the Cisco list nor the fallback list could be loaded. Check previous error messages for clues (e.g., download failure, CSV read error).
-   **"CRITICAL: No DNS servers specified. Exiting."**: You did not provide any DNS server IPs when prompted, and the `DEFAULT_DNS_SERVER` might be empty or misconfigured.

## Note on Domain List

-   The script attempts to use a dynamic list of popular domains (Cisco Umbrella top 1M) to provide a realistic test against frequently accessed sites.
-   The domains are shuffled before testing to avoid any potential bias from the order in the list (e.g., if a DNS server caches sequentially).
-   If you prefer to use a specific list of domains, you can modify the `get_domains_for_test()` function or prepare your own `top-1m.csv` file in the expected format (rank,domain_name).

