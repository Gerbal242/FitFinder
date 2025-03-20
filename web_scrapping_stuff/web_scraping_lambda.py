"""
ASOS Scraping Lambda Function
-----------------------------
This Lambda function scrapes product information from an ASOS catalog URL provided in the event body.
It paginates indefinitely until a repeated product (based on the first product title) is detected.
For each page, the function collects product titles, prices, and links.
If any errors occur during execution, the function logs the error and returns an HTTP 500 response.

Author: Gerges Ibrahim
"""

import json
import os
import requests
from bs4 import BeautifulSoup
import datatier
import api_utils
import asos_item_scraper


def lambda_handler(event, context):
    try:
        print("**STARTING ASOS Scraping Lambda with Infinite Pagination Loop**")

        # Ensure URL is provided in the event body
        if "body" not in event:
            return api_utils.error(400, "No URL provided in the event body")
        body = event["body"]
        url = body["url"]

        # Open connection to the database
        print("**Opening connection**")
        dbConn = datatier.get_dbConn()  # Use the connection details from environment variables

        headers = {
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/134.0.0.0 Safari/537.36"
            ),
        }

        pages = {}
        params = {"page": "1"}
        page = 1
        count = 0
        
        # Loop indefinitely until a repeated item is found
        while True:
            params["page"] = str(page)
            print(f"**Scraping page {page}**")
            
            response = requests.get(url, params=params, headers=headers)
            if response.status_code != 200:
                return api_utils.error(response.status_code, f"Failed to retrieve page {page}")
            
            soup = BeautifulSoup(response.text, "html.parser")
            titles = soup.find_all("h2", attrs={"class": "productDescription_sryaw"})
            prices = soup.find_all("p", attrs={"class": "container_s8SSI"})
            links = [link["href"] for link in soup.find_all("a", attrs={"class": "productLink_KM4PI"})]
            
            # Check for repetition: if the first title in the current page matches the first title from page 1, break.
            if page > 1 and titles and pages.get(1) and pages[1].get(0):
                if titles[0].text == pages[1][0]["title"]:
                    print("**Reached end of catalog")
                    print(f"**Catalog was {page - 1} pages long")
                    break
            
            # Store the scraped data for the current page
            pages[page] = {}
            for item_num in range(len(titles)):
                pages[page][item_num] = {
                    "title": titles[item_num].text,
                    "price": prices[item_num].text if item_num < len(prices) else "",
                    "link": links[item_num] if item_num < len(links) else "",
                }
                count += 1
            
            page += 1
        
        item_num = 0
        print("**Scraping item information**")
        
        for page in range(1, len(pages) + 1):
            print("Page: ", page)
            for item in range(len(pages[page])):
                print("Item ", item_num, " of ", count)
                item_num += 1
                item_info = asos_item_scraper.item_scrapper(pages[page][item]["link"])
                if item_info:
                    name = pages[page][item]["title"]
                    price = pages[page][item]["price"]
                    gender = item_info["gender"]
                    sizes = item_info["sizes"]
                    colors = item_info["colors"]
                    photo_links = item_info["photo_links"]

                    # Check for duplicates before inserting
                    sql = "SELECT COUNT(*) FROM items WHERE item_name = %s;"
                    existing_item_count = datatier.retrieve_one_row(dbConn, sql, [name])[0]

                    if existing_item_count > 0:
                        print(f"**Item '{name}' already exists. Skipping insertion.")
                        continue  # Skip this item if it's already in the database
                    
                    sql = "INSERT into items(item_name, price, item_gender) values(%s, %s, %s);"
                    modified = datatier.perform_action(dbConn, sql, [name, price, gender])

                    if modified != 1:
                        continue
                    
                    sql = "SELECT LAST_INSERT_ID();"
                    row = datatier.retrieve_one_row(dbConn, sql)
                    item_id = row[0]

                    sql = "INSERT into sizes(itemid, size) values(%s, %s);"
                    for size in sizes:
                        datatier.perform_action(dbConn, sql, [item_id, size])

                    sql = "INSERT into colors(itemid, color, photo_url) values(%s, %s, %s);"
                    for i in range(len(colors)):
                        color = colors[i]
                        photo_url = photo_links[i]
                        datatier.perform_action(dbConn, sql, [item_id, color, photo_url])


        print("**ASOS Scraping Lambda completed successfully**")
        
        return api_utils.success(200, "URL successfully scraped")
    
    except Exception as err:
        print("**ERROR in ASOS Scraping Lambda**")
        print(str(err))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(err)})
        }
