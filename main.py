from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os.path

SCOPES = ['https://www.googleapis.com/auth/drive']

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
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('drive', 'v3', credentials=creds)

        folder_id = '1cvV_tUM1qkW14mZNDiPeh6MHsbeagRSX'  # Identyfikator folderu startowego
        shared_drive_id = '0AIINzgMQ695kUk9PVA'  # Identyfikator Dysku współdzielonego

        results = []
        search_files_and_folders(service,
                                 folder_id,
                                 shared_drive_id,
                                 search_string,
                                 results)
        if not results:
            print('Nie znaleziono pasujących plików ani folderów.')
        else:
            for item in results:
                print(f"Nazwa: {item['name']}, Link: {item.get('webViewLink')}") # wyświetlenie linku

    except HttpError as error:
        print(f'Wystąpił błąd: {error}')


if __name__ == '__main__':
    main(search_string='First Time Seen Driver Loaded')
