import asyncio
import time
import dns.asyncresolver
import random
import statistics
import requests # For downloading the domain list
import zipfile # For extracting the zip file
import io # For handling the zip file in memory
import csv # For reading the CSV content
import os # For checking file existence
# Removed platform and subprocess imports

# --- Configuration ---
CISCO_UMBRELLA_URL = "https://s3-us-west-1.amazonaws.com/umbrella-static/top-1m.csv.zip"
LOCAL_CSV_FILENAME = "top-1m.csv" # Name of the CSV file after extraction
DEFAULT_DOMAINS_TO_TEST_COUNT = 10000

# Small fallback list if download fails or user requests very few domains
FALLBACK_DOMAINS = [
    "google.com", "youtube.com", "facebook.com", "twitter.com", "instagram.com",
    "wikipedia.org", "amazon.com", "yahoo.com", "reddit.com", "netflix.com",
    "office.com", "linkedin.com", "microsoft.com", "apple.com", "ebay.com",
    "bing.com", "twitch.tv", "stackoverflow.com", "github.com", "wordpress.org"
]

DEFAULT_DNS_SERVER = "192.168.0.2"
QUERY_TYPE = 'A'  # Type of DNS record to query (e.g., A, AAAA, MX)
TIMEOUT = 2.0  # Timeout in seconds for each DNS query
CONCURRENT_REQUESTS = 50 # Number of concurrent requests

# Removed the attempt_flush_os_dns_cache function

