import asyncio
import re
import time
from scrapling.spiders import Spider, Request, Response
from scrapling.fetchers import FetcherSession

class DubicarsSpider(Spider):
    name = "dubicars_cars"
    start_urls = ["https://www.dubicars.com/search"]
    concurrent_requests = 1
    
    custom_settings = {
        "page_limit": 2000
    }

    def configure_sessions(self, manager):
        manager.add("stealth", FetcherSession())

    async def parse(self, response: Response):
        # Try finding standard car cards
        cards = response.xpath('//*[contains(@class, "car-card") or contains(@class, "car-box") or contains(@class, "list-item") or contains(@class, "serp-list-item")]')
        
        # fallback: find AED
        if not cards:
            prices = response.xpath('//*[contains(text(), "AED")]')
            if prices:
                cards = []
                for p in prices:
                    if p.parent and p.parent.parent and p.parent.parent.parent:
                        cards.append(p.parent.parent.parent.parent)
        
        items_found = 0
        for card in cards:
            try:
                # Title
                title_candidates = card.css('h2::text').getall() + card.css('h3::text').getall() + card.css('.title::text').getall()
                title = " ".join([t.strip() for t in title_candidates if len(t.strip()) > 5])
                
                # Price
                price_elems = card.xpath('.//*[contains(text(), "AED")]')
                price = price_elems[0].text if price_elems else None
                
                # Link
                link = card.css('a::attr(href)').get()
                if link and not link.startswith('http'):
                    link = f"https://www.dubicars.com{link}"
                
                # Details (Year, KM, Location)
                details = card.css('li span::text').getall() + card.css('li::text').getall() + card.css('.detail::text').getall() + card.css('div.text-sm::text').getall()
                details = [d.strip() for d in details if d.strip()]
                
                year = None
                km = None
                location = None
                
                for d in details:
                    if 'km' in d.lower(): km = d
                    elif re.match(r'^(19|20)\d{2}$', d): year = d
                    elif d in ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'Fujairah', 'Ras Al Khaimah', 'Umm Al Quwain']: location = d
                
                if not year:
                    for d in details:
                        if '202' in d or '201' in d or '200' in d or '199' in d: year = d
                
                items_found += 1
                yield {
                    "source": "Dubicars",
                    "title": title.strip() if title else (details[0] if details else None),
                    "price": price.strip() if price else None,
                    "year": year,
                    "mileage": km,
                    "location": location,
                    "link": link
                }
            except Exception as e:
                self.logger.error(f"Error parsing dubicars item: {e}")
        
        current_page = response.meta.get('page_num', 1)
        self.logger.info(f"Page {current_page}: found {items_found} listings")
        
        # Stop if no items found (end of results)
        if items_found == 0:
            self.logger.info("No more listings found. Stopping pagination.")
            return
                
        # Pagination
        if current_page < self.custom_settings["page_limit"]:
            next_page_url = f"https://www.dubicars.com/search?page={current_page + 1}"
            yield Request(next_page_url, sid="stealth", meta={"page_num": current_page + 1})

if __name__ == "__main__":
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n🔄 Attempt {attempt}/{max_retries}...")
            result = DubicarsSpider().start()
            print(f"✅ Scraped {len(result.items)} Dubicars cars")
            result.items.to_json("dubicars_cars.json")
            break
        except Exception as e:
            print(f"❌ Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                wait = 10 * attempt
                print(f"   Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print("❌ All retries exhausted.")
                raise
