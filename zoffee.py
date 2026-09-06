#!/usr/bin/env python3
import requests
import json
import re
import os
from urllib.parse import urljoin, urlparse
from datetime import datetime

TARGET_URL = "https://toffeelive.com/en"
OUTPUT_DIR = "."

def analyze_network():
    print(f"[*] Starting network analysis on {TARGET_URL}")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    })
    
    # Primary request
    print("[*] Fetching main page...")
    resp = session.get(TARGET_URL, timeout=30)
    print(f"[+] Status: {resp.status_code}")
    
    # Collect all cookies
    cookies_data = {
        'timestamp': datetime.now().isoformat(),
        'url': TARGET_URL,
        'cookies': [],
        'session_cookies': session.cookies.get_dict()
    }
    
    for cookie in session.cookies:
        cookies_data['cookies'].append({
            'name': cookie.name,
            'value': cookie.value,
            'domain': cookie.domain,
            'path': cookie.path,
            'secure': cookie.secure,
            'expires': cookie.expires,
            'http_only': getattr(cookie, '_rest', {}).get('HttpOnly', False)
        })
    
    # Save cookies only
    with open(f'{OUTPUT_DIR}/cookies.json', 'w') as f:
        json.dump(cookies_data, f, indent=2)
    print(f"[+] Saved {len(cookies_data['cookies'])} cookies to cookies.json")
    
    # Network analysis - find everything
    network_data = {
        'timestamp': datetime.now().isoformat(),
        'base_url': TARGET_URL,
        'status_code': resp.status_code,
        'headers': dict(resp.headers),
        'request_headers': dict(resp.request.headers),
        'final_url': resp.url,
        'content_length': len(resp.text),
        'content_type': resp.headers.get('Content-Type', 'unknown'),
        
        # Extracted data
        'api_endpoints': [],
        'stream_urls': [],
        'cdn_urls': [],
        'javascript_files': [],
        'css_files': [],
        'image_urls': [],
        'external_links': [],
        'json_data': [],
        'csrf_tokens': [],
        'bearer_tokens': [],
        'base64_strings': []
    }
    
    text = resp.text
    
    # Find API endpoints
    api_patterns = [
        r'(https?://[^"\s\'<>]+/api/[^"\s\'<>]+)',
        r'(https?://[^"\s\'<>]+/v\d+/[^"\s\'<>]+)',
        r'(https?://[^"\s\'<>]+/graphql[^"\s\'<>]*)',
        r'"api[_-]?url"\s*:\s*"([^"]+)"',
        r'"endpoint"\s*:\s*"([^"]+)"',
        r'"base[_-]?url"\s*:\s*"([^"]+)"',
        r'fetch\(["\']([^"\']+)["\']',
        r'axios\.(get|post)\(["\']([^"\']+)["\']',
        r'url\s*:\s*["\']([^"\']+)["\']',
    ]
    
    for pattern in api_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                match = match[-1]
            if match.startswith('http'):
                network_data['api_endpoints'].append(match)
    
    # Find stream/CDN URLs
    stream_patterns = [
        r'(https?://[^"\s\'<>]+\.m3u8[^"\s\'<>]*)',
        r'(https?://[^"\s\'<>]+\.mp4[^"\s\'<>]*)',
        r'(https?://[^"\s\'<>]+\.ts[^"\s\'<>]*)',
        r'(https?://[^"\s\'<>]+\.m4s[^"\s\'<>]*)',
        r'"stream[_-]?url"\s*:\s*"([^"]+)"',
        r'"playback[_-]?url"\s*:\s*"([^"]+)"',
        r'"video[_-]?url"\s*:\s*"([^"]+)"',
        r'"cdn[_-]?url"\s*:\s*"([^"]+)"',
        r'(https?://[^"\s\'<>]*cdn[^"\s\'<>]*\.[^"\s\'<>]+)',
        r'(https?://[^"\s\'<>]*bldcm[^"\s\'<>]*\.[^"\s\'<>]+)',
    ]
    
    for pattern in stream_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[-1]
            if 'cdn' in match.lower() or 'bldcm' in match.lower():
                network_data['cdn_urls'].append(match)
            else:
                network_data['stream_urls'].append(match)
    
    # Find JS files
    js_matches = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', text)
    for js in js_matches:
        full_url = urljoin(TARGET_URL, js)
        network_data['javascript_files'].append(full_url)
    
    # Find CSS files
    css_matches = re.findall(r'<link[^>]+href=["\']([^"\']+\.css)["\']', text)
    for css in css_matches:
        full_url = urljoin(TARGET_URL, css)
        network_data['css_files'].append(full_url)
    
    # Find images
    img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', text)
    for img in img_matches:
        if img.startswith('data:'):
            network_data['base64_strings'].append(img[:100] + '...')
        else:
            full_url = urljoin(TARGET_URL, img)
            network_data['image_urls'].append(full_url)
    
    # Find external links
    link_matches = re.findall(r'href=["\'](https?://[^"\']+)["\']', text)
    network_data['external_links'] = list(set(link_matches))
    
    # Find JSON data in script tags
    json_scripts = re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL)
    for script in json_scripts:
        try:
            # Look for JSON objects
            json_matches = re.findall(r'\{[^{}]*"[^"]+"[^{}]*\}', script)
            for j in json_matches:
                if '"url"' in j or '"api"' in j or '"token"' in j:
                    network_data['json_data'].append(j[:500])
        except:
            pass
    
    # Find CSRF tokens
    csrf_patterns = [
        r'"csrf[_-]?token"\s*:\s*"([^"]+)"',
        r'name=["\']csrf[_-]?token["\'][^>]+value=["\']([^"\']+)["\']',
        r'<meta[^>]+csrf[^>]+content=["\']([^"\']+)["\']',
    ]
    for pattern in csrf_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        network_data['csrf_tokens'].extend(matches)
    
    # Find Bearer tokens
    bearer_patterns = [
        r'"token"\s*:\s*"([^"]{20,})"',
        r'"access[_-]?token"\s*:\s*"([^"]+)"',
        r'"auth[_-]?token"\s*:\s*"([^"]+)"',
        r'Bearer\s+([a-zA-Z0-9_\-\.]+)',
        r'authorization["\']?\s*:\s*["\']?([a-zA-Z0-9_\-\.]+)',
    ]
    for pattern in bearer_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        network_data['bearer_tokens'].extend(matches)
    
    # Remove duplicates
    network_data['api_endpoints'] = list(set(network_data['api_endpoints']))
    network_data['stream_urls'] = list(set(network_data['stream_urls']))
    network_data['cdn_urls'] = list(set(network_data['cdn_urls']))
    
    # Save network data (without raw cookies for cleaner output)
    network_summary = {k: v for k, v in network_data.items() if k != 'raw_cookies'}
    with open(f'{OUTPUT_DIR}/network_data.json', 'w') as f:
        json.dump(network_summary, f, indent=2)
    
    # Save API endpoints as text
    with open(f'{OUTPUT_DIR}/api_endpoints.txt', 'w') as f:
        f.write(f"API Endpoints Found ({len(network_data['api_endpoints'])}):\n")
        f.write("="*50 + "\n")
        for url in sorted(network_data['api_endpoints']):
            f.write(f"{url}\n")
        
        f.write(f"\n\nStream URLs ({len(network_data['stream_urls'])}):\n")
        f.write("="*50 + "\n")
        for url in sorted(network_data['stream_urls']):
            f.write(f"{url}\n")
        
        f.write(f"\n\nCDN URLs ({len(network_data['cdn_urls'])}):\n")
        f.write("="*50 + "\n")
        for url in sorted(network_data['cdn_urls']):
            f.write(f"{url}\n")
        
        f.write(f"\n\nJavaScript Files ({len(network_data['javascript_files'])}):\n")
        f.write("="*50 + "\n")
        for url in sorted(network_data['javascript_files']):
            f.write(f"{url}\n")
    
    # Save headers
    with open(f'{OUTPUT_DIR}/headers.json', 'w') as f:
        json.dump({
            'response_headers': network_data['headers'],
            'request_headers': network_data['request_headers']
        }, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("NETWORK ANALYSIS SUMMARY")
    print("="*60)
    print(f"Cookies found: {len(cookies_data['cookies'])}")
    print(f"API endpoints: {len(network_data['api_endpoints'])}")
    print(f"Stream URLs: {len(network_data['stream_urls'])}")
    print(f"CDN URLs: {len(network_data['cdn_urls'])}")
    print(f"JS files: {len(network_data['javascript_files'])}")
    print(f"CSRF tokens: {len(network_data['csrf_tokens'])}")
    print(f"Bearer tokens: {len(network_data['bearer_tokens'])}")
    print("="*60)
    print("\nFiles created:")
    print("  - cookies.json (shudhu cookies)")
    print("  - network_data.json (shob kisu details)")
    print("  - api_endpoints.txt (text format e URLs)")
    print("  - headers.json (request & response headers)")

if __name__ == "__main__":
    analyze_network()
