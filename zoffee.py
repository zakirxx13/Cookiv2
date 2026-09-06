#!/usr/bin/env python3
import json
import asyncio
import requests
from playwright.async_api import async_playwright
from datetime import datetime

TARGET_URL = "https://toffeelive.com/en"
API_BASE = "https://api.toffeelive.com"

async def scrape():
    print(f"[*] Starting Playwright scraper")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080},
        )
        
        page = await context.new_page()
        
        # Navigate to main page first
        print("[*] Loading main page...")
        await page.goto(TARGET_URL, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(3000)
        
        # Get initial cookies
        cookies = await context.cookies()
        print(f"[+] Found {len(cookies)} initial cookies")
        
        # Find device_token
        device_token = None
        for c in cookies:
            if c['name'] == 'device_token':
                device_token = c['value']
                print(f"[+] Found device_token")
                break
        
        # Try to fetch stream data using API
        if device_token:
            print("[*] Trying to fetch stream data via API...")
            try:
                # Use requests with the device_token
                headers = {
                    'Authorization': f'Bearer {device_token}',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                    'Accept': 'application/json',
                    'Origin': 'https://toffeelive.com',
                    'Referer': 'https://toffeelive.com/',
                }
                
                # Try to get live streams or featured content
                resp = requests.get(
                    f'{API_BASE}/api/v2/contents/featured?country=BD&page=1&limit=10',
                    headers=headers,
                    timeout=30
                )
                print(f"[+] API status: {resp.status_code}")
                
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"[+] API response keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
                    
                    # Save API response
                    with open('api_response.json', 'w') as f:
                        json.dump(data, f, indent=2)
                    
                    # Try to find stream URLs
                    stream_urls = []
                    if isinstance(data, dict) and 'data' in data:
                        for item in data['data']:
                            if isinstance(item, dict):
                                url = item.get('stream_url') or item.get('playback_url') or item.get('url')
                                if url:
                                    stream_urls.append(url)
                                    print(f"[+] Found stream URL: {url[:80]}...")
                    
                    # Navigate to first stream URL to trigger Edge-Cache-Cookie
                    if stream_urls:
                        print(f"[*] Navigating to stream URL to trigger cookie...")
                        await page.goto(stream_urls[0], wait_until='domcontentloaded', timeout=30000)
                        await page.wait_for_timeout(5000)
                        
            except Exception as e:
                print(f"[!] API error: {e}")
        
        # Also try navigating to a CDN URL directly
        print("[*] Trying direct CDN access...")
        cdn_test_url = "https://bldcmprod-cdn.tofeellive.com/Expires=1770454179/KeyName=prod_linear/Signature=eZAqqnWnwkreQy5c7uw9GSU7ElCE8APAAroc3rDpwBgcZjzIne25gTFBtPcErPdPesVUTIdsrnTv2Fz783BDAA"
        
        try:
            await page.goto(cdn_test_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"[!] CDN navigation: {e}")
        
        # Get all cookies again after navigation
        final_cookies = await context.cookies()
        print(f"[+] Total cookies after navigation: {len(final_cookies)}")
        
        # Look for Edge-Cache-Cookie
        edge_cache_cookie = None
        for cookie in final_cookies:
            if cookie['name'] == 'Edge-Cache-Cookie':
                edge_cache_cookie = cookie
                print(f"[+] FOUND Edge-Cache-Cookie!")
                print(f"    Value: {cookie['value'][:100]}...")
                break
        
        # Save results
        result = {
            'timestamp': datetime.now().isoformat(),
            'total_cookies': len(final_cookies),
            'cookies': {c['name']: c['value'] for c in final_cookies},
            'edge_cache_cookie': edge_cache_cookie,
            'device_token': device_token is not None
        }
        
        with open('cookies.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        if edge_cache_cookie:
            with open('edge_cache_cookie.txt', 'w') as f:
                f.write(f"Edge-Cache-Cookie={edge_cache_cookie['value']}\n")
                f.write(f"\nFull details:\n")
                f.write(json.dumps(edge_cache_cookie, indent=2))
            print("[+] Saved Edge-Cache-Cookie!")
        else:
            with open('edge_cache_cookie.txt', 'w') as f:
                f.write("Edge-Cache-Cookie NOT FOUND\n\n")
                f.write("All cookies found:\n")
                for c in final_cookies:
                    f.write(f"{c['name']}\n")
            print("[-] Edge-Cache-Cookie not found")
            print("    Cookies found:", [c['name'] for c in final_cookies])
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())
