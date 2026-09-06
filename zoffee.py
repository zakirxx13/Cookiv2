#!/usr/bin/env python3

import json
import asyncio
from datetime import datetime

from playwright.async_api import async_playwright


TARGET_URL = "https://toffeelive.com/"


async def scrape():
    print("[*] Starting Playwright scraper")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36"
            ),
            viewport={
                "width": 1920,
                "height": 1080,
            },
        )

        page = await context.new_page()

        print("[*] Loading main page...")

        try:
            await page.goto(
                TARGET_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )
        except Exception as e:
            print(f"[!] Page navigation error: {e}")

        await page.wait_for_timeout(3000)

        cookies = await context.cookies()

        print(f"[+] Found {len(cookies)} cookies")

        # Only inspect cookie names.
        cookie_names = sorted(
            {cookie.get("name", "") for cookie in cookies}
        )

        print("[+] Cookie names:")
        for name in cookie_names:
            print(f"    {name}")

        result = {
            "timestamp": datetime.now().isoformat(),
            "total_cookies": len(cookies),
            "cookie_names": cookie_names,
        }

        with open("cookies.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Record only whether a particular cookie name exists.
        edge_cache_found = any(
            name.lower() == "edge-cache-cookie"
            for name in cookie_names
        )

        with open(
            "edge_cache_cookie.txt",
            "w",
            encoding="utf-8",
        ) as f:
            if edge_cache_found:
                f.write("Edge-Cache-Cookie name detected\n")
            else:
                f.write("Edge-Cache-Cookie name not detected\n")

        print(
            "[+] Edge-Cache-Cookie name detected"
            if edge_cache_found
            else "[-] Edge-Cache-Cookie name not detected"
        )

        await browser.close()


if __name__ == "__main__":
    asyncio.run(scrape())
