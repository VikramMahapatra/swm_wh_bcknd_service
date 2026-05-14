import base64
import urllib.parse
import urllib.request

url = "http://13.200.249.92:8123/?query=" + urllib.parse.quote("SELECT version()")
req = urllib.request.Request(url)  # noqa: S310
creds = base64.b64encode(b"default:Zen$123").decode()
req.add_header("Authorization", "Basic " + creds)

with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
    print("ClickHouse OK:", r.read().decode().strip())
