import json
import datatier
import api_utils
import os
from configparser import ConfigParser
import boto3


def lambda_handler(event, context):
    try:
        # Ensure URL is provided in the event body
        if "body" not in event:
            return api_utils.error(400, "no body in request")

        body = json.loads(event["body"])
        url = body["url"]

        # open a connection to the db
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

        sql = "INSERT INTO scraping_tasks (task_url, task_status, task_progress) VALUES (%s, %s, %s);"

        modified = datatier.perform_action(dbConn, sql, [url, "queued", "not available yet"])

        # obtain the job id
        sql = "SELECT LAST_INSERT_ID();"
        taskid = datatier.retrieve_one_row(dbConn, sql)[0]

        sqs = boto3.client("sqs")
        
        queue_msg = {
            "taskid": taskid,
            "url": url,
        }

        # send the message
        sqs.send_message(
            QueueUrl="https://sqs.us-east-2.amazonaws.com/440744224585/FitFinder-scraping-queue",
            MessageBody=json.dumps(queue_msg),
        )


        return api_utils.success(200, f"URL is in queue with job id {taskid}")

    except Exception as err:
        print("**ERROR**")
        print(str(err))
        
        return api_utils.error(500, str(err))
