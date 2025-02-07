import logging
import threading
import requests
from time import sleep

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

# --------------------------------------
# Health Check URLs (app service server)
# --------------------------------------
# These are used strictly for health checks, e.g., HEAD to /_ping
health_check_urls = {
    "primary": "https://XXXXXXXXXXXXXX.apps.cloud.couchbase.com:4984/_ping",
    "secondary": "https://XXXXXXXXXXXXXX.apps.cloud.couchbase.com:4984/_ping"
}

# -------------------------------------
# Connection Endpoints (WebSocket URLs)
# -------------------------------------
# These are the endpoints your application actually connects to for data
# Adjust the endpoint paths as needed for your environment.
connection_urls = {
    "primary": "wss://XXXXXXXXXXXXXX.apps.cloud.couchbase.com:4984/primary",
    "secondary": "wss://XXXXXXXXXXXXXX.apps.cloud.couchbase.com:4984/primary"
}

# Track which cluster is active
active_cluster = "primary"

# This is the actual WebSocket URL your application will use at runtime
# By default, point it to the primary cluster's WSS endpoint
active_connection_url = connection_urls[active_cluster]

def is_cluster_healthy(url):
    """
    Perform a health check against the given Couchbase Sync Gateway URL using HEAD.
    Returns True if status code is 200, otherwise False.
    Logs the status code and headers for reference.
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
    global active_connection_url

    consecutive_failures = 0

    while True:
        sleep(3)  # Wait between checks

        # For health checks, use the HTTP-based /_ping endpoint
        current_health_url = health_check_urls[active_cluster]
        logging.info(f"Health check: Checking {active_cluster} at {current_health_url}...")

        if is_cluster_healthy(current_health_url):
            # Reset failure counter if healthy
            consecutive_failures = 0
        else:
            # Increment failure counter
            consecutive_failures += 1
            logging.warning(f"{active_cluster} health check failed {consecutive_failures} time(s).")

            # If we exceed 9 consecutive failures, attempt failover
            if consecutive_failures > 9:
                logging.error(f"{active_cluster} is considered down. Attempting to fail over...")

                # Determine new cluster (switch from primary->secondary or secondary->primary)
                new_cluster = "secondary" if active_cluster == "primary" else "primary"
                new_health_url = health_check_urls[new_cluster]

                # Check if the new cluster is healthy
                if is_cluster_healthy(new_health_url):
                    # Switch active cluster
                    active_cluster = new_cluster

                    # Update the WebSocket endpoint so the app connects to the healthy cluster
                    active_connection_url = connection_urls[new_cluster]

                    logging.warning(f"Switched active cluster to {new_cluster}.")
                    logging.warning(f"New WebSocket connection endpoint: {active_connection_url}")
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
    # Start the background health-check thread
    thread = threading.Thread(target=health_check_worker, daemon=True)
    thread.start()

    logging.info("Health check worker started. Press Ctrl+C to exit.")
    logging.info(f"Application will initially connect to: {active_connection_url}")

    # Keep the main thread alive
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down health check script.")

if __name__ == "__main__":
    main()
