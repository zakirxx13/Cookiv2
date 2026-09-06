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
        
        # Listen for network requests
        network_data = {
            'requests': [],
            'responses': [],
            'cookies': [],
            'timestamp': datetime.now().isoformat()
        }
        
        def handle_route(route, request):
            network_data['requests'].append({
                'url': request.url,
                'method': request.method,
                'headers': dict(request.headers),
            })
            route.continue_()
        
        def handle_response(response):
            network_data['responses'].append({
                'url': response.url,
                'status': response.status,
                'headers': dict(response.headers),
            })
        
        await page.route("**/*", handle_route)
        page.on("response", handle_response)
        
        # Navigate and wait for full load
        print("[*] Navigating to page...")
        await page.goto(TARGET_URL, wait_until='networkidle')
        
        # Wait a bit more for JavaScript to set cookies
        print("[*] Waiting for JavaScript cookies...")
        await page.wait_for_timeout(5000)
        
        # Get all cookies
        cookies = await context.cookies()
        print(f"[+] Found {len(cookies)} cookies")
        
        # Look for Edge-Cache-Cookie specifically
        edge_cache_cookie = None
        for cookie in cookies:
            if cookie['name'] == 'Edge-Cache-Cookie':
                edge_cache_cookie = cookie
                print(f"[+] FOUND Edge-Cache-Cookie!")
                break
        
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
            print(f"[+] Saved Edge-Cache-Cookie to edge_cache_cookie.txt")
        else:
            with open('edge_cache_cookie.txt', 'w') as f:
                f.write("Edge-Cache-Cookie NOT FOUND\n\n")
                f.write("Available cookies:\n")
                for c in cookies:
                    f.write(f"  - {c['name']}\n")
            print("[-] Edge-Cache-Cookie not found")
        
        # Get localStorage
        local_storage = await page.evaluate("() => JSON.stringify(localStorage)")
        
        # Get sessionStorage
        session_storage = await page.evaluate("() => JSON.stringify(sessionStorage)")
        
        # Network summary
        network_summary = {
            'timestamp': datetime.now().isoformat(),
            'url': TARGET_URL,
            'cookies_found': len(cookies),
            'edge_cache_cookie_found': edge_cache_cookie is not None,
            'edge_cache_cookie_value': edge_cache_cookie['value'] if edge_cache_cookie else None,
            'local_storage': json.loads(local_storage) if local_storage else {},
            'session_storage': json.loads(session_storage) if session_storage else {},
            'network_requests': len(network_data['requests']),
            'api_endpoints': [r['url'] for r in network_data['requests'] if 'api' in r['url'].lower()],
            'cdn_requests': [r['url'] for r in network_data['requests'] if 'cdn' in r['url'].lower() or 'bldcm' in r['url'].lower()],
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
            print(f"Cookie value preview: {edge_cache_cookie['value'][:50]}...")
        print(f"Network requests: {len(network_data['requests'])}")
        print(f"API endpoints found: {len(network_summary['api_endpoints'])}")
        print(f"CDN requests: {len(network_summary['cdn_requests'])}")
        print("="*60)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())
