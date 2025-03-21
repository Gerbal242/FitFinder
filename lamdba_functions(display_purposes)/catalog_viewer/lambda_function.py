"""
Lambda Function: Catalog Viewer (GET /catalog)
Created: 2025-03-20
Author: Gerges Ibrahim

This AWS Lambda function handles catalog viewing requests. It authenticates the user via an external API,
retrieves the user's preferences from the database, and returns a list of items that match the user's criteria.

Functionality:
    1. Parse and validate the event.
    2. Extract query parameters (token, page, includeTops, includeShoes, includePants).
    3. Authenticate the user via an external API.
    4. Load AWS credentials and RDS configuration from a configuration file.
    5. Establish a database connection.
    6. Execute a SQL query to fetch items based on user preferences.
    7. Return the results or appropriate error responses.

Responses:
    - 200: Successful retrieval of catalog items.
    - 204: No items found.
    - 400: Bad request due to missing or invalid parameters.
    - 500: Internal server or configuration errors.

Dependencies:
    - datatier: For database connections and query execution.
    - api_utils: For standardized API response formatting.
    - web_service_calls: For external API calls.
    - requests, logging, json, os, ConfigParser: Standard Python libraries.
"""

import json
import os
import logging
from configparser import ConfigParser

import datatier
import api_utils
import requests
import web_service_calls


def lambda_handler(event, context):
    """
    AWS Lambda handler for processing catalog viewing requests.

    Parameters:
        event (dict or str): The event payload containing HTTP request data. It may be a JSON string or a dictionary.
        context: AWS Lambda context object providing runtime information.

    Returns:
        dict: A response object with a status code and a message or data.
    """
    try:
        # Log the incoming event for debugging
        logging.debug("Received event: %s", event)

        # Parse the event if provided as a JSON string
        if isinstance(event, str):
            try:
                event = json.loads(event)
            except Exception as parse_err:
                logging.error("Failed to parse event: %s", parse_err)
                return api_utils.error(400, "Invalid JSON event format")

        # Ensure event is a dictionary after parsing
        if not isinstance(event, dict):
            logging.error("Event is not a dictionary after parsing: %s", event)
            return api_utils.error(400, "Invalid event format")

        # Extract query parameters from the event
        params = event.get("queryStringParameters") or {}
        logging.debug("Query parameters: %s", params)

        # Retrieve individual query parameters with defaults
        token = params.get("token")
        page = int(params.get("page", 0))
        include_tops = int(params.get("includeTops", 0))
        include_shoes = int(params.get("includeShoes", 0))
        include_pants = int(params.get("includePants", 0))

        # Authenticate the user via an external API call
        base_url = "https://ni8y2g00r3.execute-api.us-east-2.amazonaws.com/prod"
        auth_api = "/auth"
        api_url = base_url + auth_api

        data = {"token": token}
        res = web_service_calls.web_service_post(api_url, data)

        # Handle authentication errors or unexpected responses
        if res is None:
            return api_utils.error(500, "Authentication service error")
        if res.status_code == 401:
            body = res.json()
            return api_utils.error(401, body.get("message", "Unauthorized"))

        # Process successful authentication response
        if res.status_code == 200:
            auth_resp = res.json()
            userid = auth_resp.get("userid") if isinstance(auth_resp, dict) else auth_resp
        elif res.status_code in [400, 500]:
            body = res.json()
            return api_utils.error(res.status_code, body.get("message", "Error"))
        else:
            return api_utils.error(res.status_code, "Unknown error")

        # Load AWS credentials from configuration file
        config_file = "fitfinder-config.ini"
        if not os.path.exists(config_file):
            return api_utils.error(500, "Configuration file missing")
        os.environ["AWS_SHARED_CREDENTIALS_FILE"] = config_file

        # Parse the configuration file for RDS connection details
        configur = ConfigParser()
        configur.read(config_file)

        rds_endpoint = configur.get("rds", "endpoint")
        rds_portnum = int(configur.get("rds", "port_number"))
        rds_username = configur.get("rds", "user_name")
        rds_pwd = configur.get("rds", "user_pwd")
        rds_dbname = configur.get("rds", "db_name")

        # Establish a database connection
        db_conn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)
        if db_conn is None:
            return api_utils.error(500, "Database connection failed")

        # Define SQL query to fetch items based on user preferences and query parameters
        sql = """
        SELECT DISTINCT
            i.item_name,
            i.price,
            s.size,
            c.color,
            c.photo_url
        FROM items AS i
        JOIN sizes AS s
            ON i.itemid = s.itemid
        JOIN users AS u
            ON u.userid = %s
        JOIN colors AS c
            ON i.itemid = c.itemid
        WHERE
            (
                (%s = 1 AND TRIM(s.size) = TRIM(u.top_size))
                OR
                (%s = 1 AND s.size COLLATE utf8mb4_unicode_ci LIKE CONCAT('%%', CAST(u.shoe_size AS CHAR) COLLATE utf8mb4_unicode_ci, '%%'))
                OR
                (%s = 1 AND s.size COLLATE utf8mb4_unicode_ci LIKE CONCAT('%%W', u.pants_waist, ' L', u.pants_length, '%%') COLLATE utf8mb4_unicode_ci)
            )
            AND
            (
                i.item_gender = 'Unisex'
                OR (i.item_gender = 'Men'   AND u.gender = 'M')
                OR (i.item_gender = 'Women' AND u.gender = 'F')
            )
        LIMIT %s OFFSET %s;
        """
        limit = 20  # Number of items per page
        offset = page * limit  # Calculate offset based on the current page

        # Execute the SQL query and retrieve matching items
        items = datatier.retrieve_all_rows(
            db_conn,
            sql,
            [userid, include_tops, include_shoes, include_pants, limit, offset]
        )
        if items is None:
            return api_utils.success(204, "No items found")

        # Return the retrieved items as a successful response
        return api_utils.success(200, items)

    except Exception as err:
        # Log and handle any unexpected exceptions
        logging.error("Unhandled exception: %s", err)
        return api_utils.error(500, str(err))
