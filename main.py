from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os.path
import json
import logging
import sys


SCOPES = ['https://www.googleapis.com/auth/drive']
logger = logging.getLogger(__name__)

# logger.setLevel(logging.INFO)
logger.info("Starting the script...")

def setup_logging():
    """ Sets up logging configuration. """
    logging.basicConfig(
        filename='myapp.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def search_files_and_folders(service, folder_id, shared_drive_id, search_string, results):
    """ Recursively searches for files and folders in a Google Drive shared drive that match a given search string.
        service (googleapiclient.discovery.Resource): The Google Drive API service instance.
        folder_id (str): The ID of the folder to search within.
        shared_drive_id (str): The ID of the shared drive.
        search_string (str): The string to search for in file and folder names.
        results (list): A list to store the search results. Each result is a dictionary containing file/folder details.
    Returns:
        None: The results are appended to the provided results list.
    """
    query = f"parents = '{folder_id}' and trashed = false"

    response = service.files().list(
        q=query,
        pageSize=1000,
        fields="nextPageToken, files(id, name, mimeType, webViewLink)",
        corpora='drive',
        driveId=shared_drive_id,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()

    items = response.get('files', [])

    for item in items:
        if search_string.lower() in item['name'].lower():
            if item['name'].lower().endswith('.png'):
                continue  # Skip if the search string ends with '.png'
            else:
                results.append(item)

        if item['mimeType'] == 'application/vnd.google-apps.folder':
            search_files_and_folders(service, item['id'], shared_drive_id, search_string, results)


def main(search_string):
    """ Main function to search for files and folders in a Google Drive.
        search_string (str): The string to search for in file and folder names.
    Raises:
        HttpError: If an error occurs while accessing the Google Drive API.
    """
    setup_logging()

    creds = None
    try:
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            logger.info("Token loaded successfully.")
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info("Token refreshed successfully.")
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'client_secret.json', SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info("New token created successfully.")
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
                logger.info("Token saved successfully.")
    except Exception as e:
        logger.error(f"Error loading credentials: {e}")
        return
    logger.info("Credentials loaded successfully.")

    try:
        service = build('drive', 'v3', credentials=creds)
        if os.path.exists('config.json'):
            with open("config.json", "r") as config:
                data = json.load(config)
                folder_id = data['folder_id']  # Identyfikator folderu startowego
                shared_drive_id = data['shared_drive_id']  # Identyfikator Dysku współdzielonego
               # logging.basicConfig(filename='search.log', level=logging.INFO,
               #                     format='%(asctime)s - %(levelname)s - %(message)s')
        else:
            logger.error("Nie znaleziono pliku konfiguracyjnego config.json.")
            return
        results = []
        search_files_and_folders(service,
                                 folder_id,
                                 shared_drive_id,
                                 search_string,
                                 results)
        if not results:
            logger.info('Nie znaleziono pasujących plików ani folderów.')
        else:
            for item in results:
                logger.info(f"{item['name']}, Link: {item.get('webViewLink')}") # wyświetlenie linku

    except HttpError as error:
        logger.error(f'Wystąpił błąd HTTP: {error}')


if __name__ == '__main__':
    main(search_string='First Time Seen Driver Loaded')
