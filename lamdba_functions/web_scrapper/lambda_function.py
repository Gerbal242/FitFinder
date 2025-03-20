"""
ASOS Scraping Lambda Function
-----------------------------
This Lambda function scrapes product information from an ASOS catalog URL provided in the SQS event body.
It paginates indefinitely until a repeated product (based on the first product title) is detected.
For each page, the function collects product titles, prices, and links.
If any errors occur during execution, the function logs the error, updates the task status in the database,
and raises an exception to trigger an SQS retry.

Author: Gerges Ibrahim
"""

import json
import os
import requests
from bs4 import BeautifulSoup
import datatier
import FitFinder.lamdba_functions.web_scrapper.asos_item_scraper as asos_item_scraper
from configparser import ConfigParser
import boto3

def lambda_handler(event, context):
    """
    AWS Lambda function to scrape product data from ASOS website using an infinite pagination loop.
    The function is triggered by an SQS event, processes the provided URL, and stores the scraped data
    into an RDS database. It also updates the task status and progress in the database.
    """
    dbConn = None
    taskid = None
    try:
        print("**STARTING ASOS Scraping Lambda with Infinite Pagination Loop**")

        # Step 1: Validate SQS event structure
        if "Records" not in event or len(event["Records"]) == 0:
            raise ValueError("No SQS records in event")
        
        record = event["Records"][0]
        if "body" not in record:
            raise ValueError("No body provided in the SQS record")
        body = json.loads(record["body"])

        taskid = body["taskid"]
        url = body["url"]

        # Step 2: Setup AWS based on config file
        config_file = "fitfinder-config.ini"
        os.environ["AWS_SHARED_CREDENTIALS_FILE"] = config_file

        configur = ConfigParser()
        configur.read(config_file)

        # Step 3: Configure for RDS access
        rds_endpoint = configur.get("rds", "endpoint")
        rds_portnum = int(configur.get("rds", "port_number"))
        rds_username = configur.get("rds", "user_name")
        rds_pwd = configur.get("rds", "user_pwd")
        rds_dbname = configur.get("rds", "db_name")

        # Step 4: Open connection to the database
        print("**Opening connection**")
        dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)

        # Step 5: Update scraping_tasks table: set task_status to 'in progress'
        sql = "UPDATE scraping_tasks SET task_status = 'in progress' WHERE taskid = %s"
        datatier.perform_action(dbConn, sql, [taskid])
        print("Task status updated to in progress")

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
        
        # Step 6: Loop indefinitely until a repeated item is found
        while True:
            params["page"] = str(page)
            print(f"**Scraping page {page}**")
            
            response = requests.get(url, params=params, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Failed to retrieve page {page}, status code: {response.status_code}")
            
            soup = BeautifulSoup(response.text, "html.parser")
            titles = soup.find_all("h2", attrs={"class": "productDescription_sryaw"})
            prices = soup.find_all("p", attrs={"class": "container_s8SSI"})
            links = [link["href"] for link in soup.find_all("a", attrs={"class": "productLink_KM4PI"})]
            
            # Step 6.1: Check for repetition
            if page > 1 and titles and pages.get(1) and pages[1].get(0):
                if titles[0].text == pages[1][0]["title"]:
                    print("**Reached end of catalog**")
                    print(f"**Catalog was {page - 1} pages long**")
                    break
            
            # Step 6.2: Store the scraped data for the current page
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
        
        # Step 7: Process each scraped item
        for page in range(1, len(pages) + 1):
            print("Page:", page)
            for item in range(len(pages[page])):
                print("Item", item_num, "of", count)
                item_num += 1

                # Step 7.1: Update progress every 10 items
                if item_num % 10 == 0:
                    sql = "UPDATE scraping_tasks SET task_progress = %s WHERE taskid = %s"
                    datatier.perform_action(dbConn, sql, [f"{item_num}/{count}", taskid])
                    print("Task progress updated to", item_num, "/", count)

                print("Task progress updated to", item_num, "/", count)
                item_info = asos_item_scraper.item_scrapper(pages[page][item]["link"])
                if item_info:
                    name = pages[page][item]["title"]
                    price = pages[page][item]["price"]
                    gender = item_info["gender"]
                    sizes = item_info["sizes"]
                    colors = item_info["colors"]
                    photo_links = item_info["photo_links"]

                    # Step 7.2: Check for duplicates before inserting
                    sql = "SELECT COUNT(*) FROM items WHERE item_name = %s;"
                    existing_item_count = datatier.retrieve_one_row(dbConn, sql, [name])[0]
                    if existing_item_count > 0:
                        print(f"**Item '{name}' already exists. Skipping insertion.")
                        continue  # Skip this item if it's already in the database
                    
                    # Step 7.3: Attempt to insert; catch duplicate errors if they occur
                    try:
                        sql = "INSERT into items(item_name, price, item_gender) values(%s, %s, %s);"
                        modified = datatier.perform_action(dbConn, sql, [name, price, gender])
                    except Exception as err:
                        if "Duplicate entry" in str(err):
                            print(f"**Item '{name}' already exists (caught duplicate error). Skipping insertion.")
                            continue  # Skip this duplicate
                        else:
                            raise err

                    if modified != 1:
                        continue
                    
                    # Step 7.4: Insert sizes and colors
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
                if item_num > 300:
                    break
            if item_num > 300:
                break

        # Step 8: Mark task as completed
        print("**ASOS Scraping Lambda completed successfully**")
        sql = "UPDATE scraping_tasks SET task_status = 'completed', task_progress = %s WHERE taskid = %s"
        datatier.perform_action(dbConn, sql, [f"{item_num}/{count}", taskid])
        
        # Return a success message (optional for SQS-triggered Lambdas)
        return {"status": "completed", "processed_items": item_num}
    
    except Exception as err:
        # Step 9: Handle errors and update task status to 'failed'
        print("**ERROR in ASOS Scraping Lambda**")
        print(str(err))
        try:
            if dbConn and taskid:
                sql = "UPDATE scraping_tasks SET task_status = 'failed' WHERE taskid = %s"
                datatier.perform_action(dbConn, sql, [taskid])
        except Exception as update_err:
            print("Error updating task status to failed:", update_err)
        raise err
