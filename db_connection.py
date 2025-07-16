import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="sql5.freesqldatabase.com",
        user="sql5790368",
        password="9DlS5uFqig",
        database="sql5790368",
        port=3306
    )
