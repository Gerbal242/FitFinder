"""
Lambda Function: Retrieve Task Details
Created: 2025-03-20
Author: Gerges Ibrahim

Description:
    This AWS Lambda function handles HTTP requests for retrieving task details from an RDS database.
    It extracts the 'task_id' from the query string parameters, establishes a connection to the database,
    retrieves the task details, and returns the results in the response.

Workflow:
    1. Extract and validate the 'task_id' query parameter.
    2. Load AWS credentials and database configuration from the "fitfinder-config.ini" file.
    3. Establish a connection to the RDS database.
    4. Execute a SQL query to retrieve task details based on the provided 'task_id'.
    5. Return the task details if found or an error message if not found.
    6. Handle and log any exceptions that occur during execution.

Responses:
    - 200: Successfully retrieved task details.
    - 400: Missing required parameters.
    - 404: Task not found.
    - 500: Internal server error.
"""

import json
import os
from configparser import ConfigParser

import datatier
import api_utils


def lambda_handler(event, context):
    """
    AWS Lambda handler for retrieving task details from the RDS database.

    Args:
        event (dict): The event data passed to the Lambda function, expected to contain:
            - queryStringParameters (dict): A dictionary of query string parameters including:
                - task_id (str): The ID of the task to retrieve.
        context: AWS Lambda context runtime information (not used).

    Returns:
        dict: Response object with "statusCode" and "body" containing the task details or an error message.
    """
    try:
        # Retrieve query parameters from the event
        query_params = event.get("queryStringParameters") or {}
        task_id_param = query_params.get("task_id")

        # Validate the presence of the 'task_id' parameter
        if task_id_param is None:
            return api_utils.error(400, "Missing 'task_id' parameter")

        # Set up AWS credentials using the configuration file
        config_file = "fitfinder-config.ini"
        os.environ["AWS_SHARED_CREDENTIALS_FILE"] = config_file

        # Parse the configuration file for RDS access
        configur = ConfigParser()
        configur.read(config_file)

        rds_endpoint = configur.get("rds", "endpoint")
        rds_portnum = int(configur.get("rds", "port_number"))
        rds_username = configur.get("rds", "user_name")
        rds_pwd = configur.get("rds", "user_pwd")
        rds_dbname = configur.get("rds", "db_name")

        # Open connection to the RDS database
        print("**Opening database connection**")
        db_conn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)

        # SQL query to retrieve task details based on task_id
        sql = "SELECT * FROM scraping_tasks WHERE taskid = %s;"
        row = datatier.retrieve_one_row(db_conn, sql, [int(task_id_param)])

        # Validate that the task exists
        if row is None:
            return api_utils.error(404, "Task not found")

        # Unpack the task details
        task_details = {
            "task_id": row[0],
            "task_url": row[1],
            "task_status": row[2],
            "task_progress": row[3]
        }

        # Return the task details in a successful response
        return api_utils.success(200, task_details)

    except Exception as err:
        print("**ERROR**")
        print(str(err))
        return api_utils.error(500, str(err))
