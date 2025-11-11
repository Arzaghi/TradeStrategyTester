import time
import logging
from apps.app1 import App1

def main():
    logging.basicConfig(level=logging.INFO)

    app = App1()
    try:
        while True:
            app.tick()
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down gracefully...")

if __name__ == "__main__":
    main()
