"""
Security Agent: Mac check, validated digest, provider status, analyst chat.

    python main.py        # dashboard at http://127.0.0.1:5007

Flask serves the dashboard on a daemon thread; the main thread runs due jobs one at a time.
"""
import logging
import sys
import threading
import time
from datetime import datetime

import config
import database
import scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s - %(message)s",
    handlers=[logging.FileHandler(config.LOG_PATH), logging.StreamHandler(sys.stderr)],
)
logging.getLogger("werkzeug").setLevel(logging.WARNING)
logger = logging.getLogger("main")


def _serve():
    from web.app import create_app
    create_app().run(host=config.WEB_HOST, port=config.WEB_PORT, debug=False, use_reloader=False)


def main():
    conn = database.connect()
    database.init_db(conn)
    logger.info("Security agent starting, dashboard at http://%s:%d", config.WEB_HOST, config.WEB_PORT)
    threading.Thread(target=_serve, daemon=True, name="web").start()
    while True:
        try:
            scheduler.run_due_jobs(conn, datetime.now())
        except Exception:
            logger.exception("scheduler loop error")
        time.sleep(30)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Security agent stopped")
