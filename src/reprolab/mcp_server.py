"""stdio MCP entrypoint. stdout is exclusively owned by the protocol transport."""

import argparse
from pathlib import Path

from reprolab.core import Settings
from reprolab.store import Store
from reprolab.tools import create_server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--home", required=True)
    arguments = parser.parse_args()
    store = Store(Settings(home=Path(arguments.home)))
    create_server(store, arguments.run_id).run(transport="stdio")


if __name__ == "__main__":
    main()
