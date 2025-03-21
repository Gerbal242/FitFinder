"""
Lambda Function: Create User (POST /make)
Created: 2025-03-20
Author: Gerges Ibrahim

This Lambda function creates a new user in the database. The function expects a JSON payload with the following keys:
    - username: string (e.g., "username1")
    - password: string (e.g., "password1")
    - top_size: string (one of: "XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL")
    - pants_waist: integer (e.g., 32, within 24 to 50)
    - pants_length: integer (e.g., 32, within 26 to 40)
    - shoe_size: float (e.g., 10 or 10.5, within 6.0 to 15.0, must be a valid half-size)
    - gender: string (one of: "M", "F", "Other")

Responses:
    - 200: User created successfully.
    - 400: Request is missing parameters or contains invalid values.
    - 500: Internal server error (e.g., database connection issues).

"""

import json
import os
from configparser import ConfigParser

import datatier
import api_utils


def lambda_handler(event, context):
    """
    AWS Lambda handler for creating a new user.

    Parameters:
        event (dict): Event payload containing the HTTP request data.
                      Expected to have a 'body' key with a JSON string.
        context: AWS Lambda context runtime information.

    Returns:
        dict: Response object containing a status code and message.
    """
    try:
        # Check if the request body exists
        if "body" not in event:
            return api_utils.error(400, "No body in request")

        # Parse the request body from JSON
        body = json.loads(event["body"])

        # Validation constants
        VALID_TOP_SIZES = {'XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL'}
        VALID_GENDERS = {'M', 'F', 'Other'}
        MIN_PANTS_WAIST, MAX_PANTS_WAIST = 24, 50
        MIN_PANTS_LENGTH, MAX_PANTS_LENGTH = 26, 40
        MIN_SHOE_SIZE, MAX_SHOE_SIZE = 6.0, 15.0

        REQUIRED_FIELDS = {"username", "password", "top_size", "pants_waist", "pants_length", "shoe_size", "gender"}

        # Ensure all required parameters are present
        missing_fields = REQUIRED_FIELDS - body.keys()
        if missing_fields:
            return api_utils.error(400, f"Missing parameters: {', '.join(missing_fields)}")

        # Validate top size
        if body["top_size"] not in VALID_TOP_SIZES:
            return api_utils.error(400, f"Invalid top size: {body['top_size']}")

        # Validate numeric fields (pants waist, pants length, and shoe size)
        try:
            pants_waist = int(body["pants_waist"])
            pants_length = int(body["pants_length"])
            shoe_size = float(body["shoe_size"])
        except ValueError:
            return api_utils.error(400, "One or more numeric fields are not valid numbers")

        # Range checks for numeric values
        if not (MIN_PANTS_WAIST <= pants_waist <= MAX_PANTS_WAIST):
            return api_utils.error(400, f"Invalid pants waist: {pants_waist}")
        if not (MIN_PANTS_LENGTH <= pants_length <= MAX_PANTS_LENGTH):
            return api_utils.error(400, f"Invalid pants length: {pants_length}")
        # Validate shoe size and ensure it's in half sizes
        if not (MIN_SHOE_SIZE <= shoe_size <= MAX_SHOE_SIZE and shoe_size * 2 == round(shoe_size * 2)):
            return api_utils.error(400, f"Invalid shoe size: {shoe_size}")

        # Validate gender
        if body["gender"] not in VALID_GENDERS:
            return api_utils.error(400, f"Invalid gender: {body['gender']}")

        # Assign validated input values to variables
        username = body["username"]
        password = body["password"]
        top_size = body["top_size"]
        gender = body["gender"]

        # Configure AWS credentials from config file
        config_file = "fitfinder-config.ini"
        os.environ["AWS_SHARED_CREDENTIALS_FILE"] = config_file

        configur = ConfigParser()
        configur.read(config_file)

        # Retrieve RDS configuration
        rds_endpoint = configur.get("rds", "endpoint")
        rds_portnum = int(configur.get("rds", "port_number"))
        rds_username = configur.get("rds", "user_name")
        rds_pwd = configur.get("rds", "user_pwd")
        rds_dbname = configur.get("rds", "db_name")

        # Open connection to the database
        print("Opening connection to the database...")
        db_conn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)

        # SQL query to insert a new user record
        sql = (
            "INSERT INTO users(username, pwd, top_size, pants_waist, pants_length, shoe_size, gender) "
            "VALUES(%s, %s, %s, %s, %s, %s, %s)"
        )

        modified = datatier.perform_action(
            db_conn,
            sql,
            [username, password, top_size, pants_waist, pants_length, shoe_size, gender]
        )
        print("Database rows modified:", modified)

        if modified != 1:
            print("Internal error: Database insert operation failed.")
            return api_utils.error(500, "Internal error: Insert failed to modify database")

        print("User created successfully.")
        return api_utils.success(200, "User created successfully")
        
    except Exception as err:
        print("Error occurred:", str(err))
        if "Duplicate" in str(err):
            return api_utils.error(400, "Username already exists")
        return api_utils.error(500, str(err))
