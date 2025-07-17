import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from datetime import datetime, time, timedelta
import pytz
from io import BytesIO
from db_connection import get_connection # Pastikan file db_connection.py Anda sudah ada dan benar

# ==================== INIALISASI SESSION STATE UNTUK PESAN ==================== #
# Ini membantu mengelola pesan sukses/error agar tidak duplikat atau muncul di waktu yang salah
if 'message_type' not in st.session_state:
    st.session_state.message_type = None
if 'message_content' not in st.session_state:
    st.session_state.message_content = ""
if 'last_auto_delete_check' not in st.session_state:
    st.session_state.last_auto_delete_check = None
if 'show_delete_warning_this_session' not in st.session_state:
    st.session_state.show_delete_warning_this_session = False
if 'auto_delete_performed_this_session' not in st.session_state:
    st.session_state.auto_delete_performed_this_session = False

# ==================== KONSTANTA PENGHAPUSAN OTOMATIS ==================== #
MAX_DATA_ROWS = 5000 # Batas maksimal total data di data_pelayanan
DELETE_BUFFER = 500  # Jumlah data yang akan dipertahankan setelah penghapusan (misal: 5000 - 500 = 4500)
DELETE_INTERVAL_MONTHS = 3 # Interval penghapusan berdasarkan waktu (3 bulan)
WARNING_DAYS_BEFORE_DELETE = 7 # Notifikasi muncul 7 hari sebelum penghapusan 3 bulanan

