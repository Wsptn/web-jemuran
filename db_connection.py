import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",  # sesuai XAMPP
        database="jemuran_db"
    )
