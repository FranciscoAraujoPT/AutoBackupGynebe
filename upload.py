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
FOLDER_ID = "0AGehFL_62_CeUk9PVA"

logger = log_config()

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)

@retry(wait=wait_exponential(multiplier=2, min=2, max=60), stop=stop_after_attempt(5))
def upload_file(service, file_path):
    file_name = f"MWFichaClinica-{time.strftime('%Y-%m-%d_%H-%M')}.{EXTENSION}"
    media = MediaFileUpload(file_path, chunksize=5 * 1024 * 1024, resumable=True)

    # Create upload request (Shared Drive compatible)
    request = service.files().create(
        media_body=media,
        body={"name": file_name, "parents": [FOLDER_ID]},
        supportsAllDrives=True  # 👈 Required for Shared Drives
    )

    response = None
    last_progress = 0

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                if progress >= last_progress + 1:
                    logger.info(f"Progress: {progress}%")
                    last_progress = progress
        except HttpError as e:
            logger.warning(f"HTTP error {e.resp.status}, retrying...")
            raise e


    logger.info(f"Uploaded {file_name} successfully!")

    # Clean old backups and then empty trash
    cleanup_old_backups(service, keep_latest=2)

    return response["id"]


def cleanup_old_backups(service, keep_latest=2):
    """
    Deletes old backup files in the target folder, keeping only the newest 'keep_latest' backups.
    After deletion, it empties the Drive trash.
    """
    try:
        query = f"'{FOLDER_ID}' in parents and fileExtension='{EXTENSION}'"
        results = service.files().list(
            q=query,
            orderBy="createdTime asc",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            corpora="allDrives"
        ).execute()

        files = results.get("files", [])
        if len(files) <= keep_latest:
            logger.info("No old backups to delete.")
            return

        # Delete oldest backups
        for f in files[:-keep_latest]:
            try:
                service.files().delete(fileId=f["id"], supportsAllDrives=True).execute()
                logger.info(f"Deleted old backup: {f['name']}")
            except Exception as e:
                logger.warning(f"Could not delete old backup {f['name']}: {e}")

        empty_trash(service)

    except Exception as e:
        logger.error(f"Error cleaning up old backups: {e}")


def empty_trash(service):
    """
    Permanently empties the Google Drive trash (for the authenticated account or Shared Drive).
    """
    try:
        service.files().emptyTrash().execute()
        logger.info("Google Drive trash has been emptied successfully.")
    except HttpError as e:
        logger.error(f"Failed to empty Google Drive trash: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while emptying trash: {e}")


if __name__ == "__main__":
    logger.info("=== Starting Google Drive upload (Shared Drive mode) ===")
    service = get_drive_service()

    pattern = 'C:\\Users\\Servidor\\Desktop\\GynébeBackup\\MWFichaClinica*'
    files = glob.glob(pattern)

    if not files:
        raise FileNotFoundError(f"No files found with prefix MWFichaClinica in folder C:\\GynébeBackup")

    # Sort by modification time, newest first
    files.sort(key=os.path.getmtime, reverse=True)
    backup_file = files[0]
    if not os.path.exists(backup_file):
        logger.error(f"Backup file not found: {backup_file}")
    else:
        upload_file(service, backup_file)

    cleanup_old_backups(service, keep_latest=2)