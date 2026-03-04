import asyncio
import time
from scrapling.spiders import Spider, Request, Response
from scrapling.fetchers import AsyncStealthySession

class DubizzleSpider(Spider):
    name = "dubizzle_cars"
    start_urls = ["https://dubai.dubizzle.com/motors/used-cars/"]
    concurrent_requests = 1
    
    custom_settings = {
        "page_limit": 2000
    }

    def configure_sessions(self, manager):
        manager.add("stealth", AsyncStealthySession(
            headless=True,
            solve_cloudflare=True,
            timeout=60000,
        ))

    async def parse(self, response: Response):
        prices = response.css('[data-testid="listing-price"]')
        
        for price_elem in prices:
            try:
                container = price_elem.parent.parent.parent.parent
                
                title = container.css('h2::text').get()
                price = container.css('[data-testid="listing-price"]::text').get()
                year = container.css('[data-testid="listing-year"]::text').get()
                
                km = container.css('[data-testid="listing-kms"]::text').get()
                if not km: km = container.css('[data-testid="listing-km"]::text').get()
                if not km: km = container.css('[data-testid="listing-mileage"]::text').get()
                
                location = container.css('[data-testid="listing-location"]::text').get()
                
                link = container.css('a::attr(href)').get()
                if not link and container.parent: 
                    link = container.parent.css('a::attr(href)').get()
                
                if link and not link.startswith('http'):
                    link = f"https://dubai.dubizzle.com{link}"
                    
                yield {
                    "source": "Dubizzle",
                    "title": title.strip() if title else None,
                    "price": price.strip() if price else None,
                    "year": year.strip() if year else None,
                    "mileage": km.strip() if km else None,
                    "location": location.strip() if location else None,
                    "link": link
                }
            except Exception as e:
                self.logger.error(f"Error parsing item: {e}")
        
        items_found = len(prices)
        self.logger.info(f"Page {response.meta.get('page_num', 1)}: found {items_found} listings")
        
        # Stop pagination if no items found (end of results)
        if items_found == 0:
            self.logger.info("No more listings found. Stopping pagination.")
            return
        
        # Pagination
        current_page = response.meta.get('page_num', 1)
        if current_page < self.custom_settings["page_limit"]:
            next_page_link = response.xpath('//a[contains(text(), "Next") or contains(@aria-label, "Next page")]/@href').get()
            if not next_page_link:
                next_page_url = f"https://dubai.dubizzle.com/motors/used-cars/?page={current_page + 1}"
            else:
                next_page_url = next_page_link if next_page_link.startswith('http') else f"https://dubai.dubizzle.com{next_page_link}"
            
            yield Request(next_page_url, sid="stealth", meta={"page_num": current_page + 1})


if __name__ == "__main__":
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n🔄 Attempt {attempt}/{max_retries}...")
            spider = DubizzleSpider()
            result = spider.start()
            print(f"✅ Scraped {len(result.items)} Dubizzle cars")
            result.items.to_json("dubizzle_cars.json")
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
