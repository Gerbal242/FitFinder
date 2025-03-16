import datatier
import configparser

# Create a ConfigParser object
config = configparser.ConfigParser()

# Specify the path to the configuration file
config_file_path = "fitfinder-config.ini"

endpoint = None
port_number = None
region_name = None
user_name = None
user_pwd = None
db_name = None
# Read the configuration file
try:
    config.read(config_file_path)

    rds = config.items("rds")
    endpoint = rds[0][1]
    port_number = int(rds[1][1])
    region_name = rds[2][1]
    user_name = rds[3][1]
    user_pwd = rds[4][1]
    db_name = rds[5][1]
except FileNotFoundError:
    print(f"Error: Configuration file not found at {config_file_path}")
except configparser.Error as e:
    print(f"Error parsing configuration file: {e}")


dbconn = datatier.get_dbConn(endpoint, port_number, user_name, user_pwd, db_name)

print(dbconn)
