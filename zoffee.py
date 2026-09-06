#!/usr/bin/env python3
import json
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

TARGET_URL = "https://toffeelive.com/en"

async def scrape():
    print(f"[*] Starting Playwright scraper for {TARGET_URL}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
        )
        
        page = await context.new_page()
        
        # Storage for network data
        network_requests = []
        network_responses = []
        
        # Handle routes properly with await
        async def handle_route(route, request):
            network_requests.append({
                'url': request.url,
                'method': request.method,
                'headers': dict(request.headers),
            })
            await route.continue_()  # FIXED: added await
        
        def handle_response(response):
            network_responses.append({
                'url': response.url,
                'status': response.status,
                'headers': dict(response.headers),
            })
        
        await page.route("**/*", handle_route)
        page.on("response", handle_response)
        
        # Navigate with longer timeout and less strict wait
        print("[*] Navigating to page...")
        try:
            await page.goto(TARGET_URL, wait_until='domcontentloaded', timeout=60000)
            print("[+] Page DOM loaded")
        except Exception as e:
            print(f"[!] Navigation warning: {e}")
            # Try anyway
        
        # Wait for network to be mostly idle
        print("[*] Waiting for network...")
        await page.wait_for_timeout(8000)  # Wait 8 seconds for JS to run
        
        # Get all cookies
        cookies = await context.cookies()
        print(f"[+] Found {len(cookies)} cookies")
        
        # Look for Edge-Cache-Cookie
        edge_cache_cookie = None
        for cookie in cookies:
            print(f"  - {cookie['name']}: {cookie['value'][:30]}..." if len(cookie['value']) > 30 else f"  - {cookie['name']}: {cookie['value']}")
            if cookie['name'] == 'Edge-Cache-Cookie':
                edge_cache_cookie = cookie
                print(f"[+] FOUND Edge-Cache-Cookie!")
        
        # Save all cookies
        cookies_data = {
            'timestamp': datetime.now().isoformat(),
            'url': TARGET_URL,
            'total_cookies': len(cookies),
            'cookies': cookies,
            'edge_cache_cookie': edge_cache_cookie
        }
        
        with open('cookies.json', 'w') as f:
            json.dump(cookies_data, f, indent=2)
        
        # Save Edge-Cache-Cookie separately
        if edge_cache_cookie:
            with open('edge_cache_cookie.txt', 'w') as f:
                f.write(f"Edge-Cache-Cookie={edge_cache_cookie['value']}\n\n")
                f.write(f"Full cookie data:\n")
                f.write(json.dumps(edge_cache_cookie, indent=2))
            print(f"[+] Saved Edge-Cache-Cookie")
        else:
            with open('edge_cache_cookie.txt', 'w') as f:
                f.write("Edge-Cache-Cookie NOT FOUND\n\n")
                f.write("All cookies found:\n")
                for c in cookies:
                    f.write(f"{c['name']}={c['value'][:50]}\n")
            print("[-] Edge-Cache-Cookie not found")
        
        # Get storage
        local_storage = await page.evaluate("() => { try { return JSON.stringify(localStorage); } catch(e) { return '{}'; } }")
        session_storage = await page.evaluate("() => { try { return JSON.stringify(sessionStorage); } catch(e) { return '{}'; } }")
        
        # Summary
        network_summary = {
            'timestamp': datetime.now().isoformat(),
            'url': TARGET_URL,
            'cookies_found': len(cookies),
            'edge_cache_cookie_found': edge_cache_cookie is not None,
            'edge_cache_cookie_value': edge_cache_cookie['value'] if edge_cache_cookie else None,
            'local_storage': json.loads(local_storage) if local_storage else {},
            'session_storage': json.loads(session_storage) if session_storage else {},
            'network_requests': len(network_requests),
            'api_endpoints': list(set([r['url'] for r in network_requests if 'api' in r['url'].lower()])),
            'cdn_requests': list(set([r['url'] for r in network_requests if 'cdn' in r['url'].lower() or 'bldcm' in r['url'].lower()])),
        }
        
        with open('network_data.json', 'w') as f:
            json.dump(network_summary, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("PLAYWRIGHT SCRAPE SUMMARY")
        print("="*60)
        print(f"Total cookies: {len(cookies)}")
        print(f"Edge-Cache-Cookie: {'FOUND' if edge_cache_cookie else 'NOT FOUND'}")
        if edge_cache_cookie:
            print(f"Cookie length: {len(edge_cache_cookie['value'])} chars")
        print(f"Network requests: {len(network_requests)}")
        print(f"API endpoints: {len(network_summary['api_endpoints'])}")
        print(f"CDN requests: {len(network_summary['cdn_requests'])}")
        print("="*60)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())
