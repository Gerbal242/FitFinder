#
# api_utils.py
#
# Supplies utility functions for API Gateway Lambda functions.
#
# Original author:
#   Dilan Nair
#   Northwestern University
#

import json

def success(status_code, body):
  """
  Creates a success response.

  Parameters
  ----------
  status_code : int
    The status code to return.
  body : dict
    The body to return.

  Returns
  -------
  dict
    'status_code'
    'body' contains the body
  """

  if status_code < 200 or status_code >= 300:
    raise ValueError("Only success status codes should be used (2XX).")

  return {
    'statusCode': status_code,
    'body': json.dumps(body)
  }

def error(status_code, message):
  """
  Creates an error response.

  Parameters
  ----------
  status_code : int
    The status code to return.
  message : str
    The message to return.

  Returns
  -------
  dict
    'status_code'
    'body' contains the error message
  """

  if status_code < 400 or status_code >= 600:
    raise ValueError("Only error status codes should be used (4XX or 5XX).")
  
  print("**ERROR**")
  print(message)

  return {
    'statusCode': status_code,
    'body': json.dumps(message)
  }
