#!/usr/bin/python

import sys
import os
import logging
import logging.handlers
import backup
import time
import traceback
from loggingUtils import log_config
import upload
import send_backup

MAC_ADDRESS = "F4:39:09:03:72:F6"
TARGET_NAME = "ServidorBackup"
TARGET_FOLDER = r"\\SERVIDORBACKUP\ClinicaGynebeBackups\DOCbase"
USERNAME = r"ServidorBackup\Admin"

MAXIMUM_FILES = 2
LAST_EMAIL_KEY = 'lastSuccess'
DIRECTORY = "C:\\Users\\Servidor\\Desktop\\GynébeBackup"

def main():
    result = 0
    logger = log_config()
    try:
        with open("account_password.txt", "r") as file:
            PASSWORD = file.readline()
        backup_file = backup.create_backup_file()

        if backup_file is None:
            result = 4
            logger.error('No backup file!')
            raise Exception("No backup file created.")

        try:
            logger.info('Waking up target PC...')
            send_backup.wake_up_pc(MAC_ADDRESS)

            logger.info('Waiting for target PC to be online...')
            if not send_backup.wait_for_pc(TARGET_NAME):
                logger.error("Target PC did not wake up!")

            logger.info('Copying backup file...')
            dest = send_backup.copy_backup(backup_file, TARGET_FOLDER, USERNAME, PASSWORD)
            logger.info(f'Backup successfully copied to {dest}')

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            result += 1
            
        try:
            logger.info('Upload started!')
            start = time.time()
            service = upload.get_drive_service()
            upload.upload_file(service, backup_file)
            end = time.time()
            logger.info('Upload finished!')
            logger.info('Time taken: ' + time.strftime('%H:%M:%S', time.gmtime(int(end - start))))
        except:
            logger.error("File couldn't be uploaded!")
            result += 2

        sys.exit(result)
    except Exception as e:
        logger.error("Gynébe Backup Program failed: {e}")
        sys.exit(result)

def exception_handler(t, value, tb):
    logger = logging.getLogger('')
    logger.exception("Uncaught exception: {0}".format(str(value)))
    logger.exception(''.join(traceback.format_exception(t, value, tb)))


# Install exception handler
sys.excepthook = exception_handler

if __name__ == '__main__':
    main()
