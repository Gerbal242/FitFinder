"""
FitFinder Client Application
Created: 2025-03-20
Author: Gerges Ibrahim

Description:
    This is a client application for the FitFinder web service. It serves as a command-line
    interface for interacting with several AWS Lambda functions via API Gateway. The primary
    functionalities include:
        - User Authentication (log in or create an account)
        - Catalog Viewing (customized shopping catalog)
        - Web Scraping (developer tool for scraping catalogs)
        - Task Polling (check the status of web scraping tasks)

    Notes on Project Progress:
        - The authorization step allows users to create accounts and sign in. When creating an account,
          the following user information is collected:
            1. Username
            2. Password (Note: Consider using a hash function for secure storage in the future)
            3. Sizes:
                a. Top size (Valid values: XXS, XS, S, M, L, XL, XXL, 3XL)
                b. Pants waist (Valid range: 24-50)
                c. Pants length (Valid range: 26-40)
                d. Shoe size (Valid range: 6-15, half sizes accepted)
            4. Gender they are shopping for (Valid values: M, F, Other)
        
        - The database (users) has been created and configured along with the necessary read/write
          user access. The next steps include connecting a client file to call the Lambda functions.
        
        - The authorization Lambda has been refurbished from previous work. Future work includes
          creating a "make account" feature that validates inputs using the helper function (validate_user_input).
        
        - Web scraping functionality is being integrated. While multiple approaches exist (e.g., Puppeteer,
          Scrapeos API, BeautifulSoup), the initial implementation uses BeautifulSoup for its simplicity and
          cost-effectiveness.
        
        - The catalog database design includes tables for items, sizes, colors, and photos. These tables
          support connecting items with their variants.
        
        - The client also implements a polling mechanism to check the status of scraping tasks.

Usage:
    Run this script from the command line. It will prompt you for commands:
        0 => End Service
        1 => Log In
        2 => Make An Account
        3 => View Catalog
        4 => Log Out
        5 => Web Scrape (Developer tool)
        6 => Poll Tasks
"""

import requests
import json
import uuid
import pathlib
import logging
import sys
import os
import base64
import time
import pprint
import configparser
from getpass import getpass

# Constants for user validation (used in the helper function for account creation)
VALID_TOP_SIZES = {'XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL'}
VALID_GENDERS = {'M', 'F', 'Other'}
MIN_PANTS_WAIST, MAX_PANTS_WAIST = 24, 50
MIN_PANTS_LENGTH, MAX_PANTS_LENGTH = 26, 40
MIN_SHOE_SIZE, MAX_SHOE_SIZE = 4.0, 14.0  # Shoe size is a float
REQUIRED_FIELDS = {"username", "password", "top_size", "pants_waist", "pants_length", "shoe_size", "gender"}


def validate_user_input(body):
    """
    Validates the user input for creating an account.

    Ensures all required fields are present and checks that numeric fields are within allowed ranges.

    Parameters
    ----------
    body : dict
        Dictionary containing user input.

    Returns
    -------
    None if valid; otherwise, a response dictionary from api_utils.error indicating the error.
    """
    missing_fields = REQUIRED_FIELDS - body.keys()
    if missing_fields:
        return {"statusCode": 400, "body": f"Missing parameters: {', '.join(missing_fields)}"}

    if body["top_size"] not in VALID_TOP_SIZES:
        return {"statusCode": 400, "body": f"Invalid top size: {body['top_size']}"}

    try:
        pants_waist = int(body["pants_waist"])
        pants_length = int(body["pants_length"])
        shoe_size = float(body["shoe_size"])
    except ValueError:
        return {"statusCode": 400, "body": "One or more numeric fields are not valid numbers"}

    if not (MIN_PANTS_WAIST <= pants_waist <= MAX_PANTS_WAIST):
        return {"statusCode": 400, "body": f"Invalid pants waist: {pants_waist}"}
    if not (MIN_PANTS_LENGTH <= pants_length <= MAX_PANTS_LENGTH):
        return {"statusCode": 400, "body": f"Invalid pants length: {pants_length}"}
    if not (MIN_SHOE_SIZE <= shoe_size <= MAX_SHOE_SIZE and shoe_size * 2 == round(shoe_size * 2)):
        return {"statusCode": 400, "body": f"Invalid shoe size: {shoe_size}"}

    if body["gender"] not in VALID_GENDERS:
        return {"statusCode": 400, "body": f"Invalid gender: {body['gender']}"}

    return None  # No errors


