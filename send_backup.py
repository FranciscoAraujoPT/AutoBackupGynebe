import os
import time
import shutil
import glob
from wakeonlan import send_magic_packet
from loggingUtils import log_config

logger = log_config()

def wake_up_pc(mac_address: str):
    """
    Send a Wake-on-LAN magic packet to the target PC.
    """
    try:
        send_magic_packet(mac_address)
        logger.info(f"Sent Wake-on-LAN packet to {mac_address}")
    except Exception as e:
        logger.error(f"Failed to send Wake-on-LAN packet to {mac_address}: {e}")
        raise


def wait_for_pc(host: str, timeout: int = 120) -> bool:
    """
    Ping the target host (IP or computer name) until it responds or timeout expires.
    Works with both IP and hostname.
    """
    logger.info(f"Waiting for PC {host} to come online (timeout: {timeout}s)")
    start = time.time()
    while time.time() - start < timeout:
        response = os.system(f"ping -n 1 {host} >nul 2>&1")
        if response == 0:
            logger.info(f"PC {host} is online")
            return True
        time.sleep(5)
    logger.warning(f"Timeout expired: PC {host} did not respond")
    return False


def connect_network_share(target_folder: str, username: str, password: str):
    """
    Connect to a Windows network share with given credentials.
    """
    try:
        parts = target_folder.strip("\\").split("\\")
        if len(parts) < 2:
            raise ValueError(f"Invalid target folder UNC path: {target_folder}")
        server = parts[0]

        # Disconnect any existing connections
        os.system(f'net use \\\\{server} /delete /y >nul 2>&1')

        # Connect with credentials
        result = os.system(f'net use {target_folder} /user:{username} {password}')
        if result != 0:
            raise ConnectionError(f"Failed to connect to {target_folder} as {username}")

        logger.info(f"Connected to network share {target_folder} as {username}")
    except Exception as e:
        logger.error(f"Error connecting to network share {target_folder}: {e}")
        raise


def copy_backup(local_file: str, target_folder: str, username: str = None, password: str = None):
    """
    Copy the backup file to the target network folder.
    If username/password are provided, authenticate before copying.
    """
    try:
        if username and password:
            connect_network_share(target_folder, username, password)

        if not os.path.exists(local_file):
            raise FileNotFoundError(f"Backup file not found: {local_file}")
        
        if not os.path.exists(target_folder):
            raise FileNotFoundError(f"Target folder not found: {target_folder}")

        shutil.copy(local_file, target_folder)
        dest_path = os.path.join(target_folder, os.path.basename(local_file))
        logger.info(f"Copied backup file {local_file} to {dest_path}")

        # === NEW: Keep only the two newest backups ===
        cleanup_old_backups(target_folder)

        return dest_path
    except Exception as e:
        logger.error(f"Failed to copy backup file {local_file} to {target_folder}: {e}")
        raise


def cleanup_old_backups(target_folder: str, max_backups: int = 1):
    """
    Keep only the most recent 'max_backups' files in the target folder.
    Deletes older backups based on modification time.
    """
    try:
        # Get list of files in the target folder
        files = [os.path.join(target_folder, f) for f in os.listdir(target_folder)
                 if os.path.isfile(os.path.join(target_folder, f))]

        # Skip if there are fewer than or equal to max_backups
        if len(files) <= max_backups:
            return

        # Sort by modification time (newest first)
        files.sort(key=os.path.getmtime, reverse=True)

        # Delete older ones
        for old_file in files[max_backups:]:
            try:
                os.remove(old_file)
                logger.info(f"Deleted old backup: {old_file}")
            except Exception as e:
                logger.warning(f"Could not delete old backup {old_file}: {e}")
    except Exception as e:
        logger.error(f"Error cleaning up old backups in {target_folder}: {e}")


def main():
    # Test configuration
    mac_address = "F4:39:09:03:72:F6"
    host = "ServidorBackup"
    target_folder = r"\\SERVIDORBACKUP\ClinicaGynebeBackups\DOCbase"
    username = r"ServidorBackup\Admin"
    password = "your_password"

    try:
        logger.info("=== Starting backup test ===")

        pattern = 'C:\\Users\\Servidor\\Desktop\\GynébeBackup\\MWFichaClinica*'
        files = glob.glob(pattern)

        if not files:
            raise FileNotFoundError(f"No files found with prefix MWFichaClinica in folder C:\\GynébeBackup")

        # Sort by modification time, newest first
        files.sort(key=os.path.getmtime, reverse=True)
        local_file = files[0]

        # Wake up the target PC
        wake_up_pc(mac_address)

        # Wait for the PC to respond
        if wait_for_pc(host, timeout=120):
            logger.info("PC is online, proceeding to copy backup...")
        else:
            logger.warning("PC did not come online, aborting backup.")
            return
        
        with open("account_password.txt", "r") as file:
            password = file.readline()

        # Copy the backup file to the network share
        dest_path = copy_backup(local_file, target_folder, username, password)
        logger.info(f"Backup successfully copied to: {dest_path}")

        logger.info("=== Backup test completed successfully ===")
    except Exception as e:
        logger.error(f"Backup test failed: {e}")


if __name__ == "__main__":
    main()
