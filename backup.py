import os
import time
import pyodbc
import datetime
from loggingUtils import log_config
import threading

# ===== LOGGING CONFIGURATION =====
logger = log_config()

# ===== CONFIG =====
SERVER = "Servidor\\MW"
DATABASE = "MWFichaClinica"
USERNAME = "sa"
BACKUP_FOLDER = r"C:\Users\Servidor\Desktop\GynébeBackup"


# ===== FILESYSTEM PERMISSION TEST =====
def test_folder_permissions(folder: str):
    """Check if Python can write to the folder."""
    try:
        test_file = os.path.join(folder, "python_write_test.txt")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        logger.info(f"Python has write access to: {folder}")
    except Exception as e:
        logger.error(f"Python CANNOT write to backup folder: {folder}")
        logger.error(f"Filesystem error: {e}", exc_info=True)


# ===== HELPER FUNCTIONS =====
def cleanup_old_backups(folder: str, max_backups: int = 3):
    """Keep only the latest 'max_backups' .bak files."""
    backups = sorted(
        [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".bak")],
        key=os.path.getmtime,
        reverse=True,
    )
    for old_file in backups[max_backups:]:
        try:
            os.remove(old_file)
            logger.info(f"Deleted old backup: {old_file}")
        except Exception as e:
            logger.warning(f"Could not delete {old_file}: {e}")


# ===== BACKUP FUNCTION =====
def backup_database(server: str, database: str, username: str, password: str, backup_dir: str) -> str | None:
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M")
    backup_file = os.path.join(backup_dir, f"{database}_{timestamp}.bak")

    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};DATABASE=master;UID={username};PWD={password}"
    )

    backup_sql = f""" 
        BACKUP DATABASE [{database}] 
        TO DISK = N'{backup_file}' 
        WITH NOFORMAT, NOINIT, 
        NAME = N'{database}-Full Database Backup',
        SKIP, NOREWIND, NOUNLOAD, STATS = 10; 
    """
    backup_sql.encode(encoding='UTF-8')

    try:
        logger.info(f"Connecting to SQL Server at {server}...")
        def run_backup():
            with pyodbc.connect(conn_str, autocommit=True) as conn:
                cursor = conn.cursor()

                logger.info(f"Starting backup of '{database}' to: {backup_file}")

                try:
                    cursor.execute(backup_sql)
                    time.sleep(2)
                    while cursor.nextset():
                        pass

                except pyodbc.Error as sql_err:
                    logger.error("SQL Server BACKUP command failed!")
                    logger.error(f"ODBC Error: {sql_err}", exc_info=True)

                    # Extract detailed SQL Server messages
                    if hasattr(cursor, 'messages') and cursor.messages:
                        logger.error("SQL Server returned the following messages:")
                        for msg in cursor.messages:
                            logger.error(str(msg))

                    return None

                logger.info("Backup operation completed on SQL Server.")
                cursor.close()

        # Poll backup progress
        with pyodbc.connect(conn_str, autocommit=True) as progress_conn:
            logger.info(f"Starting backup of '{database}'...")
            progress_cursor = progress_conn.cursor()

            backup_thread = threading.Thread(target=run_backup)
            backup_thread.start()

            while backup_thread.is_alive():
                progress_cursor.execute("""
                    SELECT percent_complete, 
                        estimated_completion_time/1000/60 AS est_min_left
                    FROM sys.dm_exec_requests
                    WHERE command = 'BACKUP DATABASE';
                """)
                row = progress_cursor.fetchone()
                if row:
                    percent = round(row.percent_complete, 1)
                    est_time = int(row.est_min_left or 0)
                    logger.info(f"Progress: {percent}% complete, ~{est_time} min remaining...")
                else:
                    logger.info("Backup still initializing...")
                time.sleep(5)

            backup_thread.join()
            progress_conn.close()
        time.sleep(1)

        # Verify file creation
        if not os.path.exists(backup_file):
            logger.error("Backup file DOES NOT exist after SQL reported success!")
            return None

        logger.info("Verifying backup integrity...")
        verify_sql = f"RESTORE HEADERONLY FROM DISK = N'{backup_file}'"

        with pyodbc.connect(conn_str, autocommit=True) as conn:
            cur = conn.cursor()

            try:
                cur.execute(verify_sql)
            except pyodbc.Error as v_err:
                logger.error("RESTORE HEADERONLY verification failed!")
                logger.error(f"ODBC Error: {v_err}", exc_info=True)
                if hasattr(cur, 'messages') and cur.messages:
                    logger.error("SQL Server returned the following messages:")
                    for msg in cur.messages:
                        logger.error(str(msg))
                return None

        logger.info(f"Backup completed and verified successfully: {backup_file}")
        cleanup_old_backups(backup_dir, max_backups=3)
        return backup_file

    except Exception as e:
        logger.error("Unexpected fatal error during backup!", exc_info=True)
        return None


# ===== MAIN EXECUTION =====
if __name__ == "__main__":
    logger.info("=== Starting SQL Server backup process ===")

    # Test if Python can write to the folder BEFORE running SQL backup
    test_folder_permissions(BACKUP_FOLDER)

    try:
        with open("database_password.txt", "r", encoding="utf-8") as file:
            PASSWORD = file.readline().strip()
    except Exception:
        logger.error("Failed to read database_password.txt", exc_info=True)
        raise

    backup_database(SERVER, DATABASE, USERNAME, PASSWORD, BACKUP_FOLDER)
