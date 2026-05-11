import asyncio
import random
import json
import re
import logging
import html as htmlmod
from datetime import datetime
from scrapling import StealthyFetcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dubicars_spider")


class EnhancedDubicarsSpider:
    """
    Enhanced Dubicars scraper for NEW cars.
    
    Extraction strategy:
    1. Parse <li class="serp-list-item"> cards
    2. Read JSON from data-sp-item attribute (price, year, mileage, etc.)
    3. Extract title from get_all_text() or link text
    4. Extract URL from a.image-container link
    
    Note: scrapling's Selector uses .text (property) not .text() (method)
    """

    BASE_URL = "https://www.dubicars.com"
    SEARCH_URL = "https://www.dubicars.com/uae/new"

    def __init__(self, max_pages=50, scrape_details=False, min_delay=2, max_delay=5):
        self.max_pages = max_pages
        self.scrape_details = scrape_details
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.fetcher = StealthyFetcher()
        self.listings = []
        self.stats = {"pages_scraped": 0, "listings_found": 0, "details_scraped": 0, "errors": 0}

    async def _scrape_page(self, page_num):
        """Scrape a single page of new car listings."""
        url = f"{self.SEARCH_URL}?page={page_num}"
        logger.info(f"Scraping page {page_num}: {url}")

        try:
            page = await asyncio.to_thread(
                self.fetcher.fetch, url, headless=True
            )
            if not page or page.status != 200:
                logger.warning(f"Page {page_num}: HTTP {page.status if page else 'None'}")
                return []
        except Exception as e:
            logger.error(f"Failed to fetch page {page_num}: {e}")
            return []

        listings = []

        # Find listing cards
        cards = page.css("li.serp-list-item")
        if not cards:
            cards = page.css("li[data-sp-item]")

        logger.info(f"Page {page_num}: Found {len(cards) if cards else 0} card elements")

        for card in (cards or []):
            try:
                listing = self._parse_card(card)
                if listing and listing.get("price"):
                    listings.append(listing)
            except Exception as e:
                logger.debug(f"Error parsing card: {e}")
                self.stats["errors"] += 1

        return listings

    def _parse_card(self, card):
        """Parse a single listing card."""
        listing = {
            "source": "dubicars",
            "currency": "AED",
            "scraped_at": datetime.now().isoformat(),
            "extraction_method": "dom",
        }

        # ─── 1. Extract data-sp-item JSON ───
        sp_raw = str(card.attrib.get("data-sp-item", ""))
        sp_data = {}
        if sp_raw:
            try:
                sp_data = json.loads(sp_raw)
            except json.JSONDecodeError:
                try:
                    sp_data = json.loads(htmlmod.unescape(sp_raw))
                except Exception:
                    pass

        if sp_data:
            # 'rpr' is retail price, 'pr' may be discounted. Use rpr first.
            listing["price"] = sp_data.get("rpr") or sp_data.get("pr")
            listing["year"] = sp_data.get("y", "")
            listing["mileage"] = sp_data.get("km", 0)
            listing["is_new"] = sp_data.get("new", False)
            listing["seller_type"] = "dealer" if sp_data.get("st") == "dealer" else sp_data.get("st", "")
            listing["listing_id"] = sp_data.get("id", "")
            listing["photos_count"] = sp_data.get("imgc", 0)

        # ─── 2. Extract URL from image-container link ───
        links = card.css("a")
        listing["url"] = ""
        for link in (links or []):
            cls = str(link.attrib.get("class", ""))
            href = str(link.attrib.get("href", ""))
            if "image-container" in cls and href and ".html" in href:
                listing["url"] = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                break

        # ─── 3. Extract price from <strong> ───
        strongs = card.css("strong")
        for s in (strongs or []):
            txt = str(s.text).strip()
            if "AED" in txt and "/" not in txt:  # skip "AED X / month"
                price = self._clean_price(txt)
                if price:
                    listing["price"] = listing.get("price") or price
                break

        # ─── 4. Extract title from full text ───
        full_text = str(card.get_all_text())
        title = ""
        for line in full_text.split("\n"):
            line = line.strip()
            if line.startswith(("New ", "Used ")) and len(line) > 10:
                title = line
                break

        listing["title"] = title

        # ─── 5. Parse brand/model from title ───
        if title:
            parsed = self._parse_title(title)
            listing["brand"] = parsed.get("brand", "")
            listing["model"] = parsed.get("model", "")
        else:
            listing["brand"] = ""
            listing["model"] = ""

        # ─── 6. Extract specs from spans ───
        spans = card.css("span")
        listing["location"] = ""
        listing["specs_origin"] = ""

        locations = {"dubai", "abu dhabi", "sharjah", "ajman", "ras al-khaimah",
                      "fujairah", "al ain", "umm al-quwain"}
        specs_origins = {"gcc", "european", "american", "japanese", "korean",
                          "chinese", "other"}

        for s in (spans or []):
            txt = str(s.text).strip()
            if not txt or len(txt) < 2:
                continue
            txt_lower = txt.lower()
            if txt_lower in locations:
                listing["location"] = txt
            elif any(spec in txt_lower for spec in specs_origins):
                listing["specs_origin"] = txt
            elif "km" in txt_lower and any(c.isdigit() for c in txt):
                listing["mileage"] = listing.get("mileage") or self._clean_mileage(txt)

        # ─── 7. Clean up ───
        if listing.get("price"):
            listing["price"] = self._clean_price(str(listing["price"]))

        return listing if listing.get("price") else None

    def _parse_title(self, title):
        """Parse a title like 'New Mercedes-Benz G 63 AMG 2026' into brand/model."""
        clean = re.sub(r'^(New|Used)\s+', '', title).strip()
        # Remove trailing year
        clean = re.sub(r'\s+\d{4}\s*$', '', clean).strip()

        brands = [
            "Mercedes-Benz", "Land Rover", "Range Rover", "Rolls-Royce",
            "Aston Martin", "Alfa Romeo", "Mercedes", "BMW", "Audi",
            "Toyota", "Nissan", "Honda", "Hyundai", "Kia", "Ford",
            "Chevrolet", "GMC", "Jeep", "Dodge", "Lexus", "Porsche",
            "Lamborghini", "Ferrari", "Maserati", "Bentley", "Jaguar",
            "Volkswagen", "Volvo", "Mazda", "Mitsubishi", "Subaru",
            "Infiniti", "Cadillac", "Lincoln", "Chrysler", "Mini",
            "Peugeot", "Renault", "Suzuki", "Isuzu", "BRABUS",
            "MG", "BYD", "Chery", "Geely", "Haval", "GAC", "Jetour",
            "Changan", "Great Wall", "Foton", "JAC", "BAIC", "Hongqi",
            "Genesis", "Lucid", "Rivian", "Tesla", "Polestar",
            "RAM", "Cupra", "Lotus", "McLaren", "Bugatti", "Pagani",
        ]

        found_brand = ""
        model = clean
        for brand in brands:
            if clean.lower().startswith(brand.lower()):
                found_brand = brand
                model = clean[len(brand):].strip()
                # Clean model: remove leading dash/hyphen
                model = re.sub(r'^[\s\-]+', '', model).strip()
                break

        return {"brand": found_brand, "model": model}

    async def scrape_detail_page(self, listing):
        """Scrape individual listing page for richer data."""
        url = listing.get("url", "")
        if not url:
            return listing

        try:
            page = await asyncio.to_thread(self.fetcher.fetch, url, headless=True)
            if not page or page.status != 200:
                return listing

            # Try JSON-LD on detail page
            html = page.html_content
            json_ld_matches = re.findall(
                r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
                html, re.DOTALL
            )
            for match in json_ld_matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict) and data.get("@type") in ("Vehicle", "Car"):
                        listing["fuel_type"] = listing.get("fuel_type") or data.get("fuelType", "")
                        listing["transmission"] = listing.get("transmission") or data.get("vehicleTransmission", "")
                        listing["body_type"] = listing.get("body_type") or data.get("bodyType", "")
                        listing["color"] = listing.get("color") or data.get("color", "")
                        listing["description"] = (data.get("description", "") or "")[:500]
                except json.JSONDecodeError:
                    continue

            self.stats["details_scraped"] += 1

        except Exception as e:
            logger.debug(f"Detail scrape failed for {url}: {e}")

        return listing

    async def scrape_all(self):
        """Main scraping loop."""
        consecutive_empty = 0

        for page_num in range(1, self.max_pages + 1):
            page_listings = await self._scrape_page(page_num)

            if not page_listings:
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    logger.info(f"3 consecutive empty pages. Stopping at page {page_num}.")
                    break
            else:
                consecutive_empty = 0

            self.listings.extend(page_listings)
            self.stats["pages_scraped"] += 1
            self.stats["listings_found"] += len(page_listings)

            logger.info(f"Page {page_num}: {len(page_listings)} listings (total: {len(self.listings)})")
            await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))

        # Optionally scrape detail pages for richer data
        if self.scrape_details:
            logger.info(f"Scraping detail pages for {len(self.listings)} listings...")
            for i, listing in enumerate(self.listings):
                self.listings[i] = await self.scrape_detail_page(listing)
                if i % 10 == 0:
                    logger.info(f"Detail progress: {i}/{len(self.listings)}")
                await asyncio.sleep(random.uniform(1, 3))

        logger.info(f"Dubicars scraping complete. Stats: {self.stats}")
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
