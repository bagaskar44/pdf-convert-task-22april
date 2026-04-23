# 🚗 SAMSAT PDF to Excel Converter

Aplikasi Streamlit untuk mengkonversi file PDF **Detail Penerimaan Per Transaksi Kasir** dari SAMSAT Jawa Timur ke format Excel.

## Fitur

- Parse otomatis data kendaraan dari PDF SAMSAT
- Mendukung semua prefix nopol (W, L, S, N, AG, dll)
- Mendukung alamat 1 baris maupun alamat panjang (wrap 2 baris)
- Filter data by Jenis Kendaraan, Warna Plat, dan Status Pajak
- Deteksi otomatis **Pajak Lewat** berdasarkan tanggal referensi
- Export ke Excel dengan lebar kolom otomatis

## Kolom Output

| Kolom | Keterangan |
|---|---|
| Nopol | Nomor polisi kendaraan |
| Nama Pemilik | Nama pemilik kendaraan |
| Alamat | Alamat lengkap + kode kab/kota |
| Jenis Kendaraan | Sepeda Motor / Minibus / Tractor Head / dll |
| Warna Plat | Putih / Kuning / Merah |
| Tahun Buat | Tahun pembuatan kendaraan |
| Tanggal Penetapan | Tanggal TETAP pada TGL PROSES |
| Tanggal Masa Laku Pajak | Batas berlaku pajak kendaraan |
| Tanggal Masa Laku STNK | Batas berlaku STNK |
| Pajak Lewat | Yes / No (vs tanggal referensi user) |

## Instalasi Lokal

```bash
pip install -r requirements.txt
streamlit run samsat_converter.py
```

## Deploy ke Streamlit Cloud

Lihat panduan di bawah ⬇️
