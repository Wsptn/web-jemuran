import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="sql12.freesqldatabase.com",
        user="sql12786635",
        password="jtMnHixJ9S",
        database="sql12786635",
        port=3306
    )
