"""
Lambda Function: Authentication Service (POST /auth)
Modified: 2025-03-20
Authors:
    - Original: Dilan Nair
    - Modified: Prof. Joe Hummel (Northwestern University)
    - Modified again by: Gerges Ibrahim

Description:
    This AWS Lambda function handles authentication requests. The function supports two
    types of authentication:
        1. Token-based: Validates a provided token, returning the user ID if valid,
           or a 401 status if the token is invalid or expired.
        2. Username/Password-based: Authenticates the user and, if valid, generates and returns
           an access token. An optional "duration" parameter (in minutes) specifies the token's
           validity period (default 30 minutes, maximum 60 minutes).

Responses:
    - 200: Successful authentication; returns either the user ID (for token authentication)
           or a new access token (for username/password authentication).
    - 400: Bad request due to missing or malformed request data.
    - 401: Unauthorized (invalid token, expired token, or incorrect credentials).
    - 500: Internal server error (e.g., database errors).
"""

import json
import os
import datetime
import uuid
from configparser import ConfigParser

import datatier
import auth
import api_utils


def lambda_handler(event, context):
    """
    AWS Lambda handler for authentication requests.

    The function expects an event with a "body" key containing a JSON string with either:
      - A "token" key for token-based authentication, or
      - "username" and "password" keys (optionally "duration") for username/password authentication.

    Args:
        event (dict): The event payload from API Gateway.
        context: AWS Lambda runtime context.

    Returns:
        dict: A response dictionary containing an HTTP status code and a message or token.
    """
    try:
        print("**STARTING AUTHENTICATION LAMBDA**")
        print("**lambda: final_proj_auth**")

        # Set up AWS credentials using the configuration file
        config_file = "fitfinder-config.ini"
        os.environ["AWS_SHARED_CREDENTIALS_FILE"] = config_file

        configur = ConfigParser()
        configur.read(config_file)

        # Configure for RDS access
        rds_endpoint = configur.get("rds", "endpoint")
        rds_portnum = int(configur.get("rds", "port_number"))
        rds_username = configur.get("rds", "user_name")
        rds_pwd = configur.get("rds", "user_pwd")
        rds_dbname = configur.get("rds", "db_name")

        # Open connection to the database
        print("**Opening database connection**")
        dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)

        print("**Accessing request body**")
        # Ensure request body exists
        if "body" not in event:
            return api_utils.error(400, "No body in request")
        body = json.loads(event["body"])

        token = ""
        username = ""
        password = ""

        # Determine authentication mode based on provided keys
        if "token" in body:
            token = body["token"]
        elif "username" in body and "password" in body:
            username = body["username"]
            password = body["password"]
        else:
            return api_utils.error(400, "Missing credentials in body")

        # Token-based authentication
        if token != "":
            print("**Token provided for authentication**")
            print("Token:", token)
            print("**Looking up token in database**")

            sql = "SELECT userid, expiration_utc FROM tokens WHERE token = %s;"
            row = datatier.retrieve_one_row(dbConn, sql, [token])

            if row is None or row == ():
                print("**No such token, returning unauthorized**")
                return api_utils.error(401, "Invalid token")

            userid = row[0]
            expiration_utc = row[1]

            print("Retrieved userid:", userid)
            print("Token expiration (UTC):", expiration_utc)

            # Check if token is still valid
            utc_now = datetime.datetime.utcnow()
            print("Current UTC time:", utc_now)

            if utc_now < expiration_utc:
                print("**Token valid; returning userid**")
                return api_utils.success(200, str(userid))
            else:
                print("**Token expired; returning unauthorized**")
                return api_utils.error(401, "Expired token")

        # Username/Password authentication
        print("**Username/password provided for authentication**")
        print("Username:", username)
        print("Password:", password)

        # Set default duration (in minutes) for token validity
        duration = 30  # Default token duration
        if "duration" in body:
            try:
                requested_duration = int(body["duration"])
            except Exception:
                return api_utils.error(400, "Duration must be an integer")
            if 1 <= requested_duration <= 60:
                duration = requested_duration

        print("Token duration (minutes):", duration)

        print("**Looking up user in database**")
        sql = "SELECT userid, pwd FROM users WHERE username = %s;"
        row = datatier.retrieve_one_row(dbConn, sql, [username])

        if row is None or row == ():
            print("**No such user, returning unauthorized**")
            return api_utils.error(401, "Invalid username")

        userid = row[0]
        pwd = row[1]
        print("Retrieved userid:", userid)
        print("Retrieved password hash:", pwd)

        # Validate password (simple comparison here; consider using a secure hash in production)
        if password != pwd:
            print("**Incorrect password, returning unauthorized**")
            return api_utils.error(401, "Invalid password")

        print("**Password is correct; generating access token**")
        token = str(uuid.uuid4())
        print("Generated token:", token)

        # Calculate token expiration time
        expiration_utc = datetime.datetime.utcnow() + datetime.timedelta(minutes=duration)

        print("**Inserting token into database**")
        sql = "INSERT INTO tokens(token, userid, expiration_utc) VALUES(%s, %s, %s);"
        modified = datatier.perform_action(dbConn, sql, [token, userid, expiration_utc])
        if modified != 1:
            print("**INTERNAL ERROR: Insert into database failed**")
            return api_utils.error(500, "Internal error: Insert failed to modify database")

        print("**Authentication successful; returning token**")
        return api_utils.success(200, token)

    except Exception as err:
        print("**ERROR**")
        print(str(err))
        return api_utils.error(500, str(err))
