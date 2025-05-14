import requests
import json
import sys
import os
import logging
from datetime import datetime
from requests.exceptions import HTTPError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os.path
from datetime import datetime, timedelta
from driveSearch import drive_main

# Disable SSL certificate warnings for insecure requests (self-signed certificates)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

# Set up logging configuration
log_file_path = "debug.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path),  # Write logs to a file
        logging.StreamHandler()  # Output logs to the console
    ]
)
logger = logging.getLogger(__name__)
logger.info("Starting the script...")

# Load configuration from config.json
if os.path.exists('config.json'):
    with open("config.json", "r") as config:
        data = json.load(config)
        API_URL = data['API_URL']  # Identyfikator folderu startowego
        API_KEY = data['API_KEY']  # Identyfikator Dysku współdzielonego

# Constants
ALLOWED_ACCOUNTS = {"BRO", "CC", "GAL", "MJWPU", "PRZ", "SPSK", "TUZ", "UCK"}
HEADERS = {
    "Accept": "application/vnd.manageengine.sdp.v3+json",
    "authtoken": API_KEY,
    "Content-Type": "application/x-www-form-urlencoded"
}

def view_full_ticket(ticket_id: int) -> dict:
    headers = {
        "Accept": "application/vnd.manageengine.sdp.v3+json",
        "Content-Type": "application/x-www-form-urlencoded",
        "authtoken": API_KEY
    }
    url = f"https://172.24.24.16/api/v3/requests/{ticket_id}"
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=10) # nosec B501
        response_data = response.json()
        return response_data
    except Exception as e:
        logger.error("Error while trying to view full ticket", ticket_id=ticket_id, error=str(e), exc_info=True)
        return {}

def fetch_open_requests():
    """
    Fetches open requests from the Service Desk API.
    """
    input_data = {
        "list_info": {
            "row_count": 10000,
            "start_index": 400,
            "sort_fields": [{"field": "created_time", "order": "asc"}],
            "search_criteria": {
                "field": "status.name",
                "condition": "is",
                "values": ["Open"]
            },
            "fields_required": ["id", "account.name", "subject", "created_time"]
        }
    }

    try:
        response = requests.get(
            API_URL,
            headers=HEADERS,
            params={"input_data": json.dumps(input_data)},
            verify=False
        )
        response.raise_for_status()
        return response.json().get("requests", [])
    except HTTPError as e:
        logging.error(f"Failed to fetch open requests: {e.response.text}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error fetching open requests: {e}")
        return []

def addDriveLinks(request_id, drive_links):
    """
    Adds drive links to the request in the Service Desk API.
    """
    reassign_data = {
        "request": {
            "udf_fields": {"udf_mline_2101": drive_links}
        }
    }

    try:
        response = requests.put(
            f"{API_URL}/{request_id}",
            headers=HEADERS,
            data={"input_data": json.dumps(reassign_data)},
            verify=False
        )
        response.raise_for_status()
        logging.info(f"Successfully added links to Request ID {request_id}.")
    
    except HTTPError as e:
        logging.error(f"Failed to add links to Request ID {request_id}")
    except Exception as e:
        logging.error(f"Unexpected error Request ID {request_id}: {e}")


def main():
    """
    Processes all open requests and add drive links.
    """
    requests_list = fetch_open_requests()
    print(requests_list)

    for request in requests_list:
        try:
            account_data = request.get("account")
            request_id = request.get("id")
            created_time = int(request.get('created_time')['value']) / 1000
            created_time = datetime.fromtimestamp(created_time).strftime('%d.%m.%Y')
            today_date = datetime.now().strftime('%d.%m.%Y')
            if today_date != created_time:
                continue
            if isinstance(account_data, dict):
                client_name = account_data.get("name")
            else:
                client_name = None
            if client_name and client_name.startswith("SOC - "):
                client_name = client_name.replace("SOC - ", "", 1)

            if client_name not in ALLOWED_ACCOUNTS:
                logging.warning(f"Skipping Request ID {request_id}, account '{client_name}' is not in the allowed list.")
                continue        
            subject = request.get("subject")
            subject = subject[5:].strip().removesuffix('[UPDATED]').removeprefix('NETXP')
            results = drive_main(subject) # Call the drive search function based on the subject name
            if not results:
                logging.warning(f"No results found for Request ID {request_id} with subject '{subject}'.")
                continue
            else:
                logging.info(f"Found {len(results)} results for Request ID {request_id} with subject '{subject}'.")
                print(results)
                addDriveLinks(request_id, results)

      #     print("\n")
      #     print(subject)
      #     print("\n")
            logging.info(f"Processed Request ID {request_id} for account '{client_name}' with subject '{subject}'.")
        except Exception as e:
            logging.error(f"Error processing request ID {request_id}: {e}")
            continue
if __name__ == "__main__":
    logger.info("Fetching open requests...")
 #   print(view_full_ticket(2911))
    main()
    logger.info("Finished processing requests.")