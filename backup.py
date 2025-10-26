#!/usr/bin/env python3
import os
import sys
import time
import psutil
import subprocess
from loggingUtils import log_config

# === CONFIG ===
MAX_BACKUP_TIMEOUT = 120 * 60  # 120 minutes in seconds
PROC_NAME = "DOCbaseBackupRestore.exe"
PROC_LOCATION = r"C:\\Program Files (x86)\\Mobilwave\\Docbase"
BACKUP_FOLDER = r"C:\\Users\\Servidor\\Desktop\\GynébeBackup"

logger = log_config()


def kill_previous_instances():
    """
    Kill any running instances of the backup process to avoid conflicts.
    """
    for proc in psutil.process_iter():
        try:
            if proc.name() == PROC_NAME:
                proc.kill()
                logger.info(f'Killed existing process: {proc.pid}')
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            logger.warning("Could not access a process while killing previous instances.")


def create_backup_file():
    """
    Starts the backup process and waits for the backup file to be created.
    Returns the path to the backup file if successful, None otherwise.
    """
    # Generate backup file path
    backup_file = os.path.join(BACKUP_FOLDER, f"MWFichaClinica-{time.strftime('%d-%m-%Y')}.bak")

    # Kill previous backup processes
    kill_previous_instances()

    # Remove previous backup file if it exists
    if os.path.exists(backup_file):
        os.remove(backup_file)
        logger.info(f"Deleted existing backup file: {backup_file}")

    # Build command to run the backup executable
    backup_cmd = [os.path.join(PROC_LOCATION, PROC_NAME), backup_file]

    # Start the backup process
    try:
        result = subprocess.Popen(backup_cmd)
        logger.info(f'Started backup process: {PROC_NAME}')

        # Wait for process to finish with timeout
        result.wait(timeout=MAX_BACKUP_TIMEOUT)

    except subprocess.TimeoutExpired:
        logger.error("Timeout waiting for backup process to finish")
        return None
    except FileNotFoundError:
        logger.error(f"{PROC_NAME} not found at {PROC_LOCATION}")
        return None
    except Exception as e:
        logger.error(f"Error starting backup process: {e}")
        return None

    # Wait briefly to ensure file creation
    for _ in range(30):
        if os.path.exists(backup_file):
            logger.info(f'Backup file created successfully: {backup_file}')
            return backup_file
        time.sleep(1)

    logger.error(f"Backup file {backup_file} was not created!")
    return None


if __name__ == "__main__":
    logger.info("=== Starting backup process ===")
    backup_file = create_backup_file()
    if backup_file:
        logger.info(f"Backup completed successfully: {backup_file}")
    else:
        logger.error("Backup failed or backup file was not created!")