###################################################################
# Web Service Utilities
###################################################################
def web_service_get(url):
    """
    Submits a GET request to a web service, retrying up to 3 times.

    Parameters
    ----------
    url : str
        The URL of the web service.

    Returns
    -------
    response : requests.Response
        The response from the web service.
    """
    try:
        retries = 0
        while True:
            response = requests.get(url)
            if response.status_code in [200, 400, 480, 481, 482, 500]:
                break
            retries += 1
            if retries < 3:
                time.sleep(retries)
                continue
            break
        return response
    except Exception as e:
        logging.error("web_service_get() failed for url: %s", url)
        logging.error(e)
        return None


def web_service_post(url, data):
    """
    Submits a POST request to a web service, retrying up to 3 times.

    Parameters
    ----------
    url : str
        The URL of the web service.
    data : dict
        The data to be sent in the POST request.

    Returns
    -------
    response : requests.Response
        The response from the web service.
    """
    try:
        retries = 0
        while True:
            response = requests.post(url, json=data)
            if response.status_code in [200, 400, 480, 481, 482, 500]:
                break
            retries += 1
            if retries < 3:
                time.sleep(retries)
                continue
            break
        return response
    except Exception as e:
        logging.error("web_service_post() failed for url: %s", url)
        logging.error(e)
        return None


###################################################################
# User Class
###################################################################
class User:
    """
    Represents a user retrieved from the database.
    """
    def __init__(self, row):
        self.userid = row[0]
        self.username = row[1]
        self.pwd = row[2]
        self.top_size = row[3]
        self.pants_wait = row[4]
        self.shoe_size = row[5]
        self.gender = row[6]


###################################################################
# Client Functions
###################################################################
def prompt():
    """
    Displays a command prompt and returns the user's command as an integer.

    Returns
    -------
    int
        The command number entered by the user.
    """
    try:
        print("\n>> Enter a command:")
        print("     0 => End Service")
        print("     1 => Log In")
        print("     2 => Make An Account")
        print("     3 => View Catalog")
        print("     4 => Log Out")
        print("     5 => Web Scrape")
        print("     6 => Poll Tasks")
        cmd = input()
        if not cmd.isnumeric():
            return -1
        return int(cmd)
    except Exception as e:
        logging.error("prompt() failed: %s", e)
        return -1


def login(baseurl):
    """
    Prompts the user for a username and password, then attempts to log them in.

    Parameters
    ----------
    baseurl : str
        The base URL for the web service.

    Returns
    -------
    token : str or None
        The authentication token if login is successful; None otherwise.
    """
    try:
        username = input("username: ")
        password = getpass("password: ")
        duration = input("# of minutes before expiration? [ENTER for default] ")
        if duration == "":
            data = {"username": username, "password": password}
        else:
            data = {"username": username, "password": password, "duration": duration}
        api_url = baseurl + "/auth"
        res = web_service_post(api_url, data)
        password = None  # clear sensitive data

        if res.status_code == 401:
            print(res.json())
            return None
        elif res.status_code in [400, 500]:
            print("**Error:", res.json())
            return None
        elif res.status_code != 200:
            print("**ERROR: Failed with status code:", res.status_code)
            return None

        token = res.json()
        print("Logged in, token:", token)
        return token
    except Exception as e:
        logging.error("login() failed: %s", e)
        return None


def make_acc(baseurl):
    """
    Prompts the user for account creation details and creates a new account.

    Parameters
    ----------
    baseurl : str
        The base URL for the web service.
    """
    try:
        username = input("username: ")
        password = getpass("password: ")
        top_size = input("shirt size (choose from XXS, XS, S, M, L, XL, XXL, 3XL): ")
        pants_waist = input("pants waist (24-50): ")
        pants_length = input("pants length (26-40): ")
        shoe_size = input("shoe size (6-15, half sizes accepted): ")
        gender = input("gender (M, F, or Other): ")

        data = {
            "username": username,
            "password": password,
            "top_size": top_size,
            "pants_waist": pants_waist,
            "pants_length": pants_length,
            "shoe_size": shoe_size,
            "gender": gender,
        }

        # Optionally, validate input before sending:
        err = validate_user_input(data)
        if err is not None:
            print(err["body"])
            return

        api_url = baseurl + "/make"
        res = web_service_post(api_url, data)
        if res.status_code == 401:
            print(res.json())
            return
        elif res.status_code in [400, 500]:
            print("**Error:", res.json())
            return
        elif res.status_code == 200:
            print("Account successfully created")
        else:
            print("**ERROR: Failed with status code:", res.status_code)
            return
    except Exception as e:
        logging.error("make_acc() failed: %s", e)
        return


