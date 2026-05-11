import asyncio
import json
import re
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="en-US",
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await context.new_page()
        response = await page.goto("https://uae.dubizzle.com/motors/new-cars/?page=1", wait_until="load")
        
        await page.wait_for_selector("#__NEXT_DATA__", state="attached", timeout=45000)
        html = await page.content()
        match = re.search(r'<script\s+id="__NEXT_DATA__"\s+type="application/json">(.*?)</script>', html, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            actions = data.get("props", {}).get("pageProps", {}).get("reduxWrapperActionsGIPP", [])
            for action in actions:
                payload = action.get("payload", {})
                if isinstance(payload, dict):
                    hits = payload.get("hits")
                    if hits and isinstance(hits, list):
                        hit = hits[0]
                        print("added:", hit.get("added"))
                        print("created_at:", hit.get("created_at"))
                        print("user:", hit.get("user"))
                        print("Agent in details:", hit.get("details", {}).get("Agent"))
                        break
        await browser.close()

asyncio.run(main())
