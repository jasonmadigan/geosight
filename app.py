from flask import Flask, request, render_template
import dns.resolver
from playwright.async_api import async_playwright
import asyncio
import os
from geo_config import dns_servers
from threading import Thread
import asyncio


# This code ensures that the screenshots directory exists
screenshots_dir = 'static/screenshots'
if not os.path.exists(screenshots_dir):
    os.makedirs(screenshots_dir)

def resolve_dns(domain, dns_server, location):
    print(f"Resolving DNS for {domain} in {location} using {dns_server}")

    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = [dns_server]
    try:
        answers = resolver.resolve(domain, 'A')
        ip_addresses = [answer.to_text() for answer in answers]
        print(f"Resolved IP addresses: {ip_addresses}")
        return ip_addresses
    except Exception as e:
        print(f"DNS resolution error: {e}")
        return []


async def take_screenshot(url, ip_addresses, location):
    # Use the provided IP addresses instead of performing DNS lookup again
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        # Go to the first IP address resolved
        if ip_addresses:
            await page.goto('http://' + ip_addresses[0])
        else:
            # Handle error or do something else if DNS resolution failed
            pass
        screenshot_path = f'screenshots/{location}_{url.replace("http://", "").replace("https://", "").replace("/", "_")}.png'
        await page.screenshot(path=f'static/{screenshot_path}')
        await browser.close()
        return screenshot_path


def get_screenshot(url, dns_server, location):
    def start_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    new_loop = asyncio.new_event_loop()
    t = Thread(target=start_loop, args=(new_loop,))
    t.start()

    async def async_get_screenshot():
        return await take_screenshot(url, dns_server, location)

    future = asyncio.run_coroutine_threadsafe(async_get_screenshot(), new_loop)
    return future.result()

async def gather_screenshots(url):
    tasks = []
    for location, dns_server in dns_servers.items():
        dns_info = resolve_dns(url, dns_server, location)
        task = asyncio.create_task(get_screenshot(url, dns_info, location))
        tasks.append(task)
    return await asyncio.gather(*tasks)


app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    screenshots = []
    url = ''
    if request.method == 'POST':
        url = request.form['url'].replace('http://', '').replace('https://', '').split('/')[0]
        for location, dns_server in dns_servers.items():
            dns_info = resolve_dns(url, dns_server, location)
            screenshot_path = get_screenshot(url, dns_info, location)
            screenshots.append((location, {'screenshot': screenshot_path, 'dns_info': dns_info}))
    return render_template('index.html', screenshots=screenshots, original_url=url)



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001, threaded=False)
