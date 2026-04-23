import streamlit as st
import pandas as pd
import re
import subprocess
import tempfile
import os
from datetime import date
from io import BytesIO

st.set_page_config(page_title="PDF → Excel Converter", page_icon="📄", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #0f1117; color: #e8eaf0; }
.header-strip {
    background: linear-gradient(135deg, #1a3a5c 0%, #0d2137 100%);
    border-bottom: 2px solid #2e6da4;
    padding: 2rem 2.5rem 1.5rem;
    margin: -1rem -1rem 2rem;
    border-radius: 0 0 12px 12px;
}
.header-strip h1 { font-size: 1.8rem; font-weight: 600; color: #fff; margin: 0 0 .25rem; letter-spacing: -.5px; }
.header-strip p  { font-size: .875rem; color: #7bafd4; margin: 0; font-family: 'DM Mono', monospace; }
.stat-card { background: #141922; border: 1px solid #1e2d40; border-radius: 10px; padding: 1.2rem 1.5rem; text-align: center; margin-bottom: .5rem; }
.stat-number { font-size: 2rem; font-weight: 600; color: #4da6ff; font-family: 'DM Mono', monospace; line-height: 1; }
.stat-label  { font-size: .75rem; color: #6b7a99; margin-top: .4rem; text-transform: uppercase; letter-spacing: 1px; }
.stProgress > div > div { background-color: #2e6da4 !important; }
.stDownloadButton button {
    background: linear-gradient(135deg, #2e6da4, #1a4a7a) !important;
    color: white !important; border: none !important; border-radius: 8px !important;
    font-weight: 500 !important; padding: .6rem 1.5rem !important;
    font-family: 'DM Sans', sans-serif !important; font-size: .9rem !important;
    cursor: pointer !important; transition: all .2s !important;
}
.stDownloadButton button:hover {
    background: linear-gradient(135deg, #3a7dbf, #225a93) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(46,109,164,.4) !important;
}
.info-box {
    background: #0d2137; border-left: 3px solid #2e6da4;
    border-radius: 0 8px 8px 0; padding: .8rem 1.2rem;
    font-size: .85rem; color: #7bafd4; margin-bottom: 1rem;
    font-family: 'DM Mono', monospace;
}
.err-box {
    background: #2a0d0d; border-left: 3px solid #e53935;
    border-radius: 0 8px 8px 0; padding: .8rem 1.2rem;
    font-size: .85rem; color: #ff8a80; margin-bottom: .5rem;
}
hr { border-color: #1e2d40 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-strip">
    <h1>📄 PDF → Excel Converter</h1>
    <p>Konversi dokumen PDF ke format Excel secara otomatis</p>
</div>
""", unsafe_allow_html=True)


# ─── Parsing ─────────────────────────────────────────────────────────────────

def extract_field(text, pattern, group=1):
    m = re.search(pattern, text)
    return m.group(group).strip() if m else ""

def parse_vehicle_line(vline):
    kab_kota   = vline[:3].strip()
    jenis      = extract_field(vline, r',\s+([^:]+?)\s*:')
    warna_plat = extract_field(vline, r'PLAT\s+([A-Z\s]+?)(?:\s+NS\b|\s{2,}|\s*$|,)')
    tahun      = extract_field(vline, r'TH BUAT\s+(\d{4})')
    tgl_pajak  = extract_field(vline, r'PAJAK\s+(\d{2}/\d{2}/\d{4})')
    tgl_stnk   = extract_field(vline, r'STNK\s+(\d{2}/\d{2}/\d{4})')
    return kab_kota, jenis, warna_plat, tahun, tgl_pajak, tgl_stnk

def parse_records_from_page(lines, today):
    records = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^\s*([A-Z]{1,2})\s+(\d+)\s+(\S+)\s+(.+)', line)
        if not m:
            i += 1
            continue

        token1, token2, token3 = m.group(1), m.group(2), m.group(3)
        rest = m.group(4).strip()

        # Nama = sebelum "NO NOTICE"
        no_notice_pos = rest.find("NO NOTICE")
        nama_raw = rest[:no_notice_pos].strip() if no_notice_pos != -1 else rest.strip()
        nama  = " ".join(nama_raw.split())
        nopol = f"{token1} {token2} {token3}"

        # Kumpulkan baris alamat sampai baris kendaraan
        address_lines = []
        j = i + 1
        while j < len(lines):
            nl = lines[j].strip()
            if re.match(r'^[A-Z]{3},\s+', nl):
                break
            if (nl == ""
                    or re.match(r'^>', nl)
                    or re.match(r'^\(', nl)
                    or re.match(r'^(KASIR|NO\s+KE|PEMERINTAH|BADAN|KB\.|TANGGAL|DETAIL)', nl)):
                j += 1
                continue
            address_lines.append(nl)
            j += 1

        vehicle_line = lines[j].strip()   if j     < len(lines) else ""
        process_line = lines[j+1].strip() if j + 1 < len(lines) else ""

        kab_kota, jenis, warna_plat, tahun, tgl_pajak_str, tgl_stnk_str = parse_vehicle_line(vehicle_line)
        tgl_penetapan_str = extract_field(process_line, r'TETAP\s+(\d{2}/\d{2}/\d{4})')
        alamat = " ".join(address_lines + ([kab_kota] if kab_kota else [])).strip()

        try:
            d, mo, y = tgl_pajak_str.split("/")
            pajak_lewat = "Yes" if date(int(y), int(mo), int(d)) < today else "No"
        except Exception:
            pajak_lewat = "No"

        records.append({
            "Nopol":                   nopol,
            "Nama Pemilik":            nama,
            "Alamat":                  alamat,
            "Jenis Kendaraan":         jenis,
            "Warna Plat":              warna_plat,
            "Tahun Buat":              tahun,
            "Tanggal Penetapan":       tgl_penetapan_str,
            "Tanggal Masa Laku Pajak": tgl_pajak_str,
            "Tanggal Masa Laku STNK":  tgl_stnk_str,
            "Pajak Lewat":             pajak_lewat,
        })
        i = j + 2
    return records

def extract_all_records(pdf_bytes, today, progress_cb=None):
    all_records, errors = [], []
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", tmp_path, "-"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            errors.append(f"pdftotext error: {result.stderr[:200]}")
            return all_records, errors
        pages = result.stdout.split("\f")
        total = len(pages)
        for idx, page_text in enumerate(pages):
            try:
                all_records.extend(parse_records_from_page(page_text.split("\n"), today))
            except Exception as e:
                errors.append(f"Halaman {idx+1}: {e}")
            if progress_cb:
                progress_cb((idx + 1) / total)
    finally:
        os.unlink(tmp_path)
    return all_records, errors

def to_excel(df):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data Kendaraan")
        ws = writer.sheets["Data Kendaraan"]
        for col in ws.columns:
            max_len = max((len(str(c.value)) if c.value else 0) for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 80)
    buf.seek(0)
    return buf.read()


# ─── UI ──────────────────────────────────────────────────────────────────────

col_upload, col_info = st.columns([2, 1])

with col_upload:
    uploaded = st.file_uploader("Upload file PDF", type=["pdf"])

with col_info:
    st.markdown("""
    <div class="info-box">
    📋 <b>Format yang Didukung</b><br><br>
    Dokumen PDF dengan data terstruktur<br><br>
    ✓ Alamat 1 baris<br>
    ✓ Alamat panjang (wrap 2 baris)<br>
    ✓ Semua jenis kendaraan
    </div>
    """, unsafe_allow_html=True)
    today = st.date_input("Tanggal Referensi (Pajak Lewat)", value=date.today())

st.markdown("---")

if uploaded:
    st.markdown(f"**File:** `{uploaded.name}` · {uploaded.size/1024:.1f} KB")
    pdf_bytes = uploaded.read()

    with st.spinner("Memproses PDF..."):
        bar = st.progress(0)
        records, errors = extract_all_records(pdf_bytes, today, lambda v: bar.progress(min(v, 1.0)))
        bar.progress(1.0)

    if not records:
        st.error("❌ Tidak ada data yang berhasil di-parse. Pastikan format PDF sesuai.")
    else:
        df = pd.DataFrame(records)
        n_lewat = (df["Pajak Lewat"] == "Yes").sum()

        st.markdown("### Ringkasan")
        c1, c2, c3, c4, c5 = st.columns(5)
        stats = [
            (len(df),              "#4da6ff", "Total Record"),
            (df["Jenis Kendaraan"].nunique(), "#4da6ff", "Jenis Kendaraan"),
            (n_lewat,              "#ff6b6b", "Pajak Lewat"),
            (len(df)-n_lewat,      "#4ecb71", "Pajak Aktif"),
            (f"{n_lewat/len(df)*100:.1f}%", "#4da6ff", "% Lewat"),
        ]
        for col, (val, color, label) in zip([c1,c2,c3,c4,c5], stats):
            with col:
                st.markdown(f'<div class="stat-card"><div class="stat-number" style="color:{color}">{val}</div><div class="stat-label">{label}</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Filter & Preview")

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            f_jenis = st.multiselect("Jenis Kendaraan", sorted(df["Jenis Kendaraan"].unique()))
        with col_f2:
            f_warna = st.multiselect("Warna Plat", sorted(df["Warna Plat"].unique()))
        with col_f3:
            f_pajak = st.selectbox("Pajak Lewat", ["Semua", "Yes", "No"])

        dff = df.copy()
        if f_jenis: dff = dff[dff["Jenis Kendaraan"].isin(f_jenis)]
        if f_warna: dff = dff[dff["Warna Plat"].isin(f_warna)]
        if f_pajak != "Semua": dff = dff[dff["Pajak Lewat"] == f_pajak]

        st.caption(f"Menampilkan **{len(dff)}** dari **{len(df)}** record")
        st.dataframe(dff, use_container_width=True, height=420)

        if errors:
            with st.expander(f"⚠️ {len(errors)} error saat parsing"):
                for e in errors:
                    st.markdown(f'<div class="err-box">{e}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Download")
        col_dl1, col_dl2 = st.columns([1, 3])
        with col_dl1:
            fname = uploaded.name.replace(".pdf", "_converted.xlsx")
            st.download_button(
                "⬇️ Download Excel",
                data=to_excel(dff),
                file_name=fname,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        with col_dl2:
            st.caption(f"`{fname}` · {len(dff)} baris · {len(df.columns)} kolom")

else:
    st.markdown("""
    <div style="text-align:center;padding:3rem;color:#3a4a6b;">
        <div style="font-size:3rem;margin-bottom:1rem;">📄</div>
        <div style="font-size:1rem;font-family:'DM Mono',monospace;">Upload file PDF untuk memulai konversi</div>
    </div>
    """, unsafe_allow_html=True)