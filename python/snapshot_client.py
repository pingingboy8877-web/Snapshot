"""Python client for the Snapshot rendering pipeline. Requires: pip install requests."""
import os, sys, requests

API="https://production-sfo.browserless.io"

def capture(url, output="snapshot.png", kind="png", width=1440, delay=3):
    token=os.environ["BROWSERLESS_TOKEN"]
    if kind=="pdf":
        endpoint=API+"/pdf?token="+token
        payload={"url":url,"options":{"format":"A4","printBackground":True}}
    else:
        endpoint=API+"/screenshot?token="+token
        payload={"url":url,"viewport":{"width":width,"height":900},
                 "gotoOptions":{"waitUntil":"networkidle2","timeout":45000},
                 "waitForTimeout":delay*1000,"scrollPage":True,
                 "options":{"fullPage":True,"type":kind,"quality":92 if kind=="jpeg" else 100}}
    r=requests.post(endpoint,json=payload,timeout=120)
    r.raise_for_status()
    with open(output,"wb") as f:f.write(r.content)
    return output

if __name__=="__main__":
    if len(sys.argv)<2:
        raise SystemExit("Usage: python snapshot_client.py https://example.com [output]")
    print(capture(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else "snapshot.png"))
