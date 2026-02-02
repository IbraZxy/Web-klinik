from flask import Flask, render_template, request, redirect, make_response
from fpdf import FPDF
import mysql.connector

app = Flask(__name__)

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'rawat_inap_ibnu'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

def get_pasien():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM pasien_ibnu")
    pasien = cursor.fetchall()
    cursor.close()
    conn.close()
    return pasien

def get_kamar():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM kamar_ibnu")
    kamar = cursor.fetchall()
    cursor.close()
    conn.close()
    return kamar

def id_transaksi_OTOMATIS(prefix, table, column):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT {column} FROM {table} ORDER BY {column} DESC LIMIT 1")
    id_transaksi_ibnu = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if id_transaksi_ibnu:
        parts = id_transaksi_ibnu[0].split('-')
        num = int(parts[1]) + 1
        return f"{prefix}-{str(num).zfill(3)}"
    else:
        return f"{prefix}-001"

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            t.id_transaksi_ibnu,
            p.nama_ibnu,
            r.id_rawat_ibnu,
            r.tgl_masuk_ibnu,
            r.tgl_keluar_ibnu,
            r.jumlah_hari_ibnu,
            k.no_kamar_ibnu,
            k.kelas_ibnu,
            t.total_biaya_ibnu,
            t.status_pembayaran_ibnu,
            t.tgl_ibnu
        FROM transaksi_ibnu t
        JOIN pasien_ibnu p 
            ON t.id_pasien_ibnu = p.id_pasien_ibnu
        JOIN rawat_inap_ibnu r 
            ON p.id_pasien_ibnu = r.id_pasien_ibnu
        JOIN kamar_ibnu k
            ON r.id_kamar_ibnu = k.id_kamar_ibnu
    """)
    transaksi = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('transaksi_ibnu.html', transaksi=transaksi)

@app.route('/pasien_ibnu', methods=['GET', 'POST'])
def pasien_ibnu():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM `pasien_ibnu`; ")
    pasien = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('pasien_ibnu.html', pasien=pasien)

from datetime import datetime

@app.route('/formData', methods=['GET', 'POST'])
def formData():
    pasien = get_pasien()
    kamar = get_kamar()

    if request.method == 'POST':
        id_transaksi = id_transaksi_OTOMATIS("TR", "transaksi_ibnu", "id_transaksi_ibnu")
        id_pasien = request.form['id_pasien_ibnu']
        id_kamar = request.form['id_kamar_ibnu']
        status = request.form['status_pembayaran_ibnu']
        tgl_transaksi = request.form['tgl_ibnu']
        
        tgl_m = datetime.strptime(request.form['tgl_masuk_ibnu'], '%Y-%m-%d')
        tgl_k = datetime.strptime(request.form['tgl_keluar_ibnu'], '%Y-%m-%d')
        selisih = (tgl_k - tgl_m).days
        jumlah_hari = selisih if selisih > 0 else 1 # Minimal 1 hari

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            UPDATE rawat_inap_ibnu SET 
            tgl_masuk_ibnu=%s, tgl_keluar_ibnu=%s, jumlah_hari_ibnu=%s, id_kamar_ibnu=%s
            WHERE id_pasien_ibnu=%s
        """, (request.form['tgl_masuk_ibnu'], request.form['tgl_keluar_ibnu'], jumlah_hari, id_kamar, id_pasien))

        cursor.execute("SELECT harga_ibnu FROM kamar_ibnu WHERE id_kamar_ibnu = %s", (id_kamar,))
        kamar_data = cursor.fetchone()
        total_biaya = kamar_data['harga_ibnu'] * jumlah_hari

        cursor.execute("""
            INSERT INTO transaksi_ibnu
            (id_transaksi_ibnu, id_pasien_ibnu, total_biaya_ibnu, status_pembayaran_ibnu, tgl_ibnu)
            VALUES (%s, %s, %s, %s, %s)
        """, (id_transaksi, id_pasien, total_biaya, status, tgl_transaksi))

        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/')

    return render_template('form_ibnu.html', pasien=pasien, kamar=kamar)

