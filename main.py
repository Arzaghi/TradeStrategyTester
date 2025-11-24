import time
import logging
from logging.handlers import RotatingFileHandler
from apps.app1 import App1
from config import config

def main():
    # Configure logging
    log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler = RotatingFileHandler("/HDD/app.log", maxBytes=50*1024*1024, backupCount=2)
    file_handler.setFormatter(log_formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    # Load config
    config._config_file = "/HDD/config.ini"
    config.reload()
    if not config.enabled("general.init"):
        logging.info("Could not load config.ini")
        return

    app = App1()
    try:
        while True:
            config.reload()
            app.tick()
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down gracefully...")

if __name__ == "__main__":
    main()
