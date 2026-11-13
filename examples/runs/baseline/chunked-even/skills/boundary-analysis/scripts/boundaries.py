import json
import sys

data = json.load(sys.stdin)
center = int(data.get("center", 0))
print(json.dumps({"values": [center - 1, center, center + 1, 10**30]}))
