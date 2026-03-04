from scrapling.parser import Selector

with open('dubizzle.html', 'r', encoding='utf-8') as f:
    page = Selector(f.read())

prices = page.css('[data-testid="listing-price"]')

if prices:
    for i in range(2):
        container = prices[i].parent.parent.parent.parent
        
        # Test title
        title1 = container.css('[data-testid="listing-title"]::text').get()
        title2 = container.css('h2::text').get()
        title3 = container.css('[data-testid="heading"]::text').get()
        title4 = container.css('[data-testid="listing-heading"]::text').get()
        
        print(f"Item {i+1}:")
        print(f"title1: {title1}")
        print(f"title2: {title2}")
        print(f"title3: {title3}")
        print(f"title4: {title4}")
        print("All text:", container.text)
        print("---")
