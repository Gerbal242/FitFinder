"""
ASOS Item Scraper
-----------------
Created: 2025-03-20
Author: Gerges Ibrahim

Description:
    This module contains a helper function to scrape product information from an individual ASOS item page.
    It extracts details such as available sizes, colors, gender, and photo links using BeautifulSoup.
    If any error occurs during scraping, the function logs the error and returns None.
"""

import json
import re
import requests
from bs4 import BeautifulSoup

# Define a common header for ASOS requests
HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    ),
}


def item_scrapper(url):
    """
    Scrapes an ASOS item page to extract product details.

    Args:
        url (str): The URL of the ASOS item page.

    Returns:
        dict or None: A dictionary containing product details:
            - sizes (list): List of available sizes.
            - colors (list): List of available colors.
            - photo_links (list): List of photo URLs.
            - gender (str): The product's gender classification.
        Returns None if an error occurs during scraping.
    """
    try:
        response = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract the JavaScript block containing product configuration
        script_tags = soup.find_all("script", type="text/javascript")
        information = None
        for script_tag in script_tags:
            if "window.asos.pdp.config.product" in script_tag.text:
                information = script_tag.text
                break
        
        # Use regex to extract the JSON configuration from the JavaScript block
        regex = r"window\.asos\.pdp\.config\.product\s*=\s*({.*});"
        matches = re.search(regex, information)
        if not matches:
            raise ValueError("Product configuration not found in the page source.")
        product_info = json.loads(matches.group(1))

        # Initialize the result dictionary
        res = {"sizes": [], "colors": [], "photo_links": []}
        sizes = []
        res["gender"] = product_info.get("gender", "")

        # Extract sizes from product variants
        for variant in product_info.get("variants", []):
            if variant.get("size") and variant["size"] not in sizes:
                res["sizes"].append(variant["size"])
                sizes.append(variant["size"])
            
        # Attempt to extract color information and photo links
        try:
            for product in product_info["facetGroup"]["facets"][0]["products"]:
                if product.get("isInStock"):
                    res["colors"].append(product.get("description", ""))
                    res["photo_links"].append("https://" + product.get("imageUrl", ""))
        except Exception:
            # Fallback extraction if the primary structure fails
            res["colors"].append(product_info["variants"][0].get("colour", ""))
            res["photo_links"].append(product_info.get("images", [{}])[0].get("url", ""))
        
        return res

    except Exception as e:
        print(f"**Error while scraping item data: {str(e)}")
        return None
