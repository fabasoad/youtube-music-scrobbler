"""
Run this script to refresh browser.json when cookies expire.

Steps:
1. Open music.youtube.com in Chrome
2. DevTools -> Network tab -> filter 'browse' -> click anything on the page
3. Right-click the 'browse' request -> Copy -> Copy as cURL
4. Paste the cURL command into a file called 'curl.txt' and run this script
"""

import json
import os
import re
import sys


def parse_curl(curl: str) -> dict:
    cookie = re.search(r"-b '([^']+)'", curl)
    auth = re.search(r"'authorization: ([^']+)'", curl)
    authuser = re.search(r"'x-goog-authuser: ([^']+)'", curl)

    missing = []
    if not cookie:
        missing.append("cookie (-b flag)")
    if not auth:
        missing.append("authorization header")
    if not authuser:
        missing.append("x-goog-authuser header")

    if missing:
        print(f"Error: Could not find: {', '.join(missing)}")
        print("Make sure you copied the full cURL command.")
        sys.exit(1)

    return {
        "cookie": cookie.group(1),
        "authorization": auth.group(1),
        "x-goog-authuser": authuser.group(1),
    }


def main():
    curl_file = "curl.txt"
    if not os.path.exists(curl_file):
        print(f"Please paste your cURL command into a file called '{curl_file}' and run this script again.")
        sys.exit(0)

    with open(curl_file) as f:
        curl = f.read()

    parsed = parse_curl(curl)

    try:
        with open("browser.json") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    data.update(parsed)

    with open("browser.json", "w") as f:
        json.dump(data, f, indent=4)

    print("\nbrowser.json updated successfully!")
    print("\nNext: copy the contents of browser.json and update the YTM_BROWSER GitHub Secret.")
    print("Run: cat browser.json | pbcopy")


if __name__ == "__main__":
    main()
