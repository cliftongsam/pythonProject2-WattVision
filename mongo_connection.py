from pymongo import MongoClient
import os


def get_database(db_name=None):
    # Read the MongoDB connection URI and default database name from environment variables
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb+srv://root:root@root.lvaibtw.mongodb.net/')
    default_db_name = os.environ.get('DEFAULT_DB_NAME', 'Tetouan_PC')

    # Use the MongoClient with the connection URI
    client = MongoClient(mongodb_uri)

    # If db_name is provided, use it; otherwise, use the default database name
    db_name = db_name if db_name else default_db_name
    db = client[db_name]
    return db
