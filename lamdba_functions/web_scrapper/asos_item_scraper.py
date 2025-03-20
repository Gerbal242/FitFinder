"""
ASOS Item scraping
-----------------------------
This script is a web scraper designed to extract product information from ASOS item pages.
It retrieves details such as available sizes, colors, gender, and photo links for a given product.
The script uses BeautifulSoup for HTML parsing, requests for HTTP requests, and regex for extracting
specific JavaScript variables embedded in the page source.

Author: Gerges Ibrahim
"""


import requests
import json
import re
from bs4 import BeautifulSoup

headers = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
}

def item_scrapper(url):
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        script_tags = soup.find_all("script", type="text/javascript")
        
        for script_tag in script_tags:
            if "window.asos.pdp.config.product" in script_tag.text:
                information = script_tag.text
                break
        
        regex = r"window.asos.pdp.config.product = ({.*});"
        matches = re.search(regex, information)
        product_info = json.loads(matches.group(1))

        res = {"sizes": [], "colors": [], "photo_links": []}
        sizes = []
        colors = []
        photo_links = []
        res['gender'] = product_info['gender']

        for variant in product_info['variants']:
            res['sizes'].append(variant['size']) if variant['size'] not in sizes else None
            
        try:
            for product in product_info['facetGroup']['facets'][0]['products']:
                if product['isInStock']:
                    res['colors'].append(product['description'])
                    res['photo_links'].append("https://"+product['imageUrl'])
        except:
            res['colors'].append(product_info['variants'][0]['colour'])
            res['photo_links'].append(product_info['images'][0]['url'])

        return res
    except Exception as e:
        print(f"**Error while scraping item data: {str(e)}")
        return None
