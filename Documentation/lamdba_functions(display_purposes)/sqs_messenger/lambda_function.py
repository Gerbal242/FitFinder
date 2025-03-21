"""
Lambda Function: Add URL to Scraping Queue
Created: 2025-03-20
Author: Gerges Ibrahim

This AWS Lambda function handles incoming requests to add a URL to the scraping queue.
It validates the incoming request, stores the task in an RDS database, and sends a message to an SQS queue
for further processing.

Workflow:
    1. Validate that the event contains a body.
    2. Parse the URL from the request body.
    3. Load database configuration from the "fitfinder-config.ini" file.
    4. Establish a connection to the RDS database.
    5. Insert a new scraping task into the database and retrieve the task ID.
    6. Send a message to the SQS queue with the task ID and URL.
    7. Return a success response with the task ID.

Responses:
    - 200: URL added to the queue successfully.
    - 400: Missing request body.
    - 500: Internal server error.

Dependencies:
    - datatier: For database operations.
    - api_utils: For standardized API responses.
    - boto3: For interacting with AWS SQS.
"""

import json
import os
from configparser import ConfigParser

import boto3
import datatier
import api_utils


def lambda_handler(event, context):
    """
    AWS Lambda handler for adding a URL to the scraping queue.

    Args:
        event (dict): The event data passed to the Lambda function. Expected to contain:
            - "body" (str): A JSON string containing the request payload with the following key:
                - "url" (str): The URL to be added to the scraping queue.
        context: AWS Lambda context runtime information (not used).

    Returns:
        dict: Response object with "statusCode" and "body" fields indicating success or failure.
    """
    try:
        # Ensure the request body is present
        if "body" not in event:
            return api_utils.error(400, "No body in request")

        # Parse the request body from JSON
        body = json.loads(event["body"])
        url = body["url"]

        # Set up AWS credentials using the configuration file
        config_file = "fitfinder-config.ini"
        os.environ["AWS_SHARED_CREDENTIALS_FILE"] = config_file

        # Read configuration for RDS access
        configur = ConfigParser()
        configur.read(config_file)
        rds_endpoint = configur.get("rds", "endpoint")
        rds_portnum = int(configur.get("rds", "port_number"))
        rds_username = configur.get("rds", "user_name")
        rds_pwd = configur.get("rds", "user_pwd")
        rds_dbname = configur.get("rds", "db_name")

        # Open connection to the database
        print("**Opening database connection**")
        db_conn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)

        # Insert the new scraping task into the database
        sql_insert = (
            "INSERT INTO scraping_tasks (task_url, task_status, task_progress) "
            "VALUES (%s, %s, %s);"
        )
        modified = datatier.perform_action(db_conn, sql_insert, [url, "queued", "not available yet"])

        # Retrieve the newly created task ID
        sql_taskid = "SELECT LAST_INSERT_ID();"
        taskid = datatier.retrieve_one_row(db_conn, sql_taskid)[0]

        # Prepare message for SQS queue
        sqs = boto3.client("sqs")
        queue_msg = {
            "taskid": taskid,
            "url": url,
        }

        # Send the message to the SQS queue
        sqs.send_message(
            QueueUrl="https://sqs.us-east-2.amazonaws.com/440744224585/FitFinder-scraping-queue",
            MessageBody=json.dumps(queue_msg),
        )

        # Return success response with the task ID
        return api_utils.success(200, f"URL is in queue with job id {taskid}")

    except Exception as err:
        print("**ERROR**")
        print(str(err))
        return api_utils.error(500, str(err))
