# db_connection.py
import mysql.connector
import streamlit as st # Import st untuk menampilkan pesan error koneksi

def get_connection():
    """
    Mencoba membuat koneksi ke database MySQL.
    Menampilkan pesan error Streamlit jika koneksi gagal.
    Mengembalikan objek koneksi jika berhasil, None jika gagal.
    """
    try:
        conn = mysql.connector.connect(
            host="sql5.freesqldatabase.com",
            user="sql5790368",
            password="9DlS5uFqig",
            database="sql5790368",
            port=3306 # Menambahkan port sesuai permintaan Anda
        )
        return conn
    except mysql.connector.Error as err:
        st.error(f"Error koneksi ke database: {err}")
        print(f"DEBUG: Error koneksi DB: {err}") # Cetak ke konsol untuk debugging
        return None
    except Exception as e:
        st.error(f"Terjadi kesalahan tak terduga saat koneksi database: {e}")
        print(f"DEBUG: Error tak terduga koneksi DB: {e}") # Cetak ke konsol untuk debugging
        return None