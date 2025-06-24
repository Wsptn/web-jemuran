import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from datetime import datetime, time
from io import BytesIO
from db_connection import get_connection

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

# ==================== DATABASE ==================== #
def get_data(query, params=None):
    conn = get_connection()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def simpan_data_pelayanan(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT * FROM data_pelayanan
        WHERE no_kartu = %s AND ambil = 'Tidak' AND (relokasi IS NULL OR relokasi = '')""", (data[14],))
    if cursor.fetchone():
        conn.close()
        return False
    cursor.execute("UPDATE stok_pinjaman SET jumlah = jumlah - %s WHERE nama_barang = 'Jepit'", (data[11],))
    cursor.execute("UPDATE stok_pinjaman SET jumlah = jumlah - %s WHERE nama_barang = 'Hanger'", (data[12],))
    cursor.execute("UPDATE stok_pinjaman SET jumlah = jumlah - %s WHERE nama_barang = 'Timba'", (data[13],))
    query = """
        INSERT INTO data_pelayanan (
            nama_pemilik, daerah, kamar, bulan, tahun, hari_tanggal, waktu,
            baju, sarung, celana, kopyah,
            jepit, hanger, timba,
            no_kartu, relokasi, ambil
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Tidak')
    """
    cursor.execute(query, data)
    conn.commit()
    conn.close()
    return True

def update_status_ambil(id_data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT jepit, hanger, timba FROM data_pelayanan WHERE id = %s", (id_data,))
    jepit, hanger, timba = cursor.fetchone()
    cursor.execute("UPDATE stok_pinjaman SET jumlah = jumlah + %s WHERE nama_barang = 'Jepit'", (jepit,))
    cursor.execute("UPDATE stok_pinjaman SET jumlah = jumlah + %s WHERE nama_barang = 'Hanger'", (hanger,))
    cursor.execute("UPDATE stok_pinjaman SET jumlah = jumlah + %s WHERE nama_barang = 'Timba'", (timba,))
    cursor.execute("UPDATE data_pelayanan SET ambil = 'Iya' WHERE id = %s", (id_data,))
    conn.commit()
    conn.close()
    return jepit, hanger, timba

def update_relokasi(id_data, isi_relokasi):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE data_pelayanan SET relokasi = %s WHERE id = %s", (isi_relokasi, id_data))
    conn.commit()
    conn.close()

def simpan_data_kehilangan(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO data_kehilangan (id_pelayanan, jenis_pakaian, jumlah) VALUES (%s, %s, %s)", data)
    conn.commit()
    conn.close()

def get_data_kehilangan():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT k.id, k.id_pelayanan, p.nama_pemilik, p.no_kartu, k.jenis_pakaian, k.jumlah
        FROM data_kehilangan k
        JOIN data_pelayanan p ON k.id_pelayanan = p.id
    """, conn)
    conn.close()
    return df


def export_excel(df, filename):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')

    # Sheet 1: Tabel Data
    df.to_excel(writer, sheet_name="Tabel Data", index=False)

    workbook  = writer.book
    sheet = workbook.add_worksheet("Ringkasan")
    writer.sheets["Ringkasan"] = sheet

    # 1. Total Pengguna
    total_pengguna = df["nama_pemilik"].nunique()
    sheet.write("A1", "Total Pengguna")
    sheet.write("B1", total_pengguna)

    # 2. Jenis Pakaian
    pakaian = df[["baju", "sarung", "celana", "kopyah"]].sum()
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
# ==================== MENU: INPUT ==================== #
def menu_data_pelayanan():
    st.title("Input Data Pengguna")
    now = datetime.now()
    bulan = now.strftime("%B")
    tahun = now.strftime("%Y")
    hari_tanggal = now.date()
    jam_menit = now.time()
    waktu = "Pagi" if time(6,30) <= jam_menit <= time(11,0) else \
            "Siang" if time(11,0) < jam_menit <= time(16,0) else \
            "Malam" if time(20,0) <= jam_menit or jam_menit <= time(1,0) else \
            "Tidak Tersedia"

    if waktu == "Tidak Tersedia":
        st.warning("Waktu input tidak sesuai shift.")

    nama = st.text_input("Nama Pemilik")
    daerah = st.selectbox("Daerah", DAERAH_LIST)
    kamar = st.text_input("Kamar")
    st.markdown(f"**Bulan:** {bulan} | **Tahun:** {tahun} | **Tanggal:** {hari_tanggal} | **Waktu:** {waktu}")
    st.subheader("Jumlah Jenis Pakaian")
    baju = st.number_input("Baju", min_value=0)
    sarung = st.number_input("Sarung", min_value=0)
    celana = st.number_input("Celana", min_value=0)
    kopyah = st.number_input("Kopyah", min_value=0)
    st.subheader("Jumlah Pinjaman Barang")
    jepit = st.number_input("Jepit", min_value=0)
    hanger = st.number_input("Hanger", min_value=0)
    timba = st.number_input("Timba", min_value=0)
    no_kartu = st.text_input("Nomor Kartu")

    if st.button("Simpan"):
        if not nama or not kamar:
            st.error("Nama dan kamar wajib diisi.")
            st.stop()
        elif waktu == "Tidak Tersedia":
            st.error("Waktu tidak valid.")
            st.stop()
        else:
            berhasil = simpan_data_pelayanan((
                nama, daerah, kamar, bulan, tahun, hari_tanggal, waktu,
                baju, sarung, celana, kopyah,
                jepit, hanger, timba,
                no_kartu, ""
            ))

            if berhasil:
                st.success("Data berhasil disimpan.")
            else:
                st.error("Nomor kartu masih dipakai dan belum direlokasi.")
                st.stop()

# ==================== MENU: STATUS ==================== #
def menu_update_status():
    st.title("Status Pengambilan")
    df = get_data("SELECT * FROM data_pelayanan")
    belum = df[df["ambil"] == "Tidak"]
    if belum.empty:
        st.info("Semua sudah diambil.")
        return
    selected = st.selectbox("Pilih ID", belum["id"])
    st.dataframe(belum[belum["id"] == selected])
    if st.button("Ubah ke 'Iya'"):
        jepit, hanger, timba = update_status_ambil(selected)
        st.success(f"Barang dikembalikan: Jepit {jepit}, Hanger {hanger}, Timba {timba}")

# ==================== MENU: KEHILANGAN ==================== #
def menu_data_kehilangan():
    st.title("Data Kehilangan")

    df = get_data("SELECT * FROM data_pelayanan")
    selected_id = st.selectbox("Pilih ID Data Pelayanan", df["id"])
    st.dataframe(df[df["id"] == selected_id])

    jenis = st.selectbox("Jenis Pakaian yang Hilang", ["Baju", "Sarung", "Celana", "Kopyah"])
    jumlah = st.number_input("Jumlah Hilang", min_value=1)
    
    if st.button("Simpan Kehilangan"):
        simpan_data_kehilangan((selected_id, jenis, jumlah))
        st.success("Data kehilangan berhasil disimpan.")

    # ------------------ Tabel Kehilangan ------------------ #
    st.subheader("Riwayat Data Kehilangan")
    df_kehilangan = get_data_kehilangan()

    filter_nama = st.text_input("🔍 Filter Nama Pemilik")
    if filter_nama:
        df_kehilangan = df_kehilangan[df_kehilangan["nama_pemilik"].str.contains(filter_nama, case=False)]

    st.dataframe(df_kehilangan)

    # ------------------ Export Excel ------------------ #
    from io import BytesIO
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
        st.warning("Data belum tersedia.")
        return

    st.sidebar.subheader("Filter")
    
    # Filter Nama Pemilik
    df = df[df["nama_pemilik"].str.contains(st.sidebar.text_input("Nama Pemilik"), case=False, na=False)]

    # Tambahan: Filter No Kartu
    no_kartu = st.sidebar.text_input("Nomor Kartu")
    if no_kartu:
        df = df[df["no_kartu"].astype(str).str.contains(no_kartu, case=False, na=False)]

    # Filter Lainnya
    for col in ["daerah", "ambil", "bulan", "tahun", "hari_tanggal"]:
        pilih = st.sidebar.multiselect(col.title(), df[col].astype(str).unique())
        if pilih:
            df = df[df[col].astype(str).isin(pilih)]
    # ========== Notifikasi Otomatis Jika Melebihi 2 Hari ==========
    st.subheader("🔔 Notifikasi Relokasi Otomatis (Melebihi 2 Hari)")
    hari_ini = pd.to_datetime(datetime.now().date())
    df["hari_tanggal"] = pd.to_datetime(df["hari_tanggal"])
    df_terlambat = df[(df["ambil"] == "Tidak") & ((hari_ini - df["hari_tanggal"]).dt.days > 2)]

    if not df_terlambat.empty:
        for _, row in df_terlambat.iterrows():
            st.warning(f"🔴 {row['nama_pemilik']} (No Kartu: {row['no_kartu']}) sudah lebih dari 2 hari, harap segera direlokasi.")
    else:
        st.success("✅ Tidak ada jemuran yang melebihi 2 hari.")

    st.subheader("1. Layanan per Daerah")
    st.bar_chart(df["daerah"].value_counts())
    st.subheader("2. Jenis Pakaian")
    st.bar_chart(df[["baju", "sarung", "celana", "kopyah"]].sum())
    st.subheader("3. Pinjaman Barang")
    st.bar_chart(df[["jepit", "hanger", "timba"]].sum())
    st.subheader("4. Shift")
    st.bar_chart(df["waktu"].value_counts())
    st.subheader("5. Status Ambil")
    st.bar_chart(df["ambil"].value_counts())
    st.subheader("6. Sisa Stok")
    st.dataframe(get_data("SELECT * FROM stok_pinjaman"))
    st.subheader("7. Total Pengguna")
    st.info(f"{df['nama_pemilik'].nunique()} pengguna")
    st.subheader("8. Total Pengguna per Daerah")
    pengguna_per_daerah = df.groupby("daerah")["nama_pemilik"].nunique().reset_index()
    pengguna_per_daerah.columns = ["Daerah", "Total Pengguna"]
    st.dataframe(pengguna_per_daerah)
    st.subheader("9. Tabel Data")
    st.dataframe(df)
    st.subheader("10. Relokasi Nomor Kartu")
    if not df.empty:
        id_pilih = st.selectbox("Pilih ID yang akan direlokasi", df["id"])
        keterangan = st.text_input("Isi Keterangan Relokasi")
        if st.button("Simpan Relokasi"):
            update_relokasi(id_pilih, keterangan)
            st.success(f"Relokasi untuk ID {id_pilih} berhasil diperbarui.")

    export_excel(df, "data_statistik.xlsx")


# ==================== MAIN MENU ==================== #
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
