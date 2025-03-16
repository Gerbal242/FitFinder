#
# Client-side python app for FitFinder app, which is calling
# a set of lambda functions in AWS through API Gateway.
# The overall purpose of the app is to display a unique catalog
# of items to a user providing them with a unique shopping experience.
# Authentication is required in order to customize each catalog for the user.
#
# Author:
#   Gerges Ibrahim

import requests
import jsons

import uuid
import pathlib
import logging
import sys
import os
import base64
import time

import configparser
from getpass import getpass


############################################################
#
# classes
#
class User:

    def __init__(self, row):
        self.userid = row[0]
        self.username = row[1]
        self.pwd = row[2]
        self.top_size = row[3]
        self.pants_wait = row[4]
        self.shoe_size = row[5]
        self.gender = row[6]


###################################################################
#
# web_service_get
#
# When calling servers on a network, calls can randomly fail.
# The better approach is to repeat at least N times (typically
# N=3), and then give up after N tries.
#
def web_service_get(url):
    """
    Submits a GET request to a web service at most 3 times, since
    web services can fail to respond e.g. to heavy user or internet
    traffic. If the web service responds with status code 200, 400
    or 500, we consider this a valid response and return the response.
    Otherwise we try again, at most 3 times. After 3 attempts the
    function returns with the last response.

    Parameters
    ----------
    url: url for calling the web service

    Returns
    -------
    response received from web service
    """

    try:
        retries = 0

        while True:
            response = requests.get(url)

            if response.status_code in [200, 400, 480, 481, 482, 500]:
                #
                # we consider this a successful call and response
                #
                break

            #
            # failed, try again?
            #
            retries = retries + 1
            if retries < 3:
                # try at most 3 times
                time.sleep(retries)
                continue

            #
            # if get here, we tried 3 times, we give up:
            #
            break

        return response

    except Exception as e:
        print("**ERROR**")
        logging.error("web_service_get() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return None


###################################################################
#
# web_service_post
#
def web_service_post(url, data):
    """
    Submits a POST request to a web service at most 3 times, since
    web services can fail to respond e.g. to heavy user or internet
    traffic. If the web service responds with status code 200, 400
    or 500, we consider this a valid response and return the response.
    Otherwise we try again, at most 3 times. After 3 attempts the
    function returns with the last response.

    Parameters
    ----------
    url: url for calling the web service
    data: data to be sent in the POST request

    Returns
    -------
    response received from web service
    """

    try:
        retries = 0

        while True:
            response = requests.post(url, json=data)

            if response.status_code in [200, 400, 480, 481, 482, 500]:
                #
                # we consider this a successful call and response
                #
                break

            #
            # failed, try again?
            #
            retries = retries + 1
            if retries < 3:
                # try at most 3 times
                time.sleep(retries)
                continue

            #
            # if get here, we tried 3 times, we give up:
            #
            break

        return response

    except Exception as e:
        print("**ERROR**")
        logging.error("web_service_post() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return None


############################################################
#
# prompt
#
def prompt():
    """
    Prompts the user and returns the command number

    Parameters
    ----------
    None

    Returns
    -------
    Command number entered by user (0, 1, 2, ...)
    """
    try:
        print()
        print(">> Enter a command:")
        print("     0 => End Service")
        print("     1 => Log In")
        print("     2 => Make An Account")
        print("     3 => View Catalog")
        print("     4 => Log Out")

        cmd = input()

        if cmd == "":  # If the input is empty
            cmd = -1
        elif not cmd.isnumeric():  # is the input is not a number
            cmd = -1
        else:
            cmd = int(cmd)

        return cmd

    except Exception as e:
        print("**ERROR")
        print("**ERROR: invalid input")
        print("**ERROR")
        return -1


############################################################
#
# login
#
def login(baseurl):
    """
    Prompts the user for a username and password, then attempts to
    log them in. If successful, returns the token returned by authentication
    service; Otherwise returns None.

    Parameters
    ----------
    baseurl: url for web service

    Returns
    -------
    token if successful, None if not
    """
    try:
        # promt the user for username, password
        username = input("username: ")
        password = getpass("password: ")
        duration = input("# of minutes before expiration? [ENTER for default] ")

        #
        # build message:
        #
        if duration == "":  # use default
            data = {"username": username, "password": password}
        else:
            data = {"username": username, "password": password, "duration": duration}

        api = "/auth"
        auth_url = baseurl + api

        res = web_service_post(auth_url, data)

        #
        # clear password variable:
        #
        password = None

        #
        # let's look at what we got back:
        #
        if res.status_code == 401:
            #
            # authentication failed:
            #
            body = res.json()
            print(body)
            return None

        if res.status_code == 200:  # success
            pass
        elif res.status_code in [400, 500]:
            # we'll have an error message
            body = res.json()
            print("**Error:", body)
            return
        else:
            # failed:
            print("**ERROR: Failed with status code:", res.status_code)
            print("url: " + baseurl)
            return

        #
        # success, extract token:
        #
        body = res.json()

        token = body

        print("logged in, token:", token)
        return token

    except Exception as e:
        logging.error("**ERROR: login() failed:")
        logging.error("url: " + baseurl)
        logging.error(e)
        return None


############################################################
#
# make_acc
#
def make_acc(baseurl):
    """
    Prompts the user for all information neccesary to make an account.
    If successful, an account is made and use can now log in with username
    and pwd they just provided. If not an error is returned saying one or more of
    the information provided does not satisfy a requirement.

    Parameters
    ----------
    baseurl: url for web service

    Returns
    -------
    token if successful, None if not
    """
    try:
        # promt the user for a lot of stuff
        username = input("username: ")
        password = getpass("password: ")
        top_size = input("shirt size (choose from XXS, X, S, M, L, XL, XXL, 3XL): ")
        pants_waist = input("pants waist from 24 to 50: ")
        pants_length = input("pants length from 26 to 40: ")
        shoe_size = input("shoe size from 6 to 15 (half sizes acceptable): ")
        gender = input("gender M, F, or Other: ")

        # build a message & call lambda function
        data = {
            "username": username,
            "password": password,
            "top_size": top_size,
            "pants_waist": pants_waist,
            "pants_length": pants_length,
            "shoe_size": shoe_size,
            "gender": gender,
        }

        api = "/make"
        auth_url = baseurl + api

        res = web_service_post(auth_url, data)

        #
        # let's look at what we got back:
        #
        if res.status_code == 401:
            #
            # authentication failed:
            #
            body = res.json()
            print(body)
            return None

        if res.status_code == 200:  # success
            print("Account successfully made")
            return
        elif res.status_code in [400, 500]:
            # we'll have an error message
            body = res.json()
            print("**Error:", body)
            return
        else:
            # failed:
            print("**ERROR: Failed with status code:", res.status_code)
            print("url: " + baseurl)
            return

    except Exception as e:
        logging.error("**ERROR: make_acc() failed:")
        logging.error("url: " + baseurl)
        logging.error(e)
        return


def main():
    try:
        print("** Welcome to FitFinder **")
        print("** To begin, Please log in or create an account **")
        print()

        # eliminate traceback so we just get error message:
        sys.tracebacklimit = 0

        # read the config file to extract the webservice url
        fitfinder_file = "fitfinder-config.ini"
        config = configparser.ConfigParser()
        config.read(fitfinder_file)
        baseurl = config.get("client", "webservice")
        print(baseurl)

        #
        # initalize login token:
        #
        token = None

        #
        # main processing loop
        #
        cmd = prompt()

        while cmd != 0:
            if cmd == 1:
                token = login(baseurl)
            elif cmd == 2:
                make_acc(baseurl)
            elif cmd == 3:
                pass
            elif cmd == 4:
                token = None
            else:
                print("** Unknown command, try again...")

            cmd = prompt()

        #
        # Ending service
        #
        print()
        print("** Goodbye and Thank you **")
        sys.exit(0)

    except Exception as e:
        logging.error("**ERROR: main() failed:")
        logging.error(e)
        sys.exit(0)


main()
