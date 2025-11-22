import time
import logging
from apps.app1 import App1
from config import config

def main():
    logging.basicConfig(level=logging.INFO)
    config._config_file = "/HDD/config.ini"
    config.reload()
    if not config.enabled("general.init"):
        logging.error("Could not load config.ini")
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