# ==================== STYLING ==================== #
st.markdown("""
<style>
/* 1. GLOBAL FONT & BACKGROUND */
html, body, [class*="css"] {
    color: #212529 !important;
    font-family: 'Segoe UI', sans-serif !important;
    background-color: #f5f6fa !important;
}

/* 2. NAVBAR */
.main-title {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 65px;
    background-color: #0d6efd;
    color: white;
    font-size: 22px;
    font-weight: 600;
    display: flex;
    align-items: center;
    padding-left: 25px;
    z-index: 9999;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}

/* 3. SIDEBAR */
section[data-testid="stSidebar"] {
    padding: 0 !important;
    border-right: 1px solid #dee2e6;
    z-index: 100;
}

section[data-testid="stSidebar"] > div:first-child {
    display: flex;
    flex-direction: column;
    height: 100vh;
}

section[data-testid="stSidebar"] > div:first-child > div:nth-child(1) {
    background-color: #0d6efd;
    height: 65px;
}

section[data-testid="stSidebar"] > div:first-child > div:nth-child(2) {
    background-color: white;
    flex-grow: 1;
    padding: 1rem;
    overflow-y: auto;
}

/* 4. TEKS DI SIDEBAR */
section[data-testid="stSidebar"] > div:first-child {
    padding-bottom: 70px !important;
}

/* 5. KONTEN UTAMA */
.block-container {
    background-color: #f5f6fa !important;
    padding-top: 90px !important;
    padding-left: 2rem;
    padding-right: 2rem;
}

/* 6. FORM INPUT, DROPDOWN, TEXTAREA */
input, select, textarea {
    background-color: #ffffff !important;
    color: #212529 !important;
    border: 1px solid #212529 !important;
    border-radius: 5px !important;
}

/* 7. LABEL & TEKS */
label, h1, h2, h3, h4, h5, h6, p, span, div {
    color: #212529 !important;
}

/* 8. TOMBOL */
button[kind="primary"] {
    background-color: #0d6efd !important;
    color: white !important;
    border-radius: 5px !important;
}

/* 9. FOOTER */
.footer {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background-color: #f8f9fa;
    color: #6c757d;
    text-align: center;
    padding: 10px;
    font-size: 14px;
    border-top: 1px solid #dee2e6;
    z-index: 9999;
}

/* 10. RESPONSIVE FIX (Mobile) */
@media screen and (max-width: 768px) {
    .main-title {
        font-size: 18px;
        padding-left: 15px;
    }
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>Sistem Informasi Jemuran Pesantren</div>", unsafe_allow_html=True)

# ==================== KONSTANTA ==================== #
DAERAH_LIST = [
    "Sunan Gunung Jati", "Sunan Kalijaga", "Sunan Kudus", "Sunan Ampel", "Sunan Drajat",
    "Sunan Bonang", "Sunan Giri", "Nawawi Al-Bantani", "Abu Hasan Asy-Syadzili", "Abul Aswad Ad-Dua'ali",
    "Yasin Al-Fadani", "Ibnu Arabi", "Sa'id Al-Makki Al-Manduri", "Raden Fatah", "K.H Zaini Mun'im",
    "Nurus Shobah", "Sunan Muria", "Faza", "Imam Al-Ghazali", "Maulana Malik Ibrahim"
]

# ==================== DATABASE FUNCTIONS ==================== #
def get_data(query, params=None):
    """Mengambil data dari database menggunakan query SQL."""
    conn = get_connection()
    if conn is None: # Pastikan koneksi berhasil
        return pd.DataFrame()
    try:
        df = pd.read_sql(query, conn, params=params)
        return df
    except Exception as e:
        st.error(f"Terjadi kesalahan saat mengambil data: {e}")
        print(f"DEBUG: Error get_data: {e}") # Cetak ke konsol untuk debugging
        return pd.DataFrame() # Return empty DataFrame on error
    finally:
        if conn:
            conn.close()

def update_app_setting(setting_name, setting_value):
    """Memperbarui atau menyisipkan pengaturan aplikasi."""
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        query = """
            INSERT INTO app_settings (setting_name, setting_value)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE setting_value = %s
        """
        cursor.execute(query, (setting_name, setting_value, setting_value))
        conn.commit()
        return True
    except Exception as e:
        print(f"DEBUG: Error updating app setting {setting_name}: {e}")
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_app_setting(setting_name):
    """Mengambil nilai pengaturan aplikasi."""
    conn = get_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        query = "SELECT setting_value FROM app_settings WHERE setting_name = %s"
        cursor.execute(query, (setting_name,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"DEBUG: Error getting app setting {setting_name}: {e}")
        return None
    finally:
        if conn:
            conn.close()

def simpan_data_pelayanan(data):
    """
    Menyimpan data pelayanan baru dan mengurangi stok barang pinjaman.
    Mengembalikan True jika berhasil, False jika nomor kartu sudah dipakai atau error.
    """
    conn = get_connection()
    if conn is None: # Pastikan koneksi berhasil
        return False
    cursor = conn.cursor()
    try:
        # Periksa apakah nomor kartu sudah digunakan dan belum diambil
        cursor.execute("""SELECT * FROM data_pelayanan
            WHERE no_kartu = %s AND ambil = 'Tidak' AND (relokasi IS NULL OR relokasi = '')""", (data[14],))
        if cursor.fetchone():
            print("DEBUG: Nomor kartu sudah dipakai.") # Debug print
            return False # Nomor kartu masih dipakai

        # Kurangi stok_tersedia untuk barang pinjaman
        # data[11] = jepit, data[12] = hanger, data[13] = timba
        cursor.execute("UPDATE stok_pinjaman SET stok_tersedia = stok_tersedia - %s WHERE nama_barang = 'Jepit'", (data[11],))
        cursor.execute("UPDATE stok_pinjaman SET stok_tersedia = stok_tersedia - %s WHERE nama_barang = 'Hanger'", (data[12],))
        cursor.execute("UPDATE stok_pinjaman SET stok_tersedia = stok_tersedia - %s WHERE nama_barang = 'Timba'", (data[13],))

        # Masukkan data pelayanan baru
        query = """
            INSERT INTO data_pelayanan (
                nama_pemilik, daerah, kamar, bulan, tahun, hari_tanggal, waktu,
                baju, sarung, celana, jenis_lainnya,
                jepit, hanger, timba,
                no_kartu, relokasi, ambil
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Tidak')
        """
        cursor.execute(query, data)
        conn.commit()
        print("DEBUG: Data pelayanan berhasil disimpan dan stok diperbarui.") # Debug print
        return True
    except Exception as e:
        print(f"DEBUG: Exception caught in simpan_data_pelayanan: {e}") # Debug print
        conn.rollback() # Batalkan perubahan jika ada error
        return False
    finally:
        if conn:
            conn.close()

def update_status_ambil(id_data, jepit_kembali, hanger_kembali, timba_kembali):
    """
    Memperbarui status pengambilan, mengembalikan stok barang pinjaman,
    dan mencatat kehilangan jika ada selisih.
    """
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        # Ambil jumlah barang pinjaman awal dari record pelayanan
        cursor.execute("SELECT jepit, hanger, timba FROM data_pelayanan WHERE id = %s", (id_data,))
        pinjaman_awal = cursor.fetchone()

        if pinjaman_awal:
            jepit_pinjam = pinjaman_awal[0] if pinjaman_awal[0] is not None else 0
            hanger_pinjam = pinjaman_awal[1] if pinjaman_awal[1] is not None else 0
            timba_pinjam = pinjaman_awal[2] if pinjaman_awal[2] is not None else 0

            # Hitung selisih barang pinjaman yang hilang (jika ada)
            jepit_hilang = max(0, jepit_pinjam - jepit_kembali)
            hanger_hilang = max(0, hanger_pinjam - hanger_kembali)
            timba_hilang = max(0, timba_pinjam - timba_kembali)

            # Tambahkan stok_tersedia dengan barang yang DIKEMBALIKAN
            cursor.execute("UPDATE stok_pinjaman SET stok_tersedia = stok_tersedia + %s WHERE nama_barang = 'Jepit'", (jepit_kembali,))
            cursor.execute("UPDATE stok_pinjaman SET stok_tersedia = stok_tersedia + %s WHERE nama_barang = 'Hanger'", (hanger_kembali,))
            cursor.execute("UPDATE stok_pinjaman SET stok_tersedia = stok_tersedia + %s WHERE nama_barang = 'Timba'", (timba_kembali,))

            # Catat barang yang hilang ke tabel data_kehilangan
            if jepit_hilang > 0:
                cursor.execute("INSERT INTO data_kehilangan (id_pelayanan, jenis_barang, jumlah_hilang, keterangan) VALUES (%s, 'Jepit', %s, 'Tidak dikembalikan')", (id_data, jepit_hilang))
            if hanger_hilang > 0:
                cursor.execute("INSERT INTO data_kehilangan (id_pelayanan, jenis_barang, jumlah_hilang, keterangan) VALUES (%s, 'Hanger', %s, 'Tidak dikembalikan')", (id_data, hanger_hilang))
            if timba_hilang > 0:
                cursor.execute("INSERT INTO data_kehilangan (id_pelayanan, jenis_barang, jumlah_hilang, keterangan) VALUES (%s, 'Timba', %s, 'Tidak dikembalikan')", (id_data, timba_hilang))

            # Perbarui status 'ambil' di data_pelayanan
            cursor.execute("UPDATE data_pelayanan SET ambil = 'Iya' WHERE id = %s", (id_data,))
            conn.commit()
            print("DEBUG: Status ambil berhasil diperbarui.") # Debug print
            return True
        else:
            print("DEBUG: Data pinjaman untuk ID ini tidak ditemukan saat update status ambil.") # Debug print
            return False
    except Exception as e:
        print(f"DEBUG: Exception caught in update_status_ambil: {e}") # Debug print
        st.error(f"Terjadi kesalahan saat memperbarui status atau mencatat kehilangan: {e}")
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def update_relokasi(id_data, isi_relokasi):
    """Memperbarui kolom relokasi di tabel data_pelayanan."""
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE data_pelayanan SET relokasi = %s WHERE id = %s", (isi_relokasi, id_data))
        conn.commit()
        print("DEBUG: Relokasi berhasil diperbarui.") # Debug print
        return True
    except Exception as e:
        print(f"DEBUG: Exception caught in update_relokasi: {e}") # Debug print
        st.error(f"Terjadi kesalahan saat memperbarui relokasi: {e}")
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def simpan_data_kehilangan(id_pelayanan, jenis_barang, jumlah_hilang, keterangan):
    """
    Menyimpan data kehilangan dan mengurangi stok_tersedia jika barang yang hilang adalah barang pinjaman.
    """
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO data_kehilangan (id_pelayanan, jenis_barang, jumlah_hilang, keterangan) VALUES (%s, %s, %s, %s)",
                       (id_pelayanan, jenis_barang, jumlah_hilang, keterangan))
        conn.commit()
        
        # Jika barang yang hilang adalah barang pinjaman, kurangi stok_tersedia
        if jenis_barang in ['Jepit', 'Hanger', 'Timba']:
            cursor.execute("UPDATE stok_pinjaman SET stok_tersedia = stok_tersedia - %s WHERE nama_barang = %s",
                           (jumlah_hilang, jenis_barang))
            conn.commit() # Commit lagi setelah update stok
            print(f"DEBUG: Stok {jenis_barang} dikurangi karena kehilangan.") # Debug print
            
        print("DEBUG: Data kehilangan berhasil disimpan.") # Debug print
        return True
    except Exception as e:
        print(f"DEBUG: Exception caught in simpan_data_kehilangan: {e}") # Debug print
        st.error(f"Terjadi kesalahan saat menyimpan data kehilangan: {e}")
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_data_kehilangan_lengkap():
    """Mengambil semua data kehilangan dengan detail pemilik."""
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    try:
        df = pd.read_sql("""
            SELECT 
                k.id, 
                k.id_pelayanan, 
                p.nama_pemilik, 
                p.no_kartu, 
                k.jenis_barang, 
                k.jumlah_hilang, 
                k.waktu_lapor, 
                k.keterangan
            FROM data_kehilangan k
            LEFT JOIN data_pelayanan p ON k.id_pelayanan = p.id
        """, conn)
        return df
    except Exception as e:
        st.error(f"Terjadi kesalahan saat mengambil data kehilangan: {e}")
        print(f"DEBUG: Error get_data_kehilangan_lengkap: {e}") # Debug print
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def get_ringkasan_kehilangan_barang_pinjaman():
    """Mengambil ringkasan jumlah barang pinjaman yang hilang."""
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    try:
        df = pd.read_sql("""
            SELECT
                jenis_barang as nama_barang,
                SUM(jumlah_hilang) as jumlah_hilang_total
            FROM data_kehilangan
            WHERE jenis_barang IN ('Jepit', 'Hanger', 'Timba')
            GROUP BY jenis_barang
        """, conn)
        return df
    except Exception as e:
        st.error(f"Terjadi kesalahan saat mengambil ringkasan kehilangan: {e}")
        print(f"DEBUG: Error get_ringkasan_kehilangan_barang_pinjaman: {e}") # Debug print
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def tambah_stok_barang(nama_barang, jumlah_tambah):
    """
    Menambahkan stok barang ke tabel stok_pinjaman.
    Ini akan menambah `jumlah_total` dan `stok_tersedia`.
    """
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE stok_pinjaman SET jumlah_total = jumlah_total + %s, stok_tersedia = stok_tersedia + %s WHERE nama_barang = %s",
                       (jumlah_tambah, jumlah_tambah, nama_barang))
        conn.commit()
        print(f"DEBUG: Stok {nama_barang} berhasil ditambah.") # Debug print
        return True
    except Exception as e:
        print(f"DEBUG: Exception caught in tambah_stok_barang: {e}") # Debug print
        st.error(f"Terjadi kesalahan saat menambah stok: {e}")
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def export_excel(df, filename):
    """Mengekspor DataFrame ke file Excel dengan ringkasan statistik."""
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')

    # Sheet 1: Tabel Data
    df.to_excel(writer, sheet_name="Tabel Data", index=False)

    workbook = writer.book
    sheet = workbook.add_worksheet("Ringkasan")
    writer.sheets["Ringkasan"] = sheet

    # 1. Total Pengguna
    total_pengguna = df["nama_pemilik"].nunique()
    sheet.write("A1", "Total Pengguna")
    sheet.write("B1", total_pengguna)

    # 2. Jenis Pakaian
    pakaian = df[["baju", "sarung", "celana", "jenis_lainnya"]].sum() # Changed 'kopyah' to 'jenis_lainnya'
    sheet.write("A3", "Jenis Pakaian")
    for i, (item, jumlah) in enumerate(pakaian.items()):
        sheet.write(i + 4, 0, item)
        sheet.write(i + 4, 1, jumlah)

    # 3. Pinjaman Barang
    pinjaman = df[["jepit", "hanger", "timba"]].sum()
    sheet.write("D3", "Pinjaman Barang")
    for i, (item, jumlah) in enumerate(pinjaman.items()):
        sheet.write(i + 4, 3, item)
        sheet.write(i + 4, 4, jumlah)

    # 4. Status Ambil
    ambil = df["ambil"].value_counts()
    sheet.write("G3", "Status Ambil")
    for i, (item, jumlah) in enumerate(ambil.items()):
        sheet.write(i + 4, 6, item)
        sheet.write(i + 4, 7, jumlah)

    # 5. Shift
    shift = df["waktu"].value_counts()
    sheet.write("I3", "Shift")
    for i, (item, jumlah) in enumerate(shift.items()):
        sheet.write(i + 4, 8, item)
        sheet.write(i + 4, 9, jumlah)

    # 6. Per Daerah
    daerah = df["daerah"].value_counts()
    sheet.write("K3", "Layanan per Daerah")
    for i, (item, jumlah) in enumerate(daerah.items()):
        sheet.write(i + 4, 10, item)
        sheet.write(i + 4, 11, jumlah)

    writer.close()
    st.download_button(
        "📥 Export Excel ",
        data=output.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def perform_auto_deletion(trigger_type):
    """
    Melakukan penghapusan data otomatis berdasarkan pemicu.
    Hanya menghapus data dengan status 'Iya' (sudah diambil).
    """
    conn = get_connection()
    if conn is None:
        return False, "Koneksi database gagal."
    cursor = conn.cursor()
    
    deleted_count = 0
    try:
        if trigger_type == 'count_based':
            # Ambil ID data yang sudah diambil ('Iya'), diurutkan dari yang terlama
            cursor.execute("SELECT id FROM data_pelayanan WHERE ambil = 'Iya' ORDER BY hari_tanggal ASC")
            ids_to_delete = [row[0] for row in cursor.fetchall()]
            
            current_total_data = get_data("SELECT COUNT(*) FROM data_pelayanan").iloc[0,0]

            if current_total_data >= MAX_DATA_ROWS:
                # Hitung berapa banyak data yang perlu dihapus untuk mencapai buffer
                # Target: MAX_DATA_ROWS - DELETE_BUFFER
                num_to_delete = current_total_data - (MAX_DATA_ROWS - DELETE_BUFFER)
                
                # Pastikan tidak menghapus lebih dari jumlah data 'Iya' yang tersedia
                num_to_delete = min(num_to_delete, len(ids_to_delete))

                if num_to_delete > 0:
                    # Ambil ID dari data 'Iya' terlama
                    ids_to_delete_final = tuple(ids_to_delete[:num_to_delete])
                    
                    # Hapus data dari data_pelayanan
                    delete_query = f"DELETE FROM data_pelayanan WHERE id IN ({','.join(['%s'] * len(ids_to_delete_final))})"
                    cursor.execute(delete_query, ids_to_delete_final)
                    deleted_count = cursor.rowcount
                    conn.commit()
                    print(f"DEBUG: Dihapus {deleted_count} data (berdasarkan jumlah) dengan status 'Iya'.")
                    return True, f"{deleted_count} data lama (sudah diambil) berhasil dihapus karena total data melebihi batas {MAX_DATA_ROWS} data."
                else:
                    return False, "Tidak ada data 'sudah diambil' yang perlu dihapus berdasarkan jumlah."

        elif trigger_type == 'time_based':
            # Hapus data yang sudah diambil ('Iya') DAN sudah lebih dari 3 bulan
            tanggal_batas = datetime.now().date() - pd.DateOffset(months=DELETE_INTERVAL_MONTHS)
            
            delete_query = """
                DELETE FROM data_pelayanan
                WHERE ambil = 'Iya' AND hari_tanggal < %s
            """
            cursor.execute(delete_query, (tanggal_batas,))
            deleted_count = cursor.rowcount
            conn.commit()
            print(f"DEBUG: Dihapus {deleted_count} data (berdasarkan waktu) dengan status 'Iya'.")
            return True, f"{deleted_count} data lama (sudah diambil) berhasil dihapus karena sudah lebih dari {DELETE_INTERVAL_MONTHS} bulan."
        
        return False, "Tidak ada pemicu penghapusan yang dikenali."

    except Exception as e:
        print(f"DEBUG: Exception caught in perform_auto_deletion: {e}")
        conn.rollback()
        return False, f"Terjadi kesalahan saat penghapusan otomatis: {e}"
    finally:
        if conn:
            conn.close()

def check_and_trigger_auto_delete():
    """
    Memeriksa kondisi penghapusan otomatis dan memicu penghapusan jika diperlukan.
    Juga menampilkan notifikasi peringatan.
    """
    current_datetime = datetime.now()
    current_date = current_datetime.date()

    # Kontrol agar fungsi ini tidak berjalan setiap kali Streamlit me-rerun
    # Hanya cek sekali per sesi atau jika sudah lewat waktu tertentu (misal: 1 jam)
    if st.session_state.last_auto_delete_check is not None and \
       (current_datetime - st.session_state.last_auto_delete_check).total_seconds() < 3600: # Cek setiap jam
        return

    st.session_state.last_auto_delete_check = current_datetime # Update dengan datetime penuh
    print("DEBUG: Menjalankan pemeriksaan penghapusan otomatis...")

    # --- Ambil pengaturan terakhir dari database ---
    last_auto_delete_run_str = get_app_setting('last_auto_delete_run')
    next_3_month_delete_schedule_str = get_app_setting('next_3_month_delete_schedule')

    last_auto_delete_run = datetime.fromisoformat(last_auto_delete_run_str).date() if last_auto_delete_run_str else None
    next_3_month_delete_schedule = datetime.fromisoformat(next_3_month_delete_schedule_str).date() if next_3_month_delete_schedule_str else None

    # --- Hitung atau perbarui jadwal penghapusan 3 bulanan ---
    # Jika belum ada jadwal atau jadwal sudah lewat, hitung jadwal 3 bulan ke depan
    if next_3_month_delete_schedule is None or next_3_month_delete_schedule <= current_date:
        start_date_for_next_schedule = last_auto_delete_run if last_auto_delete_run else current_date
        # Menghitung tanggal 3 bulan ke depan secara akurat
        # Pastikan hasil pd.DateOffset dikonversi ke date() untuk perbandingan
        next_3_month_schedule_temp = start_date_for_next_schedule + pd.DateOffset(months=DELETE_INTERVAL_MONTHS)
        next_3_month_delete_schedule = next_3_month_schedule_temp.date()
        
        # Pastikan tanggalnya tidak di masa lalu jika aplikasi baru dimulai atau jadwal terlalu jauh di masa lalu
        while next_3_month_delete_schedule <= current_date:
            next_3_month_schedule_temp += pd.DateOffset(months=DELETE_INTERVAL_MONTHS)
            next_3_month_delete_schedule = next_3_month_schedule_temp.date()

        update_app_setting('next_3_month_delete_schedule', next_3_month_delete_schedule.isoformat())
        print(f"DEBUG: Jadwal penghapusan 3 bulanan berikutnya diatur ke: {next_3_month_delete_schedule}")

    # --- Cek notifikasi 7 hari sebelum penghapusan 3 bulanan ---
    days_until_next_delete = (next_3_month_delete_schedule - current_date).days
    if 0 < days_until_next_delete <= WARNING_DAYS_BEFORE_DELETE:
        st.session_state.show_delete_warning_this_session = True
        print(f"DEBUG: Menampilkan peringatan penghapusan dalam {days_until_next_delete} hari.")
    else:
        st.session_state.show_delete_warning_this_session = False

    # --- Cek pemicu penghapusan ---
    total_data_count = get_data("SELECT COUNT(*) FROM data_pelayanan").iloc[0,0]

    trigger_activated = False
    delete_message = ""

    # Pemicu berdasarkan jumlah data
    if total_data_count >= MAX_DATA_ROWS:
        success, msg = perform_auto_deletion('count_based')
        if success:
            trigger_activated = True
            delete_message = msg
            print("DEBUG: Penghapusan berdasarkan jumlah dipicu.")

    # Pemicu berdasarkan waktu (jika belum dipicu oleh jumlah dan jadwal sudah tiba)
    if not trigger_activated and current_date >= next_3_month_delete_schedule:
        success, msg = perform_auto_deletion('time_based')
        if success:
            trigger_activated = True
            delete_message = msg
            print("DEBUG: Penghapusan berdasarkan waktu dipicu.")

    if trigger_activated:
        st.session_state.message_type = "info" # Gunakan info untuk notifikasi otomatis
        st.session_state.message_content = f"Pembersihan data otomatis selesai: {delete_message}"
        st.session_state.auto_delete_performed_this_session = True
        
        # Perbarui last_auto_delete_run dan jadwal berikutnya setelah penghapusan
        update_app_setting('last_auto_delete_run', datetime.now().isoformat())
        # Hitung jadwal 3 bulan ke depan dari tanggal penghapusan baru
        new_next_schedule_temp = datetime.now().date() + pd.DateOffset(months=DELETE_INTERVAL_MONTHS)
        new_next_schedule = new_next_schedule_temp.date()
        update_app_setting('next_3_month_delete_schedule', new_next_schedule.isoformat())
        
        st.rerun() # Refresh untuk menampilkan pesan dan data terbaru

# ==================== MENU: INPUT ==================== #
def menu_data_pelayanan():
    st.title("Input Data Pengguna")
    
    # Gunakan waktu Jakarta
    jakarta_tz = pytz.timezone('Asia/Jakarta')
    now = datetime.now(pytz.utc).astimezone(jakarta_tz)
    
    bulan = now.strftime("%B")
    tahun = now.strftime("%Y")
    hari_tanggal = now.date()
    jam_menit = now.time()
    waktu = "Pagi" if time(6,30) <= jam_menit <= time(11,0) else \
            "Siang" if time(11,0) < jam_menit <= time(16,0) else \
            "Malam" if time(20,0) <= jam_menit or jam_menit <= time(1,0) else \
            "Tidak Tersedia"

    if waktu == "Tidak Tersedia":
        st.warning("Waktu input tidak sesuai shift. Pastikan Anda menginput pada shift yang ditentukan.") 

    nama = st.text_input("Nama Pemilik")
    daerah = st.selectbox("Daerah", DAERAH_LIST)
    kamar = st.text_input("Kamar")
    st.markdown(f"**Bulan:** {bulan} | **Tahun:** {tahun} | **Tanggal:** {hari_tanggal} | **Waktu:** {waktu} ({now.strftime('%H:%M:%S')})")
    st.subheader("Jumlah Jenis Pakaian")
    baju = st.number_input("Baju", min_value=0)
    sarung = st.number_input("Sarung", min_value=0)
    celana = st.number_input("Celana", min_value=0)
    jenis_lainnya = st.number_input("Jenis Lainnya", min_value=0) # Changed 'kopyah' to 'jenis_lainnya'
    st.subheader("Jumlah Pinjaman Barang")
    jepit = st.number_input("Jepit", min_value=0)
    hanger = st.number_input("Hanger", min_value=0)
    timba = st.number_input("Timba", min_value=0)
    no_kartu = st.text_input("Nomor Kartu")

    if st.button("Simpan"):
        if not nama or not kamar or not no_kartu:
            st.session_state.message_type = "error"
            st.session_state.message_content = "Nama, kamar, dan Nomor Kartu wajib diisi."
        elif waktu == "Tidak Tersedia":
            st.session_state.message_type = "error"
            st.session_state.message_content = "Waktu tidak valid untuk input data."
        else:
            berhasil = simpan_data_pelayanan((
                nama, daerah, kamar, bulan, tahun, hari_tanggal, waktu,
                baju, sarung, celana, jenis_lainnya, # Changed 'kopyah' to 'jenis_lainnya'
                jepit, hanger, timba,
                no_kartu, ""
            ))

            if berhasil:
                st.session_state.message_type = "success"
                st.session_state.message_content = "Data berhasil disimpan."
            else:
                st.session_state.message_type = "error"
                st.session_state.message_content = "Nomor kartu ini masih dipakai dan belum diambil atau direlokasi. Mohon periksa kembali."
        st.rerun() 

# ==================== MENU: STATUS ==================== #
def menu_update_status():
    st.title("Status Pengambilan")
    df = get_data("SELECT * FROM data_pelayanan WHERE ambil = 'Tidak'")
    if df.empty:
        st.info("Semua jemuran telah diambil. Tidak ada data yang perlu diperbarui.")
        return
    
    st.write("Daftar Jemuran yang Belum Diambil:")
    selected_id = st.selectbox(
        "Pilih ID Data Pelayanan", 
        df["id"], 
        format_func=lambda x: f"ID: {x} - {df[df['id'] == x]['nama_pemilik'].iloc[0]} (Kartu: {df[df['id'] == x]['no_kartu'].iloc[0]})"
    )
    st.dataframe(df[df["id"] == selected_id])

    st.subheader("Input Barang yang Dikembalikan")
    st.info("Masukkan jumlah barang pinjaman yang dikembalikan. Jika kurang dari yang dipinjam, selisihnya akan dicatat sebagai hilang.")
    
    current_jepit_borrowed = df[df['id'] == selected_id]['jepit'].iloc[0] if not df[df['id'] == selected_id]['jepit'].isnull().all() else 0
    current_hanger_borrowed = df[df['id'] == selected_id]['hanger'].iloc[0] if not df[df['id'] == selected_id]['hanger'].isnull().all() else 0
    current_timba_borrowed = df[df['id'] == selected_id]['timba'].iloc[0] if not df[df['id'] == selected_id]['timba'].isnull().all() else 0

    jepit_kembali = st.number_input(f"Jepit Dikembalikan (Dipinjam: {current_jepit_borrowed})", min_value=0, value=current_jepit_borrowed)
    hanger_kembali = st.number_input(f"Hanger Dikembalikan (Dipinjam: {current_hanger_borrowed})", min_value=0, value=current_hanger_borrowed)
    timba_kembali = st.number_input(f"Timba Dikembalikan (Dipinjam: {current_timba_borrowed})", min_value=0, value=current_timba_borrowed)

    if st.button("Ubah Status Menjadi 'Sudah Diambil'"):
        if update_status_ambil(selected_id, jepit_kembali, hanger_kembali, timba_kembali):
            st.session_state.message_type = "success"
            st.session_state.message_content = "Status berhasil diubah menjadi 'Sudah Diambil', stok diperbarui, dan kehilangan dicatat (jika ada)."
        else:
            st.session_state.message_type = "error"
            st.session_state.message_content = "Gagal memperbarui status. Silakan coba lagi."
        st.rerun() 


# ==================== MENU: KEHILANGAN ==================== #
def menu_data_kehilangan():
    st.title("Data Kehilangan")

    df_pelayanan = get_data("SELECT * FROM data_pelayanan")
    
    st.markdown("### ➕ Tambah Data Kehilangan")
    st.info("Pilih data pelayanan yang terkait, atau biarkan kosong jika kehilangan tidak terkait langsung dengan layanan tertentu (misal: stok hilang di gudang).")
    
    pelayanan_ids = ['Tidak Terkait Layanan'] + df_pelayanan["id"].tolist()
    selected_id_for_loss = st.selectbox(
        "Pilih ID Data Pelayanan yang Melaporkan Kehilangan (Opsional)", 
        pelayanan_ids, 
        format_func=lambda x: f"ID: {x} - {df_pelayanan[df_pelayanan['id'] == x]['nama_pemilik'].iloc[0]} (Kartu: {df_pelayanan[df_pelayanan['id'] == x]['no_kartu'].iloc[0]})" if x != 'Tidak Terkait Layanan' else x
    )

    id_pelayanan_to_save = None
    if selected_id_for_loss != 'Tidak Terkait Layanan':
        id_pelayanan_to_save = selected_id_for_loss
        st.write("Detail Data Pelayanan Terpilih:")
        st.dataframe(df_pelayanan[df_pelayanan["id"] == id_pelayanan_to_save])

    jenis = st.selectbox(
        "Jenis Barang yang Hilang",
        ["Baju", "Sarung", "Celana", "Jenis Lainnya", "Jepit", "Hanger", "Timba", "Kartu"] # Changed 'Kopyah' to 'Jenis Lainnya'
    )
    jumlah = st.number_input("Jumlah Barang yang Hilang", min_value=1, step=1)
    keterangan_hilang = st.text_area("Keterangan Kehilangan (Opsional)", "Tidak dikembalikan / Rusak / Hilang di gudang")

    if st.button("Simpan Data Kehilangan"):
        if simpan_data_kehilangan(id_pelayanan_to_save, jenis, jumlah, keterangan_hilang):
            st.session_state.message_type = "success"
            st.session_state.message_content = "Data kehilangan berhasil disimpan dan stok (jika barang pinjaman) diperbarui."
        else:
            st.session_state.message_type = "error"
            st.session_state.message_content = "Gagal menyimpan data kehilangan. Silakan coba lagi."
        st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Riwayat Data Kehilangan")
    df_kehilangan = get_data_kehilangan_lengkap()

    if df_kehilangan.empty:
        st.info("Belum ada data kehilangan yang tercatat.")
        return

    filter_nama = st.text_input("🔍 Filter berdasarkan Nama Pemilik (di riwayat kehilangan)")
    if filter_nama:
        df_kehilangan = df_kehilangan[df_kehilangan["nama_pemilik"].str.contains(filter_nama, case=False, na=False, regex=True)]

    if df_kehilangan.empty and filter_nama:
        st.warning(f"Tidak ditemukan data kehilangan untuk '{filter_nama}'.")
    else:
        st.dataframe(df_kehilangan, use_container_width=True)

    # ------------------ Export Excel ------------------ #
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df_kehilangan.to_excel(writer, index=False, sheet_name="Data Kehilangan")
    writer.close()
    st.download_button("📥 Export Data Kehilangan ke Excel", output.getvalue(), file_name="data_kehilangan.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ==================== MENU: STATISTIK ==================== #
def menu_data_statistik():
    st.title("Statistik Data Jemuran")
    df = get_data("SELECT * FROM data_pelayanan")
    if df.empty:
        st.warning("Data belum tersedia. Silakan input data pengguna terlebih dahulu.")
        return

    st.sidebar.subheader("Filter Data")
    
    # Filter Nama Pemilik
    filter_nama_pemilik = st.sidebar.text_input("Filter Nama Pemilik")
    if filter_nama_pemilik:
        df = df[df["nama_pemilik"].str.contains(filter_nama_pemilik, case=False, na=False)]

    # Filter No Kartu
    filter_no_kartu = st.sidebar.text_input("Filter Nomor Kartu")
    if filter_no_kartu:
        df = df[df["no_kartu"].astype(str).str.contains(filter_no_kartu, case=False, na=False)]

    # Filter Lainnya
    for col in ["daerah", "ambil", "bulan", "tahun", "hari_tanggal", "waktu"]:
        unique_values = df[col].astype(str).unique()
        if col == "hari_tanggal":
            unique_values = sorted(unique_values)
        elif col == "tahun":
            unique_values = sorted(unique_values, reverse=True)
        
        pilih = st.sidebar.multiselect(col.replace("_", " ").title(), unique_values)
        if pilih:
            df = df[df[col].astype(str).isin(pilih)]
    
    # ========== Notifikasi Otomatis Jika Melebihi 2 Hari ==========
    st.subheader("🔔 Notifikasi Relokasi Otomatis (Jemuran Melebihi 2 Hari)")
    
    df["hari_tanggal"] = pd.to_datetime(df["hari_tanggal"]) 
    hari_ini = pd.to_datetime(datetime.now().date())
    
    df_terlambat = df[(df["ambil"] == "Tidak") & ((hari_ini - df["hari_tanggal"]).dt.days > 2)]

    if not df_terlambat.empty:
        for _, row in df_terlambat.iterrows():
            st.warning(f"🔴 **{row['nama_pemilik']}** (No Kartu: **{row['no_kartu']}**) di daerah **{row['daerah']}** (Kamar: **{row['kamar']}**) sudah lebih dari 2 hari ({row['hari_tanggal'].strftime('%d %B %Y')}). Harap segera direlokasi!")
    else:
        st.success("✅ Tidak ada jemuran yang belum diambil yang melebihi 2 hari.")

    # --- Tampilkan notifikasi penghapusan 7 hari sebelumnya ---
    if st.session_state.show_delete_warning_this_session:
        next_delete_date_str = get_app_setting('next_3_month_delete_schedule')
        if next_delete_date_str:
            next_delete_date = datetime.fromisoformat(next_delete_date_str).date()
            hari_ini_date = datetime.now().date()
            days_until_next_delete = (next_delete_date - hari_ini_date).days
            st.warning(f"⚠️ **PERINGATAN PENGHAPUSAN DATA!** Penghapusan data lama (status 'Sudah Diambil/Iya') akan segera dilakukan pada **{next_delete_date.strftime('%d %B %Y')}** (dalam {days_until_next_delete} hari). Harap ekspor data Anda sekarang jika diperlukan.")

    st.markdown("---")
    st.subheader("Ringkasan Statistik")
    
    st.subheader("1. Layanan per Daerah")
    st.bar_chart(df["daerah"].value_counts(), use_container_width=True)
    
    st.subheader("2. Jenis Pakaian yang Terdata")
    st.bar_chart(df[["baju", "sarung", "celana", "jenis_lainnya"]].sum(), use_container_width=True) # Changed 'kopyah' to 'jenis_lainnya'
    
    st.subheader("3. Pinjaman Barang")
    st.bar_chart(df[["jepit", "hanger", "timba"]].sum(), use_container_width=True)
    
    st.subheader("4. Data per Shift Waktu")
    st.bar_chart(df["waktu"].value_counts(), use_container_width=True)
    
    st.subheader("5. Status Pengambilan")
    st.bar_chart(df["ambil"].value_counts(), use_container_width=True)
    
    st.subheader("6. Stok Barang Pinjaman")
    stok_df = get_data("SELECT nama_barang, jumlah_total, stok_tersedia FROM stok_pinjaman")

    # Ambil total kehilangan barang pinjaman dari data_kehilangan
    df_hilang_barang = get_ringkasan_kehilangan_barang_pinjaman()

    # Gabungkan data stok dan kehilangan
    stok_info = pd.merge(stok_df, df_hilang_barang, on='nama_barang', how='left')
    stok_info['jumlah_hilang_total'] = stok_info['jumlah_hilang_total'].fillna(0).astype(int)
    
    # Tampilkan DataFrame dengan kolom yang relevan
    st.dataframe(
        stok_info[["nama_barang", "jumlah_total", "stok_tersedia", "jumlah_hilang_total"]].rename(
            columns={"jumlah_total": "Jumlah Awal/Ditambah", "stok_tersedia": "Stok Tersedia Saat Ini", "jumlah_hilang_total": "Jumlah Hilang"}
        ), 
        hide_index=True,
        use_container_width=True
    )

    st.markdown("#### ➕ Tambah Stok Barang")
    nama_barang_tambah = st.selectbox("Pilih Barang untuk Ditambah Stok", stok_df["nama_barang"].unique())
    jumlah_tambah = st.number_input("Jumlah Tambahan Stok", min_value=1, step=1)

    if st.button("Tambah Stok Barang"):
        if tambah_stok_barang(nama_barang_tambah, jumlah_tambah):
            st.session_state.message_type = "success"
            st.session_state.message_content = f"Stok barang '{nama_barang_tambah}' berhasil ditambah sebanyak {jumlah_tambah}."
        else:
            st.session_state.message_type = "error"
            st.session_state.message_content = "Gagal menambah stok barang. Silakan coba lagi."
        st.rerun()
    
    st.subheader("7. Total Pengguna Unik")
    st.info(f"Terdapat **{df['nama_pemilik'].nunique()}** pengguna unik yang terdata.")
    
    st.subheader("8. Total Pengguna per Daerah")
    pengguna_per_daerah = df.groupby("daerah")["nama_pemilik"].nunique().reset_index()
    pengguna_per_daerah.columns = ["Daerah", "Total Pengguna Unik"]
    st.dataframe(pengguna_per_daerah, hide_index=True, use_container_width=True)
    
    st.subheader("9. Tabel Data Pelayanan Lengkap")
    st.dataframe(df, use_container_width=True)
    
    st.subheader("10. Relokasi Nomor Kartu")
    if not df.empty:
        df_unpicked = df[df['ambil'] == 'Tidak']
        if not df_unpicked.empty:
            id_pilih = st.selectbox(
                "Pilih ID Data Pelayanan yang Akan Direlokasi (Belum Diambil)", 
                df_unpicked["id"], 
                format_func=lambda x: f"ID: {x} - {df_unpicked[df_unpicked['id'] == x]['nama_pemilik'].iloc[0]} (Kartu: {df_unpicked[df_unpicked['id'] == x]['no_kartu'].iloc[0]})"
            )
            keterangan = st.text_input("Masukkan Keterangan Relokasi (e.g., 'Dipindah ke jemuran C')")
            if st.button("Simpan Keterangan Relokasi"):
                if update_relokasi(id_pilih, keterangan):
                    st.session_state.message_type = "success"
                    st.session_state.message_content = f"Keterangan relokasi untuk ID **{id_pilih}** berhasil diperbarui."
                else:
                    st.session_state.message_type = "error"
                    st.session_state.message_content = "Gagal memperbarui relokasi. Silakan coba lagi."
                st.rerun()
        else:
            st.info("Tidak ada jemuran yang belum diambil yang dapat direlokasi.")
    else:
        st.info("Tidak ada data pelayanan yang tersedia untuk direlokasi.")

    st.markdown("---")
    export_excel(df, "data_statistik_jemuran.xlsx")


# ==================== MAIN MENU ==================== #
# --- Jalankan pemeriksaan penghapusan otomatis di awal aplikasi ---
check_and_trigger_auto_delete()

with st.sidebar:
    selected = option_menu("📁 Menu",
        ["Input Data Pengguna", "Status Pengambilan", "Data Statistik", "Data Kehilangan"],
        icons=["person-plus", "check-circle", "bar-chart", "exclamation-triangle"],
        menu_icon="grid-3x3-gap", default_index=0,
        styles={
            "container": {"padding": "5px", "background-color": "#ffffff"},
            "icon": {"color": "#0d6efd", "font-size": "18px"},
            "nav-link": {"color": "#333", "font-size": "16px", "text-align": "left"},
            "nav-link-selected": {"background-color": "#cce5ff"},
        }
    )

# Tampilkan pesan dari session state di bagian atas konten utama
if st.session_state.message_type == "success":
    st.success(st.session_state.message_content)
elif st.session_state.message_type == "error":
    st.error(st.session_state.message_content)
elif st.session_state.message_type == "info": # Untuk notifikasi otomatis
    st.info(st.session_state.message_content)

# Setelah pesan ditampilkan, reset session state agar pesan tidak muncul lagi di rerun berikutnya
st.session_state.message_type = None
st.session_state.message_content = ""
st.session_state.auto_delete_performed_this_session = False # Reset flag setelah pesan ditampilkan


if selected == "Input Data Pengguna":
    menu_data_pelayanan()
elif selected == "Status Pengambilan":
    menu_update_status()
elif selected == "Data Statistik":
    menu_data_statistik()
elif selected == "Data Kehilangan":
    menu_data_kehilangan()

# ==================== FOOTER ==================== #
st.markdown("""
    <div class='footer'>
        &copy; 2025 Sistem Jemuran Pesantren | Designed by Muhammad Babun Waseptian
    </div>
""", unsafe_allow_html=True)