def download_and_extract_domain_list(url, target_csv_filename):
    """
    Downloads the Cisco Umbrella top 1M domains list if not already present.
    Extracts the CSV file.
    Returns the path to the CSV file or None if failed.
    """
    if os.path.exists(target_csv_filename):
        print(f"INFO: Using existing domain list: '{target_csv_filename}'")
        return target_csv_filename

    print(f"INFO: Attempting to download domain list from {url}...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            expected_file_in_zip = 'top-1m.csv'
            if expected_file_in_zip in zf.namelist():
                zf.extract(expected_file_in_zip, path=".")
                extracted_path = os.path.join(".", expected_file_in_zip)
                if os.path.basename(extracted_path) != target_csv_filename:
                     os.rename(extracted_path, target_csv_filename)
                print(f"INFO: Successfully downloaded and extracted '{target_csv_filename}'")
                return target_csv_filename
            else:
                csv_files_in_zip = [name for name in zf.namelist() if name.lower().endswith('.csv')]
                if csv_files_in_zip:
                    file_to_extract = csv_files_in_zip[0]
                    print(f"INFO: '{expected_file_in_zip}' not found. Extracting '{file_to_extract}' instead.")
                    zf.extract(file_to_extract, path=".")
                    extracted_path = os.path.join(".", file_to_extract)
                    if os.path.basename(extracted_path) != target_csv_filename:
                        os.rename(extracted_path, target_csv_filename)
                    print(f"INFO: Successfully extracted and renamed to '{target_csv_filename}'")
                    return target_csv_filename
                else:
                    print(f"ERROR: No CSV files found in the downloaded ZIP from {url}.")
                    return None
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Could not download domain list: {e}")
        return None
    except zipfile.BadZipFile:
        print(f"ERROR: Downloaded file from {url} is not a valid ZIP file or is corrupted.")
        return None
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during download/extraction: {e}")
        return None

def load_domains_from_csv(csv_filepath, num_domains):
    """
    Loads the specified number of domains from the CSV file.
    The CSV is expected to have domains in the second column.
    """
    domains = []
    try:
        with open(csv_filepath, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if len(domains) >= num_domains:
                    break
                if len(row) >= 2:
                    domain_name = row[1].strip()
                    if domain_name:
                        domains.append(domain_name)
                elif i < 5 : # Print warning only for first few malformed rows
                    print(f"WARNING: Skipping malformed row {i+1} in {csv_filepath}: {row}")
        if not domains:
            print(f"ERROR: No domains loaded from {csv_filepath}. It might be empty or in the wrong format.")
            return None
        print(f"INFO: Loaded {len(domains)} domains from '{csv_filepath}'.")
        return domains
    except FileNotFoundError:
        print(f"ERROR: CSV file '{csv_filepath}' not found.")
        return None
    except Exception as e:
        print(f"ERROR: Could not read domains from '{csv_filepath}': {e}")
        return None

def get_domains_for_test():
    """
    Manages acquiring the list of domains, by download or fallback.
    Asks user for the number of top N domains to use.
    """
    csv_path = download_and_extract_domain_list(CISCO_UMBRELLA_URL, LOCAL_CSV_FILENAME)

    num_domains_to_use_str = input(f"How many top domains do you want to test? (default: {DEFAULT_DOMAINS_TO_TEST_COUNT}): ")
    try:
        if not num_domains_to_use_str:
            num_domains_to_use = DEFAULT_DOMAINS_TO_TEST_COUNT
        else:
            num_domains_to_use = int(num_domains_to_use_str)
        if num_domains_to_use <= 0:
            print("INFO: Number of domains must be positive. Using default.")
            num_domains_to_use = DEFAULT_DOMAINS_TO_TEST_COUNT
    except ValueError:
        print("INFO: Invalid input. Using default number of domains.")
        num_domains_to_use = DEFAULT_DOMAINS_TO_TEST_COUNT

    final_domains_list = []
    if csv_path:
        domains_from_csv = load_domains_from_csv(csv_path, num_domains_to_use)
        if domains_from_csv:
            final_domains_list = domains_from_csv
            if len(final_domains_list) < num_domains_to_use:
                print(f"WARNING: Requested {num_domains_to_use} domains, but only {len(final_domains_list)} were available in the list.")
        else:
            print("WARNING: Failed to load domains from CSV. Using fallback list.")
            final_domains_list = FALLBACK_DOMAINS[:min(num_domains_to_use, len(FALLBACK_DOMAINS))]
    else:
        print(f"WARNING: Could not obtain domain list from Cisco Umbrella. Using fallback list of up to {num_domains_to_use} domains.")
        final_domains_list = FALLBACK_DOMAINS[:min(num_domains_to_use, len(FALLBACK_DOMAINS))]

    if not final_domains_list:
        print("CRITICAL WARNING: No domains could be loaded. Using a minimal internal list.")
        return ["google.com", "cloudflare.com"]
    return final_domains_list


async def query_domain(resolver, domain):
    """
    Performs a DNS lookup for a given domain and returns the time taken and error key (if any).
    """
    start_time = time.perf_counter()
    try:
        await resolver.resolve(domain, QUERY_TYPE)
        end_time = time.perf_counter()
        return domain, end_time - start_time, None  # Domain, time_taken, error_key
    except dns.resolver.NXDOMAIN:
        end_time = time.perf_counter()
        return domain, end_time - start_time, "NXDOMAIN"
    except dns.resolver.NoAnswer:
        end_time = time.perf_counter()
        return domain, end_time - start_time, "NoAnswer"
    except dns.resolver.Timeout:
        end_time = time.perf_counter()
        return domain, TIMEOUT, "Timeout"
    except Exception as e: # Catch other DNS-related or unexpected errors
        end_time = time.perf_counter()
        error_name = type(e).__name__ # e.g., "NoNameservers", "YXDOMAIN"
        return domain, end_time - start_time, error_name # Use just the exception class name as the error key


async def run_test(dns_servers, domains_to_test):
    """
    Runs the DNS performance test against the specified DNS servers, showing live QPS.
    """
    # Create a new resolver instance for each test run.
    # configure=False prevents reading system's /etc/resolv.conf
    resolver = dns.asyncresolver.Resolver(configure=False)
    resolver.nameservers = dns_servers
    resolver.timeout = TIMEOUT
    resolver.lifetime = TIMEOUT # Set lifetime for the resolver context
    # Removed DEBUG print for resolver nameservers

    print(f"\nTesting DNS servers: {', '.join(dns_servers)}")
    print(f"Querying {len(domains_to_test)} domains for '{QUERY_TYPE}' records...")
    print(f"Concurrent requests: {CONCURRENT_REQUESTS}\n")

    tasks = []
    successful_lookups = 0
    failed_lookups = 0
    error_counts = {}
    timings = []

    # Use a semaphore to limit concurrency
    sem = asyncio.Semaphore(CONCURRENT_REQUESTS)

    async def limited_query(domain_to_query):
        # Acquire semaphore before running the query
        async with sem:
            return await query_domain(resolver, domain_to_query)

    # Create all task objects
    for domain in domains_to_test:
        tasks.append(limited_query(domain))

    # Start timing just before processing results
    start_processing_time = time.perf_counter()
    total_processed = 0 # Counter for total tasks processed

    # Process tasks as they complete
    for i, future in enumerate(asyncio.as_completed(tasks)):
        domain, time_taken, error_key = await future
        total_processed = i + 1 # Total tasks completed so far

        # Record results
        if error_key:
            failed_lookups += 1
            error_counts[error_key] = error_counts.get(error_key, 0) + 1
        else:
            successful_lookups += 1
            timings.append(time_taken)

        # Calculate elapsed time and QPS for progress display
        current_time = time.perf_counter()
        elapsed_time = current_time - start_processing_time
        current_qps = total_processed / elapsed_time if elapsed_time > 0 else 0

        # Update progress indicator line
        progress_percent = total_processed / len(domains_to_test) * 100
        print(f"\rProgress: {progress_percent:.2f}% ({total_processed}/{len(domains_to_test)}) | QPS: {current_qps:.2f} | Success: {successful_lookups}, Errors: {failed_lookups}", end="")

    # Record end time after all tasks are processed
    end_processing_time = time.perf_counter()
    total_duration = end_processing_time - start_processing_time # Use the processing time for final QPS

    # --- Print Summary ---
    print("\n\n--- Test Summary ---")
    print(f"DNS Servers Tested: {', '.join(dns_servers)}")
    print(f"Total Domains Tested: {len(domains_to_test)}")
    print(f"Total Processing Time: {total_duration:.2f} seconds") # Label reflects processing duration
    print(f"Successful Lookups: {successful_lookups}")
    print(f"Failed Lookups: {failed_lookups}")

    # Print error breakdown if any errors occurred
    if failed_lookups > 0:
        print("\nError Breakdown:")
        # Sort errors by count descending for readability
        sorted_errors = sorted(error_counts.items(), key=lambda item: item[1], reverse=True)
        for err_type, count in sorted_errors:
            print(f"  - {err_type}: {count}")

    # Print performance metrics if any lookups were successful
    if timings:
        print("\nPerformance Metrics (for successful lookups):")
        print(f"  Average Query Time: {statistics.mean(timings)*1000:.2f} ms")
        print(f"  Median Query Time: {statistics.median(timings)*1000:.2f} ms")
        print(f"  Min Query Time: {min(timings)*1000:.2f} ms")
        print(f"  Max Query Time: {max(timings)*1000:.2f} ms")
        # Calculate standard deviation only if more than one timing is available
        if len(timings) > 1:
            print(f"  Standard Deviation: {statistics.stdev(timings)*1000:.2f} ms")
        # Calculate final average QPS based on total processed and total duration
        if total_duration > 0:
            final_qps = len(domains_to_test) / total_duration
            print(f"  Overall Average QPS: {final_qps:.2f}")
    else:
        print("\nNo successful lookups to calculate performance metrics.")

def get_dns_servers_from_user():
    """
    Asks the user for DNS servers, using a default if no input is provided.
    """
    dns_input = input(f"Enter DNS server(s) to test, separated by commas (default: {DEFAULT_DNS_SERVER}): ")
    if not dns_input:
        return [DEFAULT_DNS_SERVER]
    else:
        # Filter out empty strings that might result from trailing commas
        return [server.strip() for server in dns_input.split(',') if server.strip()]

# --- Main execution block ---
if __name__ == "__main__":
    # Removed the call to attempt_flush_os_dns_cache()

    # Get the list of domains to test (handles download/fallback/user count)
    actual_domains_to_test = get_domains_for_test()

    # Exit if no domains could be loaded
    if not actual_domains_to_test:
        print("CRITICAL: No domains available to test. Exiting.")
    else:
        # Get the DNS servers from the user
        custom_dns_servers = get_dns_servers_from_user()
        print(f"DEBUG: User provided DNS servers: {custom_dns_servers}") # Added debug print

        # Exit if no DNS servers were provided
        if not custom_dns_servers:
            print("CRITICAL: No DNS servers specified. Exiting.")
        else:
            # Shuffle the domain list to avoid potential biases from list order
            random.shuffle(actual_domains_to_test)
            # Run the main asynchronous test function
            try:
                asyncio.run(run_test(custom_dns_servers, actual_domains_to_test))
            except KeyboardInterrupt:
                # Handle user interruption gracefully
                print("\n\nTest interrupted by user. Exiting.")
            except Exception as e:
                # Catch any other unexpected errors during the async run
                print(f"\nAn unexpected error occurred during the test run: {e}")


