"""libSQL/Turso client helper for the local sync script."""
import os
from dotenv import load_dotenv
import libsql_client

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def get_client() -> "libsql_client.Client":
    url = os.environ["TURSO_DATABASE_URL"]
    token = os.environ["TURSO_AUTH_TOKEN"]
    # libsql-client sync client speaks HTTP; accept libsql:// or https:// URLs.
    if url.startswith("libsql://"):
        url = "https://" + url[len("libsql://"):]
    return libsql_client.create_client_sync(url=url, auth_token=token)


def apply_schema() -> None:
    here = os.path.dirname(__file__)
    with open(os.path.join(here, "turso", "schema.sql")) as f:
        statements = [s.strip() for s in f.read().split(";") if s.strip()]
    client = get_client()
    try:
        for stmt in statements:
            client.execute(stmt)
    finally:
        client.close()


if __name__ == "__main__":
    apply_schema()
    client = get_client()
    try:
        rs = client.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        print("Tables in Turso:", [row[0] for row in rs.rows])
    finally:
        client.close()
