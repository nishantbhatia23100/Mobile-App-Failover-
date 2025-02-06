import logging
import threading
import requests
from time import sleep

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

# Example Sync Gateway health-check endpoints (adjust these to match your environment)
PRIMARY_URL = "https://b2el4ajtbbvm7z9z.apps.cloud.couchbase.com:4984/_ping"
SECONDARY_URL = "https://ewat48fdlvqfczxo.apps.cloud.couchbase.com:4984/_ping"


# Simple data structure to hold cluster info
clusters = {
    "primary": PRIMARY_URL,
    "secondary": SECONDARY_URL
}

# Track which cluster is active
active_cluster = "primary"

def is_cluster_healthy(url):
    """
    Perform a health check against the given Couchbase Sync Gateway URL using HEAD.
    Returns True if status code is 200, otherwise False.
    Also logs the status code and headers for reference.
    """
    try:
        response = requests.head(url, timeout=5)
        
        logging.info(f"Health Check Response for {url}")
        logging.info(f"  Status Code: {response.status_code}")
        logging.info("  Headers:")
        for header, value in response.headers.items():
            logging.info(f"    {header}: {value}")

        if response.status_code == 200:
            logging.info(f"{url} is healthy!")
            return True
        else:
            logging.warning(f"{url} might be unhealthy or unreachable.")
            return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Health check failed for {url}: {e}")
        return False

def health_check_worker():
    """
    Background worker to continually check the health of the active cluster.
    If the active cluster is down for more than 9 consecutive checks,
    fail over to the other cluster (if that cluster is healthy).
    """
    global active_cluster

    # Consecutive failures for the current active cluster
    consecutive_failures = 0

    while True:
        sleep(3)  # Wait between checks

        current_url = clusters[active_cluster]
        logging.info(f"Health check: Checking {active_cluster} cluster at {current_url}...")

        if is_cluster_healthy(current_url):
            # Reset failure counter if healthy
            consecutive_failures = 0
        else:
            # Increment failure counter
            consecutive_failures += 1
            logging.warning(f"{active_cluster} cluster health check failed {consecutive_failures} time(s).")

            # If we exceed 9 consecutive failures, attempt failover
            if consecutive_failures > 9:
                logging.error(f"{active_cluster} cluster is considered down. Attempting to fail over...")

                # Determine the new cluster name (switch to the other one)
                new_cluster = "secondary" if active_cluster == "primary" else "primary"
                new_url = clusters[new_cluster]
                
                # Check the new cluster's health before switching
                if is_cluster_healthy(new_url):
                    active_cluster = new_cluster
                    logging.warning(f"Switched active cluster to {new_cluster}.")
                else:
                    logging.critical("Both clusters appear to be down!")

                # Reset failure counter after attempting failover
                consecutive_failures = 0

def main():
    """
    Main function:
      - Starts the background health-check thread
      - Keeps running indefinitely (or until stopped)
    """
    # Start health-check thread
    thread = threading.Thread(target=health_check_worker, daemon=True)
    thread.start()

    logging.info("Health check worker started. Press Ctrl+C to exit.")

    # Keep the main thread alive
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down health check script.")

if __name__ == "__main__":
    main()
