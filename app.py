import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
import json
import re

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Laporan QPR 360° (AI Powered)", layout="wide", page_icon="🎙️")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #1a1a1a; background-color: #f3f4f6; }
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
    .css-card { background-color: #ffffff; padding: 24px; border-radius: 16px; border: 1px solid #e5e7eb; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); margin-bottom: 24px; }
    .header-box { background: linear-gradient(135deg, #4c1d95 0%, #7c3aed 100%); color: white; padding: 35px; border-radius: 16px; text-align: center; margin-bottom: 30px; box-shadow: 0 10px 20px -5px rgba(124, 58, 237, 0.3); }
    .score-container { text-align: center; padding: 20px; border-bottom: 2px dashed #f3f4f6; margin-bottom: 20px; }
    .score-val { font-size: 4rem; font-weight: 800; color: #6d28d9; line-height: 1; }
    .score-label { font-size: 0.85rem; font-weight: 700; color: #4b5563; text-transform: uppercase; margin-top: 10px; letter-spacing: 1.5px; }
    .narrative-box { background-color: #fdf4ff; border-left: 6px solid #d946ef; padding: 30px; border-radius: 12px; margin-top: 20px; margin-bottom: 25px; }
    .styled-table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 0.95rem; border-radius: 10px; overflow: hidden; }
    .styled-table th { background-color: #5b21b6; color: #ffffff; font-weight: 600; padding: 14px 16px; text-align: left; }
    .styled-table td { padding: 16px; border-bottom: 1px solid #f3f4f6; vertical-align: top; color: #374151; line-height: 1.6; word-wrap: break-word; }
    .col-catatan { width: 50%; text-align: justify; }
    .styled-table tbody tr:hover { background-color: #f9fafb; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: AI CONFIG ---
with st.sidebar:
    st.header("🧠 Pengaturan AI")
    api_key = st.text_input("Google Gemini API Key:", value="AIzaSyA6Zhv-KKZ__KRcawR93jblsmljZ6bUZ_A", type="password")
    if api_key:
        try:
            genai.configure(api_key=api_key)
            st.success("✅ AI Siap Menilai!")
        except Exception as e:
            st.error(f"Koneksi Gagal: {e}")
    else:
        st.warning("Masukkan API Key.")

# --- FUNGSI AI CERDAS (Plotting & Scoring) ---
def analyze_with_ai(text_input, role_name):
    # Prompt Teknikal untuk memaksa AI memploting dan menilai
    prompt = f"""
    Kamu adalah HR Evaluator Profesional. Tugasmu adalah menganalisis transkrip ucapan user tentang seorang {role_name}.
    
    INPUT SUARA/TEKS: "{text_input}"

    TUGAS UTAMA:
    1. **PLOTTING**: Baca teks input, lalu pilah kalimat mana yang masuk kategori Kinerja, Inisiatif, Kolaborasi, Partisipasi, atau Waktu.
    2. **SCORING**: Berikan nilai (0-100) berdasarkan sentimen kalimat tersebut.
       - Kata positif ("bagus", "cepat", "rajin") = Skor Tinggi (80-100).
       - Kata netral ("biasa", "cukup") = Skor Sedang (70-79).
       - Kata negatif ("telat", "malas", "kurang") = Skor Rendah (<70).
       - Jika tidak ada info tentang kategori tertentu, beri nilai 75 (Netral).

    OUTPUT WAJIB JSON MURNI (Tanpa Markdown):
    {{
        "scores": {{
            "Kinerja": 0, "Inisiatif": 0, "Kolaborasi": 0, "Partisipasi": 0, "Waktu": 0
        }},
        "plotting_evidence": {{
            "Kinerja": "Kutip kalimat user yang berhubungan dengan kinerja...",
            "Inisiatif": "Kutip kalimat user yang berhubungan dengan inisiatif...",
            "Kolaborasi": "Kutip kalimat user yang berhubungan dengan kolaborasi...",
            "Partisipasi": "Kutip kalimat user yang berhubungan dengan partisipasi...",
            "Waktu": "Kutip kalimat user yang berhubungan dengan waktu..."
        }},
        "summary": "Buat rangkuman narasi profesional 1 paragraf panjang.",
        "recommendation": "Saran singkat."
    }}
    """
    
    # Logic Fallback Model (Anti Error 404)
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
    except:
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
        except Exception as e:
            return None, f"Error AI: {e}"

    # Parsing JSON
    try:
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        return data, None
    except:
        return None, "Gagal membaca format data dari AI."

# --- FUNGSI TRANSKRIPSI ---
def transcribe_audio(audio_bytes):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([
            "Transkrip audio ini persis seperti apa yang diucapkan (verbatim). Bahasa Indonesia.", 
            {"mime_type": "audio/webm", "data": audio_bytes}
        ])
        return response.text
    except:
        return "Gagal transkripsi (Model audio tidak tersedia). Silakan ketik manual."

# --- UI HEADER ---
st.markdown('<div class="header-box"><h1>QPR Report Dashboard 360°</h1><p>Performance Evaluation System</p></div>', unsafe_allow_html=True)

# --- TABS ---
tab_anggota, tab_leader = st.tabs(["👥 Evaluasi Anggota (Excel)", "🎙️ Evaluasi Ketua & Wakil (Voice AI)"])

# === TAB 1: EXCEL (Fitur Lama) ===
with tab_anggota:
    uploaded_file = st.file_uploader("Upload File Excel QPR II (.xlsx)", type=['xlsx'])
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file, sheet_name="Recap Point Penilaian", header=1)
            st.info("Fitur Excel aktif. Pilih nama anggota di sidebar (jika ada).")
        except: st.error("Format Excel tidak sesuai.")

# === TAB 2: AI VOICE PLOTTING (FITUR UTAMA) ===
with tab_leader:
    st.write("### 🎙️ Evaluasi Ketua & Wakil (AI Scoring & Plotting)")
    st.caption("Ucapkan penilaian Anda secara bebas. AI akan mendengarkan, memilah kategori (plotting), dan memberikan skor otomatis.")

    c_input, c_result = st.columns([1, 1.5])

    # STATE MANAGEMENT
    if 'voice_text' not in st.session_state: st.session_state.voice_text = ""

    with c_input:
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        target_name = st.text_input("Nama Yang Dinilai:", "Budi Santoso")
        role = st.selectbox("Jabatan:", ["Ketua Divisi", "Wakil Ketua"])
        
        st.markdown("---")
        st.write("**1. Rekam Suara Anda:**")
        audio = mic_recorder(start_prompt="🎤 Mulai Bicara", stop_prompt="⏹️ Selesai", key="recorder")
        
        if audio:
            with st.spinner("👂 Mendengarkan..."):
                transkrip = transcribe_audio(audio['bytes'])
                st.session_state.voice_text = transkrip
                st.success("Suara terekam!")

        st.write("**2. Hasil Transkrip (Bisa diedit):**")
        user_text = st.text_area("Teks:", value=st.session_state.voice_text, height=150, placeholder="Contoh: Kinerjanya bagus banget target tercapai, tapi sayangnya sering telat pas meeting...")
        
        # Update state jika user edit manual
        if user_text != st.session_state.voice_text: st.session_state.voice_text = user_text

        analyze = st.button("🚀 Analisis & Beri Skor Otomatis", type="primary")
        st.markdown('</div>', unsafe_allow_html=True)

    with c_result:
        if analyze and user_text:
            with st.spinner("🤖 AI sedang mem-plotting kategori & menghitung skor..."):
                data_ai, error = analyze_with_ai(user_text, role)
                
                if error:
                    st.error(error)
                else:
                    # AMBIL DATA DARI AI
                    scores = data_ai['scores']
                    evidence = data_ai['plotting_evidence']
                    
                    # Hitung Total (Bobot: Kinerja 30, Inisiatif 15, Kolab 20, Partisipasi 20, Waktu 15)
                    final_score = (scores['Kinerja']*0.3) + (scores['Inisiatif']*0.15) + (scores['Kolaborasi']*0.2) + (scores['Partisipasi']*0.2) + (scores['Waktu']*0.15)

                    # TAMPILKAN HASIL
                    st.markdown(f"### 📊 Hasil Penilaian AI: {target_name}")
                    
                    # Score Card
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.markdown(f'<div class="score-container"><div class="score-val">{final_score:.1f}</div><div class="score-label">AI Score</div></div>', unsafe_allow_html=True)
                    with c2:
                        fig = go.Figure(data=go.Scatterpolar(r=list(scores.values()), theta=list(scores.keys()), fill='toself', line_color='#7c3aed'))
                        fig.update_layout(height=220, margin=dict(t=20, b=20, l=20, r=20))
                        st.plotly_chart(fig, use_container_width=True)

                    # Tabel Plotting (BUKTI)
                    st.markdown("#### 📝 Plotting Suara ke Kategori")
                    rows = ""
                    for k, v in scores.items():
                        # Warna skor
                        color = "#16a34a" if v >= 80 else "#ca8a04" if v >= 70 else "#dc2626"
                        # Ambil bukti teks
                        bukti = evidence.get(k, "-")
                        rows += f"<tr><td><b>{k}</b></td><td style='text-align:center; font-weight:bold; color:{color}'>{v}</td><td class='col-catatan'><i>\"{bukti}\"</i></td></tr>"
                    
                    st.markdown(f"""
                    <table class="styled-table">
                        <thead><tr><th>Aspek</th><th>Skor AI</th><th>Bukti dari Ucapan Anda (Plotting)</th></tr></thead>
                        <tbody>{rows}</tbody>
                    </table>
                    """, unsafe_allow_html=True)

                    # Narasi Akhir
                    st.markdown("#### 📋 Kesimpulan Akhir")
                    st.markdown(f'<div class="narrative-box">{data_ai["summary"]}</div>', unsafe_allow_html=True)
                    st.success(f"💡 Rekomendasi: {data_ai['recommendation']}")
