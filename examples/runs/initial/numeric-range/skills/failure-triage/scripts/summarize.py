import json
import sys

data = json.load(sys.stdin)
lines = str(data.get("text", "")).splitlines()
keys = ("Error", "FAILED", "assert ", "DID NOT RAISE", "passed")
print(
    json.dumps(
        {"signals": [line for line in lines if any(key in line for key in keys)][-20:]}, ensure_ascii=False
    )
)
