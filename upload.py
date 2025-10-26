#!/usr/bin/env python3
import os
import time
import glob
from loggingUtils import log_config
from tenacity import retry, wait_exponential, stop_after_attempt
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

# === CONFIG ===
EXTENSION = "bak"
SERVICE_ACCOUNT_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_ID = "1hFXhgDtpYTkONdmdMbWi5nsA4iQ8GsEZ"

logger = log_config()

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)

@retry(wait=wait_exponential(multiplier=2, min=2, max=60), stop=stop_after_attempt(5))
def upload_file(service, file_path):
    file_name = f"Backup-{time.strftime('%Y-%m-%d_%H-%M')}.{EXTENSION}"
    media = MediaFileUpload(file_path, chunksize=5*1024*1024, resumable=True)
    request = service.files().create(
        media_body=media, body={"name": file_name, "parents": [FOLDER_ID]}
    )

    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                logger.info(f"Progress: {int(status.progress() * 100)}%")
        except HttpError as e:
            logger.warning(f"HTTP error {e.resp.status}, retrying...")
            raise e

    logger.info(f"Uploaded {file_name} successfully!")
    cleanup_old_backups(service, keep_latest=2)  # Keep only the 2 latest backups
    return response["id"]

def cleanup_old_backups(service, keep_latest=2):
    query = f"'{FOLDER_ID}' in parents and fileExtension='{EXTENSION}'"
    results = service.files().list(q=query, orderBy="createdTime asc").execute()
    files = results.get("files", [])

    if len(files) <= keep_latest:
        return

    for f in files[:-keep_latest]:
        service.files().delete(fileId=f["id"]).execute()
        logger.info(f"Deleted old backup: {f['name']}")

if __name__ == "__main__":
    service = get_drive_service()
    pattern = 'C:\\Users\\Servidor\\Desktop\\GynébeBackup\\MWFichaClinica'
    files = glob.glob(pattern)

    if not files:
        logger.error(f"No files found with prefix MWFichaClinica in folder C:\\Users\\Servidor\\Desktop\\GynébeBackup\\")

    # Sort by modification time, newest first
    files.sort(key=os.path.getmtime, reverse=True)
    local_file = files[0]
    upload_file(service, local_file)