@app.route('/editData/<id_transaksi_ibnu>', methods=['GET', 'POST'])
def editData(id_transaksi_ibnu):
    pasien = get_pasien()
    kamar = get_kamar()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        id_pasien = request.form['id_pasien_ibnu']
        id_kamar = request.form['id_kamar_ibnu']
        
        # selisih hari
        tgl_m = datetime.strptime(request.form['tgl_masuk_ibnu'], '%Y-%m-%d')
        tgl_k = datetime.strptime(request.form['tgl_keluar_ibnu'], '%Y-%m-%d')
        selisih = (tgl_k - tgl_m).days
        jumlah_hari = selisih if selisih > 0 else 1

        cursor.execute("""
            UPDATE rawat_inap_ibnu SET 
            tgl_masuk_ibnu=%s, tgl_keluar_ibnu=%s, jumlah_hari_ibnu=%s, id_kamar_ibnu=%s
            WHERE id_pasien_ibnu=%s
        """, (request.form['tgl_masuk_ibnu'], request.form['tgl_keluar_ibnu'], jumlah_hari, id_kamar, id_pasien))

        # total biaya baru
        cursor.execute("SELECT harga_ibnu FROM kamar_ibnu WHERE id_kamar_ibnu = %s", (id_kamar,))
        kamar_row = cursor.fetchone()
        total_biaya = kamar_row['harga_ibnu'] * jumlah_hari

        cursor.execute("""
            UPDATE transaksi_ibnu SET
            id_pasien_ibnu=%s, total_biaya_ibnu=%s, status_pembayaran_ibnu=%s, tgl_ibnu=%s
            WHERE id_transaksi_ibnu=%s
        """, (id_pasien, total_biaya, request.form['status_pembayaran_ibnu'], request.form['tgl_ibnu'], id_transaksi_ibnu))
        
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/')

    cursor.execute("""
        SELECT t.*, r.tgl_masuk_ibnu, r.tgl_keluar_ibnu, r.id_kamar_ibnu 
        FROM transaksi_ibnu t
        JOIN rawat_inap_ibnu r ON t.id_pasien_ibnu = r.id_pasien_ibnu
        WHERE t.id_transaksi_ibnu=%s
    """, (id_transaksi_ibnu,))
    transaksi_ibnu = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('form_ibnu.html', transaksi_ibnu=transaksi_ibnu, pasien=pasien, kamar=kamar)

@app.route('/hapusData/<id_transaksi_ibnu>', methods=['POST','GET'])
def hapusData(id_transaksi_ibnu):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transaksi_ibnu WHERE id_transaksi_ibnu=%s", (id_transaksi_ibnu,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/')

@app.route('/cetak_pasien_ibnu')
def cetak_pasien_ibnu():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM pasien_ibnu")
        data_pasien = cursor.fetchall()
        cursor.close()
        conn.close()

        pdf = FPDF()
        pdf.add_page()
        
        pdf.set_font('Helvetica', 'B', 16)
        
        pdf.cell(0, 10, 'Laporan Data Pasien', align='C', new_x='LMARGIN', new_y='NEXT')
        pdf.ln(5)

        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_fill_color(200, 220, 255)
        
        col_id = 40
        col_nama = 50
        col_alamat = 60
        col_kontak = 40

        pdf.cell(col_id, 10, 'ID Pasien', border=1, align='C', fill=True)
        pdf.cell(col_nama, 10, 'Nama', border=1, align='C', fill=True)
        pdf.cell(col_alamat, 10, 'Alamat', border=1, align='C', fill=True)
        pdf.cell(col_kontak, 10, 'Kontak', border=1, align='C', fill=True)
        pdf.ln()

        pdf.set_font('Helvetica', '', 10)
        for row in data_pasien:
            pdf.cell(col_id, 10, str(row['id_pasien_ibnu']), border=1)
            pdf.cell(col_nama, 10, str(row['nama_ibnu']), border=1)
            pdf.cell(col_alamat, 10, str(row['alamat_ibnu']), border=1)
            pdf.cell(col_kontak, 10, str(row['kontak_ibnu']), border=1)
            pdf.ln()

        pdf_bytes = pdf.output()
        
        response = make_response(bytes(pdf_bytes))
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=laporan_pasien.pdf'
        return response

    except Exception as e:
        return f"<h1>Gagal Mencetak PDF</h1><p>Error: {e}</p>"

