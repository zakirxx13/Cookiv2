import json
from pathlib import Path

import requests


TARGET_URL = "https://toffeelive.com/en/watch/Xi_Ga5oBNnOkwJLWkhKP"
COOKIE_NAME = "Edge-Cache-Cookie"

OUTPUT_FILE = Path("cookie_result.json")


def check_cookie():
    response = requests.get(
        TARGET_URL,
        timeout=30,
        allow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
    )

    found = any(
        cookie.name == COOKIE_NAME
        for cookie in response.cookies
    )

    result = {
        COOKIE_NAME: "[REDACTED]" if found else None
    }

    OUTPUT_FILE.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    check_cookie()
