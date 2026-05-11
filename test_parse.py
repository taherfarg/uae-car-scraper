from bs4 import BeautifulSoup

html = open('dubicars_detail_test.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')

# Find dealer
for img in soup.select('img'):
    if 'logo' in str(img.get('class', '')) or 'dealer' in str(img.get('class', '')):
        print('Dealer img:', img.get('alt'))
        
for a in soup.select('a'):
    if 'dealer' in str(a.get('href', '')):
        print('Dealer a:', a.text.strip())
        
for meta in soup.select('meta'):
    print(meta.get('property'), meta.get('content'))