@app.route('/cetak_transaksi_ibnu')
def cetak_transaksi_ibnu():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                t.id_transaksi_ibnu,
                p.nama_ibnu,
                r.id_rawat_ibnu,
                r.tgl_masuk_ibnu,
                r.tgl_keluar_ibnu,
                r.jumlah_hari_ibnu,
                k.kelas_ibnu,
                t.total_biaya_ibnu,
                t.status_pembayaran_ibnu,
                t.tgl_ibnu
            FROM transaksi_ibnu t
            JOIN pasien_ibnu p ON t.id_pasien_ibnu = p.id_pasien_ibnu
            JOIN rawat_inap_ibnu r ON p.id_pasien_ibnu = r.id_pasien_ibnu
            JOIN kamar_ibnu k ON r.id_kamar_ibnu = k.id_kamar_ibnu
        """)
        data_transaksi = cursor.fetchall()
        cursor.close()
        conn.close()

        pdf = FPDF('L', 'mm', 'A4') 
        pdf.add_page()
        
        pdf.set_font('Helvetica', 'B', 16)
        pdf.cell(0, 10, 'Laporan Data Transaksi Rawat Inap', align='C', ln=True)
        pdf.ln(5)

        pdf.set_font('Helvetica', 'B', 8) # ngecilin font
        pdf.set_fill_color(200, 220, 255)
        
        pdf.cell(25, 10, 'ID Trans', 1, 0, 'C', True)
        pdf.cell(25, 10, 'ID Rawat', 1, 0, 'C', True)
        pdf.cell(40, 10, 'Nama Pasien', 1, 0, 'C', True)
        pdf.cell(25, 10, 'Kelas', 1, 0, 'C', True)
        pdf.cell(30, 10, 'Status', 1, 0, 'C', True)
        pdf.cell(25, 10, 'Masuk', 1, 0, 'C', True)
        pdf.cell(25, 10, 'Keluar', 1, 0, 'C', True)
        pdf.cell(15, 10, 'Hari', 1, 0, 'C', True)
        pdf.cell(30, 10, 'Total Biaya', 1, 0, 'C', True)
        pdf.cell(30, 10, 'Tgl Trans', 1, 1, 'C', True)

        pdf.set_font('Helvetica', '', 8)
        for row in data_transaksi:
            pdf.cell(25, 10, str(row['id_transaksi_ibnu']), 1)
            pdf.cell(25, 10, str(row['id_rawat_ibnu']), 1)
            pdf.cell(40, 10, str(row['nama_ibnu']), 1)
            pdf.cell(25, 10, str(row['kelas_ibnu']), 1)
            pdf.cell(30, 10, str(row['status_pembayaran_ibnu']), 1)
            pdf.cell(25, 10, str(row['tgl_masuk_ibnu']), 1)
            pdf.cell(25, 10, str(row['tgl_keluar_ibnu']), 1)
            pdf.cell(15, 10, str(row['jumlah_hari_ibnu']), 1)
            pdf.cell(30, 10, f"Rp {row['total_biaya_ibnu']:,}", 1) # Format mata uang
            pdf.cell(30, 10, str(row['tgl_ibnu']), 1, 1)

        pdf_bytes = pdf.output()
        response = make_response(bytes(pdf_bytes))
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=laporan_transaksi.pdf'
        return response

    except Exception as e:
        return f"<h1>Gagal Mencetak PDF</h1><p>Error: {e}</p>"

if __name__ == '__main__':
    app.run(debug=True)
