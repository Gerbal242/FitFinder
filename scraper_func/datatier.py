import pymysql
import os

# Initialize the database connection once, and reuse it in subsequent Lambda invocations
# This helps to optimize connection times and minimize overhead when Lambda reuses a container

def get_dbConn():
    """
    Opens and returns a connection object for interacting with a
    MySQL database using environment variables for credentials.
    """
    try:
        # Using environment variables for secure handling of credentials
        dbConn = pymysql.connect(
            host=os.environ["RDS_ENDPOINT"],
            port=int(os.environ["RDS_PORT"]),
            user=os.environ["RDS_USER"],
            passwd=os.environ["RDS_PASSWORD"],
            database=os.environ["RDS_DBNAME"],
            connect_timeout=5  # Timeout set for fast failure in case of network issues
        )
        return dbConn
    except Exception as err:
        print("datatier.get_dbConn() failed:")
        print(str(err))
        raise


def retrieve_one_row(dbConn, sql, parameters=[]):
    """
    Executes an sql SELECT query and returns the first row as a tuple.
    If no row is found, returns an empty tuple.
    """
    with dbConn.cursor() as dbCursor:
        try:
            dbCursor.execute(sql, parameters)
            row = dbCursor.fetchone()
            return row if row else ()
        except Exception as err:
            print("datatier.retrieve_one_row() failed:")
            print(str(err))
            raise


def retrieve_all_rows(dbConn, sql, parameters=[]):
    """
    Executes an sql SELECT query and returns all rows as a list of tuples.
    Returns an empty list if no rows are found.
    """
    with dbConn.cursor() as dbCursor:
        try:
            dbCursor.execute(sql, parameters)
            rows = dbCursor.fetchall()
            return rows if rows else []
        except Exception as err:
            print("datatier.retrieve_all_rows() failed:")
            print(str(err))
            raise


def perform_action(dbConn, sql, parameters=[]):
    """
    Executes an sql ACTION query (insert, update, delete) and returns
    the number of rows affected.
    """
    with dbConn.cursor() as dbCursor:
        try:
            dbCursor.execute(sql, parameters)
            dbConn.commit()
            return dbCursor.rowcount  # Return the number of rows affected
        except Exception as err:
            dbConn.rollback()  # Rollback any changes in case of failure
            print("datatier.perform_action() failed:")
            print(str(err))
            raise
