import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import database
import config
from web.app import app


def main():
    database.init_db()
    print(f"[Solaris] Starting on http://localhost:{config.WEB_PORT}")
    app.run(host="0.0.0.0", port=config.WEB_PORT, debug=False)


if __name__ == "__main__":
    main()
