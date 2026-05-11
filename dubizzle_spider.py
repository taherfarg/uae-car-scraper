import asyncio
import random
import json
import logging
import re
from datetime import datetime
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dubizzle_spider")


class EnhancedDubizzleSpider:
    """
    Enhanced Dubizzle scraper for NEW cars.

    Uses Playwright with a real Chromium browser to bypass Imperva
    anti-bot protection. Extracts listing data from the __NEXT_DATA__
    JSON blob embedded in the page source.
    """

    BASE_URL = "https://uae.dubizzle.com/motors/new-cars"

    def __init__(self, max_pages=50, min_delay=2, max_delay=5):
        self.max_pages = max_pages
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.listings = []
        self.failed_pages = []
        self.stats = {"pages_scraped": 0, "listings_found": 0, "errors": 0}
        self._browser = None
        self._context = None
        self._page = None

    async def _init_browser(self):
        """Launch a Playwright Chromium browser with stealth-like settings."""
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        # Remove the webdriver flag to reduce detection
        await self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self._page = await self._context.new_page()
        logger.info("Playwright browser launched")

    async def _close_browser(self):
        """Gracefully close the browser."""
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    def _extract_from_html(self, html):
        """
        Extract listings from raw HTML by finding the __NEXT_DATA__ JSON blob.
        """
        listings = []

        # Check if page is blocked by Imperva
        if "Pardon Our Interruption" in html or len(html) < 10000:
            logger.warning("Page appears to be blocked by Imperva anti-bot protection")
            return listings

        # Find __NEXT_DATA__ JSON
        match = re.search(
            r'<script\s+id="__NEXT_DATA__"\s+type="application/json">(.*?)</script>',
            html, re.DOTALL
        )
        if not match:
            logger.warning("__NEXT_DATA__ not found in page HTML")
            return listings

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse __NEXT_DATA__: {e}")
            return listings

        # Navigate to the hits array
        actions = (
            data.get("props", {})
            .get("pageProps", {})
            .get("reduxWrapperActionsGIPP", [])
        )

        for action in actions:
            payload = action.get("payload", {})
            if not isinstance(payload, dict):
                continue
            hits = payload.get("hits")
            if hits and isinstance(hits, list):
                for hit in hits:
                    try:
                        listing = self._parse_hit(hit)
                        if listing and listing.get("price"):
                            listings.append(listing)
                    except Exception as e:
                        logger.debug(f"Error parsing hit: {e}")
                        self.stats["errors"] += 1

        return listings

    def _parse_hit(self, hit):
        """Parse a single hit from the __NEXT_DATA__ payload."""
        details = hit.get("details", {})

        def get_detail(key):
            """Safely extract an English detail value."""
            d = details.get(key, {})
            if not isinstance(d, dict):
                return ""
            en = d.get("en", {})
            if not isinstance(en, dict):
                return str(en) if en else ""
            val = en.get("value", "")
            if isinstance(val, list):
                return ", ".join(str(v) for v in val)
            return str(val) if val else ""

        # Name
        name_obj = hit.get("name", {})
        title = name_obj.get("en", "") if isinstance(name_obj, dict) else str(name_obj)

        # Price
        price = hit.get("price")
        if price is not None:
            price = self._clean_price(str(price))

        # URL
        url_obj = hit.get("absolute_url", {})
        url = url_obj.get("en", "") if isinstance(url_obj, dict) else str(url_obj)

        # Location
        loc_obj = hit.get("location_list", hit.get("places", {}))
        if isinstance(loc_obj, dict):
            places = loc_obj.get("en", [])
            location = ", ".join(places[1:3]) if len(places) > 1 else (places[0] if places else "")
        else:
            location = ""

        # Mileage
        km_raw = get_detail("Kilometers")
        mileage = self._clean_mileage(str(km_raw)) if km_raw else 0

        return {
            "title": title,
            "price": price,
            "currency": "AED",
            "year": get_detail("Year") or "",
            "mileage": mileage,
            "brand": get_detail("Make") or "",
            "model": get_detail("Model") or "",
            "trim": get_detail("Trim") or get_detail("Motors Trim") or "",
            "body_type": get_detail("Body Type") or "",
            "fuel_type": get_detail("Fuel Type") or "",
            "transmission": get_detail("Transmission Type") or "",
            "color": get_detail("Exterior Color") or "",
            "interior_color": get_detail("Interior Color") or "",
            "cylinders": get_detail("No. of Cylinders") or "",
            "horsepower": get_detail("Horsepower") or "",
            "engine_cc": get_detail("Engine Capacity (cc)") or "",
            "doors": get_detail("Doors") or "",
            "specs_origin": get_detail("Regional Specs") or "",
            "seller_type": hit.get("seller_type", ""),
            "location": location,
            "url": url,
            "photos_count": hit.get("photos_count", 0),
            "has_warranty": bool(get_detail("Warranty")),
            "source": "dubizzle",
            "scraped_at": datetime.now().isoformat(),
            "extraction_method": "next_data",
            "dealer": get_detail("Agent") or hit.get("seller_name", ""),
            "publish_date": datetime.fromtimestamp(hit.get("added")).isoformat() if hit.get("added") else "",
        }

    async def _fetch_page(self, url, max_retries=3):
        """Fetch a page using Playwright with retry logic."""
        for attempt in range(max_retries):
            try:
                response = await self._page.goto(
                    url,
                    wait_until="load",
                    timeout=45000,
                )
                if response and response.status == 200:
                    # Wait for the __NEXT_DATA__ script to appear
                    try:
                        await self._page.wait_for_selector(
                            'script#__NEXT_DATA__', timeout=10000
                        )
                    except Exception:
                        logger.debug("__NEXT_DATA__ selector not found, trying content anyway")
                    html = await self._page.content()
                    return html
                elif response and response.status == 429:
                    wait_time = (2 ** attempt) * 5
                    logger.warning(f"Rate limited (429). Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    status = response.status if response else "None"
                    logger.warning(f"Got status {status} for {url}")
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {url}: {e}")
                await asyncio.sleep(2 ** attempt)
        return None

    async def scrape_page(self, page_num):
        """Scrape a single page of listings."""
        url = f"{self.BASE_URL}/?page={page_num}"
        logger.info(f"Scraping page {page_num}: {url}")

        html = await self._fetch_page(url)
        if not html:
            self.failed_pages.append(page_num)
            return []

        listings = self._extract_from_html(html)

        if not listings:
            logger.warning(f"No listings extracted from page {page_num}")

        self.stats["pages_scraped"] += 1
        self.stats["listings_found"] += len(listings)

        logger.info(f"Page {page_num}: Found {len(listings)} listings")
        return listings

    async def scrape_all(self):
        """Scrape all pages with rate limiting."""
        await self._init_browser()

        try:
            consecutive_empty = 0
            for page_num in range(1, self.max_pages + 1):
                page_listings = await self.scrape_page(page_num)
                self.listings.extend(page_listings)

                if not page_listings:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        logger.info(f"3 consecutive empty pages. Stopping at page {page_num}.")
                        break
                else:
                    consecutive_empty = 0

                delay = random.uniform(self.min_delay, self.max_delay)
                await asyncio.sleep(delay)

            # Retry failed pages once
            if self.failed_pages:
                logger.info(f"Retrying {len(self.failed_pages)} failed pages...")
                retry_pages = self.failed_pages.copy()
                self.failed_pages.clear()
                for page_num in retry_pages:
                    page_listings = await self.scrape_page(page_num)
                    self.listings.extend(page_listings)
                    await asyncio.sleep(random.uniform(3, 6))
        finally:
            await self._close_browser()

        logger.info(f"Scraping complete. Stats: {self.stats}")
        return self.listings

    @staticmethod
    def _clean_price(price_str):
        if not price_str:
            return None
        cleaned = re.sub(r'[^\d.]', '', str(price_str))
        try:
            price = float(cleaned)
            return price if 3000 <= price <= 50_000_000 else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _clean_mileage(mileage_str):
        if not mileage_str:
            return None
        cleaned = re.sub(r'[^\d]', '', str(mileage_str))
        try:
            mileage = int(cleaned)
            return mileage if 0 <= mileage <= 1_000_000 else None
        except (ValueError, TypeError):
            return None
