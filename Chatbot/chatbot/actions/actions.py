import mysql.connector

def get_db_connection():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="Product"
        )
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        return None

