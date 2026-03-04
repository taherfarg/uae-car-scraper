from scrapling.parser import Selector
import json

with open('dubicars.html', 'r', encoding='utf-8') as f:
    page = Selector(f.read())

cards = page.xpath('//*[contains(@class, "car-card") or contains(@class, "car-box") or contains(@class, "list-item")]')

if cards:
    for i in range(2):
        card = cards[i]
        title = card.css('h2 a::text').get() or card.css('h3 a::text').get() or card.css('a[title]::attr(title)').get() or card.css('h2.title::text').get()
        price_elem = card.xpath('.//*[contains(text(), "AED")]')
        price = price_elem[0].text if price_elem else None
        
        # usually properties like km, year are in 'li'
        props = card.css('li span::text').getall() or card.css('li::text').getall()
        # filter out empty strings
        props = [p.strip() for p in props if p.strip()]
        
        link = card.css('a::attr(href)').get()
        
        print(f"--- Item {i+1} ---")
        print(json.dumps({
            "title": title.strip() if title else None,
            "price": price.strip() if price else None,
            "properties": props,
            "link": link
        }, indent=2))