def web_scrape(baseurl):
    """
    Prompts the user for a catalog URL to scrape and queues the URL via a Lambda function.

    Parameters
    ----------
    baseurl : str
        The base URL for the web service.
    """
    try:
        page_to_scrape = input("URL desired to scrape: ")
        data = {"url": page_to_scrape}
        api_url = baseurl + "/scrape"
        print("**Queuing URL to be scraped**")
        res = web_service_post(api_url, data)
        if res.status_code == 401:
            print(res.json())
            return
        elif res.status_code in [400, 500]:
            print("**Error:", res.json())
            return
        elif res.status_code == 200:
            print("Information successfully added to catalog")
            print(res.json())
        else:
            print("**ERROR: Failed with status code:", res.status_code)
            return
    except Exception as e:
        logging.error("web_scrape() failed: %s", e)
        return


def poll_tasks(baseurl):
    """
    Polls the server for a task matching the input task ID and displays its status and progress.
    
    Parameters
    ----------
    baseurl : str
        The base URL for the web service.
    """
    try:
        task_id = input("Enter the task id you would like to poll: ")
        api_url = baseurl + "/poll?task_id=" + task_id
        res = web_service_get(api_url)
        if res.status_code == 401:
            print(res.json())
            return
        elif res.status_code == 200:
            body = res.json()
            print("Task status:", body.get("task_status"))
            print("Task progress:", body.get("task_progress"))
        elif res.status_code in [400, 500]:
            print("**Error:", res.json())
            return
        else:
            print("**ERROR: Failed with status code:", res.status_code)
            return
    except Exception as e:
        logging.error("poll_tasks() failed: %s", e)
        return


def view_catalog(baseurl, token):
    """
    Retrieves and displays a customized catalog for the logged-in user.

    Parameters
    ----------
    baseurl : str
        The base URL for the web service.
    token : str
        The authentication token of the logged-in user.
    """
    try:
        include_tops_input = input("Include tops in catalog? (y/n): ")
        include_shoes_input = input("Include shoes in catalog? (y/n): ")
        include_pants_input = input("Include pants in catalog? (y/n): ")

        if token is None:
            print("You must be logged in to view the catalog")
            return

        # Authenticate the user using the token
        api_url = baseurl + "/auth"
        res = web_service_post(api_url, {"token": token})
        if res.status_code == 401:
            print(res.json())
            return
        elif res.status_code in [400, 500]:
            print("**Error:", res.json())
            return
        elif res.status_code != 200:
            print("**ERROR: Failed with status code:", res.status_code)
            return

        page = 0
        while True:
            token_param = "token=" + token
            page_param = "page=" + str(page)
            tops_flag = "1" if include_tops_input.lower() == "y" else "0"
            shoes_flag = "1" if include_shoes_input.lower() == "y" else "0"
            pants_flag = "1" if include_pants_input.lower() == "y" else "0"
            query_string = "?" + "&".join([token_param, page_param,
                                            "includeTops=" + tops_flag,
                                            "includeShoes=" + shoes_flag,
                                            "includePants=" + pants_flag])
            api_url = baseurl + "/view" + query_string
            res = web_service_get(api_url)

            if res.status_code == 401:
                print(res.json())
                return
            elif res.status_code in [400, 500]:
                print("**Error:", res.json())
                return
            elif res.status_code == 204:
                print("No more items to display. Please upload more items via the web scraper.")
                return
            elif res.status_code != 200:
                print("**ERROR: Failed with status code:", res.status_code)
                return

            body = res.json()
            print("Page:", page + 1)
            print("Catalog:")
            for i, item in enumerate(body, start=1):
                print("Item #:", i)
                pprint.pp(item)

            if input("View the next page? (y/n): ").lower() != "y":
                break
            page += 1
    except Exception as e:
        logging.error("view_catalog() failed: %s", e)
        return


###################################################################
# Main Application Loop
###################################################################
def main():
    """
    Main function for the FitFinder client application.
    
    Reads configuration, displays a command prompt, and executes commands until the user chooses to exit.
    """
    try:
        print("** Welcome to FitFinder **")
        print("** Please log in or create an account to begin **\n")
        sys.tracebacklimit = 0

        # Read the client configuration file for the web service URL
        fitfinder_file = "fitfinder-client-config.ini"
        config = configparser.ConfigParser()
        config.read(fitfinder_file)
        baseurl = config.get("client", "webservice")

        token = None  # Initialize the login token

        # Main processing loop
        cmd = prompt()
        while cmd != 0:
            if cmd == 1:
                token = login(baseurl)
            elif cmd == 2:
                make_acc(baseurl)
            elif cmd == 3:
                view_catalog(baseurl, token)
            elif cmd == 4:
                token = None
                print("Logged out successfully.")
            elif cmd == 5:
                web_scrape(baseurl)
            elif cmd == 6:
                poll_tasks(baseurl)
            else:
                print("** Unknown command, please try again...")
            cmd = prompt()

        print("\n** Goodbye and Thank you **")
        sys.exit(0)

    except Exception as e:
        logging.error("main() failed: %s", e)
        sys.exit(0)


if __name__ == "__main__":
    main()
