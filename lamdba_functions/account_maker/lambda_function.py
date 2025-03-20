#
# POST /make
#
# Lambda function to create an user. The caller need to pass 
# a username, pwd, and a variety of sizes as can be seen below 
# Valid message formats:
#
# {
#   "username": "username1",
#   "password": "password1",
#   "top_size": "L",
#   "pants_waist": "32",
#   "pants_length": "32",
#   "shoe_size": "10"
# }
#
# If all the information passed is valid and acceptable by
# our database rules, status code 200 is returned to the client.
# If information passed is not in acceptable format, 400 is returned.
#
# If the function is called incorrectly, a status code of 400
# is returned, and the body of the message contains an error
# message. Server-side programming errors are returned with a
# status code of 500, with the body containing the error msg.
#
#
# Author: Gerges Ibrahim
#

import json
import os
import datetime
import uuid
import datatier
import api_utils

from configparser import ConfigParser

def lambda_handler(event, context):
    try:
        # parse the information obtained in the context and attempt to upload to sql, if failure, then return why
        if "body" not in event:
            return api_utils.error(400, "no body in request")

        body = json.loads(event["body"])

        VALID_TOP_SIZES = {'XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL'}
        VALID_GENDERS = {'M', 'F', 'Other'}
        MIN_PANTS_WAIST, MAX_PANTS_WAIST = 24, 50
        MIN_PANTS_LENGTH, MAX_PANTS_LENGTH = 26, 40
        MIN_SHOE_SIZE, MAX_SHOE_SIZE = 6.0, 15.0  # Shoe size is a float

        REQUIRED_FIELDS = {"username", "password", "top_size", "pants_waist", "pants_length", "shoe_size", "gender"}

        # Ensure all required parameters are present
        missing_fields = REQUIRED_FIELDS - body.keys()
        if missing_fields:
            return api_utils.error(400, f"Missing parameters: {', '.join(missing_fields)}")

        # Validate top_size
        if body["top_size"] not in VALID_TOP_SIZES:
            return api_utils.error(400, f"Invalid top size: {body['top_size']}")

        # Validate numeric fields
        try:
            pants_waist = int(body["pants_waist"])
            pants_length = int(body["pants_length"])
            shoe_size = float(body["shoe_size"])
        except ValueError:
            return api_utils.error(400, "One or more numeric fields are not valid numbers")

        # Range checks
        if not (MIN_PANTS_WAIST <= pants_waist <= MAX_PANTS_WAIST):
            return api_utils.error(400, f"Invalid pants waist: {pants_waist}")
        if not (MIN_PANTS_LENGTH <= pants_length <= MAX_PANTS_LENGTH):
            return api_utils.error(400, f"Invalid pants length: {pants_length}")
        if not (MIN_SHOE_SIZE <= shoe_size <= MAX_SHOE_SIZE and shoe_size * 2 == round(shoe_size * 2)):
            return api_utils.error(400, f"Invalid shoe size: {shoe_size}")

        # Validate gender
        if body["gender"] not in VALID_GENDERS:
            return api_utils.error(400, f"Invalid gender: {body['gender']}")


        # 1) obtain the information
        username = body['username']
        pwd = body['password']
        top_size = body['top_size']
        pants_waist = int(body['pants_waist'])
        pants_length = int(body['pants_length'])
        shoe_size = float(body['shoe_size'])
        gender = body['gender']

        #
        # setup AWS based on config file
        #
        config_file = "fitfinder-config.ini"
        os.environ["AWS_SHARED_CREDENTIALS_FILE"] = config_file

        configur = ConfigParser()
        configur.read(config_file)

        #
        # configure for RDS access
        #
        rds_endpoint = configur.get("rds", "endpoint")
        rds_portnum = int(configur.get("rds", "port_number"))
        rds_username = configur.get("rds", "user_name")
        rds_pwd = configur.get("rds", "user_pwd")
        rds_dbname = configur.get("rds", "db_name")

        #
        # open connection to the database
        #
        print("**Opening connection**")
        dbConn = datatier.get_dbConn(
            rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname
        )

        # create the sql that we will be using to input all these items
        sql = "INSERT into users(username, pwd, top_size, pants_waist, pants_length, shoe_size, gender) values(%s, %s, %s, %s, %s, %s, %s)"
        
        modified = datatier.perform_action(dbConn, sql, [username, pwd, top_size, pants_waist, pants_length, shoe_size, gender])

        print("printing motified: ", modified)
        if modified != 1:
            print("**INTERNAL ERROR: insert into database failed...**")
            return api_utils.error(
                500, "INTERNAL ERROR: insert failed to modify database"
            )

        #
        # success, done!
        #
        print("**DONE, succesfully created user**")

        return api_utils.success(200, "user created successfully")
        
    except Exception as err:
        print("**ERROR**")
        print(str(err))

        if "Duplicate" in str(err):
            return api_utils.error(400, "username already exists")

        
        return api_utils.error(500, str(err))


