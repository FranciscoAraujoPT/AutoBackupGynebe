import logging
import logging.handlers
import os
import sys

LOGFILE = "C:\\Users\\Servidor\\gynebeautobackup\\gynebeBot.log"


def log_config():
    # Configure logger to write to a file...
    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)
    log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(log_formatter)
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)

    fh = logging.handlers.RotatingFileHandler(LOGFILE, maxBytes=(1048576 * 10), backupCount=7)
    fh.setFormatter(log_formatter)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    return logger
