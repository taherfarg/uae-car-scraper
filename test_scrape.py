"""Test Dubicars card parsing in detail."""
import json
import html as htmlmod
import re
from scrapling import StealthyFetcher

f = StealthyFetcher()
r = f.fetch("https://www.dubicars.com/uae/new", headless=True)

cards = r.css("li.serp-list-item")
print(f"Total cards: {len(cards)}")

card = cards[0]

# Get data-sp-item
sp_raw = card.attrib.get("data-sp-item", "")
print(f"\ndata-sp-item raw type: {type(sp_raw)}")
print(f"data-sp-item raw length: {len(sp_raw)}")

# Try to parse it
try:
    sp_data = json.loads(sp_raw)
    print(f"Parsed OK! Price (pr): {sp_data.get('pr')}, Year (y): {sp_data.get('y')}")
    print(f"Keys: {list(sp_data.keys())}")
except Exception as e:
    print(f"JSON parse failed: {e}")
    # Try unescaping
    unescaped = htmlmod.unescape(sp_raw)
    sp_data = json.loads(unescaped)
    print(f"After unescape - Price: {sp_data.get('pr')}")

# Get strong elements (price)
strongs = card.css("strong")
for s in strongs:
    txt = s.text
    print(f"\nstrong.text type: {type(txt)}, value: '{txt}'")
    # Clean price
    cleaned = re.sub(r'[^\d.]', '', str(txt))
    print(f"  cleaned: {cleaned}")

# Get links
links = card.css("a")
for a in (links or [])[:3]:
    href = a.attrib.get("href", "")
    cls = a.attrib.get("class", "")
    print(f"\nlink: class='{cls}', href='{href[:80]}'")

# Get spans
spans = card.css("span")
for s in (spans or []):
    txt = str(s.text).strip()
    if txt and len(txt) > 1 and len(txt) < 50:
        print(f"span: '{txt}'")

# Try get_all_text
print(f"\ncard.get_all_text: '{card.get_all_text()[:200]}'")
