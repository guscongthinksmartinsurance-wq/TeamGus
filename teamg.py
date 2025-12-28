import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from io import BytesIO

# --- 1. GIAO DIỆN VINH DANH SANG TRỌNG ---
st.set_page_config(page_title="Team G - Hall of Fame", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #FFFFFF; }
    /* Style cho các ô vinh danh */
    .award-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #38bdf8;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.2);
    }
    .award-rank { color: #ffd700; font-size: 1.2rem; font-weight: bold; }
    .award-name { color: #ffffff; font-size: 1.5rem; font-weight: bold; margin: 10px 0; }
    .award-value { color: #00D4FF; font-size: 1.3rem; font-family: 'Courier New', monospace; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HÀM ĐỌC FILE ---
def smart_load(file):
    try:
        if file.name.endswith(('.xlsx', '.xls')):
            raw_df = pd.read_excel(file, header=None)
        else:
            file.seek(0)
            raw_df = pd.read_csv(file, sep=None, engine='python', header=None, encoding='utf-8', errors='ignore')
        header_row = 0
        for i, row in raw_df.head(20).iterrows():
            if 'TARGET PREMIUM' in " ".join(str(val).upper() for val in row):
                header_row = i
                break
        file.seek(0)
        return pd.read_excel(file, skiprows=header_row) if file.name.endswith(('.xlsx', '.xls')) else pd.read_csv(file, sep=None, engine='python', skiprows=header_row, encoding='utf-8', errors='ignore')
    except: return None

# --- 3. ENGINE PHÂN TÍCH & VINH DANH ---
def process_honors(file):
    df = smart_load(file)
    if df is None: return

    current_year = datetime.now().year
    cols = df.columns
    c_list = [" ".join(str(c).upper().split()) for c in cols]
    def get_c(keys):
        for i, c in enumerate(c_list):
            if all(k in c for k in keys): return cols[i]
        return None

    m_c, team_c, owner_c = get_c(['TARGET', 'PREMIUM']), get_c(['TEAM']), get_c(['OWNER'])
    e_c, v_c, w_c, id_c, src_c = get_c(['THÁNG', 'NHẬN', 'FILE']), get_c(['THÁNG', 'NHẬN', 'LEAD']), get_c(['NĂM', 'NHẬN', 'LEAD']), get_c(['LEAD', 'ID']), get_c(['SOURCE'])

    if not all([team_c, owner_c, m_c]):
        st.error("❌ Thiếu cột Team, Owner hoặc Target Premium.")
        return

    # Lọc Team G
    df_g = df[df[team_c].astype(str).str.upper().str.contains('G', na=False)].copy()
    
    # Làm sạch tiền
    df_g['REV'] = df_g[m_c].apply(lambda v: float(re.sub(r'[^0-9.]', '', str(v))) if pd.notna(v) and re.sub(r'[^0-9.]', '', str(v)) != '' else 0.0)

    # --- PHẦN 1: VINH DANH TOP 5 ---
    st.title("🏆 TEAM G - HALL OF FAME 2025")
    st.subheader("Vinh danh 5 cá nhân xuất sắc nhất năm")
    
    leaderboard = df_g.groupby(owner_c)['REV'].sum().sort_values(ascending=False).reset_index()
    top_5 = leaderboard.head(5)

    cols_award = st.columns(5)
    icons = ["🥇", "🥈", "🥉", "🏅", "🏅"]
    
    for i, (idx, row) in enumerate(top_5.iterrows()):
        with cols_award[i]:
            st.markdown(f"""
                <div class="award-card">
                    <div class="award-rank">{icons[i]} Hạng {i+1}</div>
                    <div class="award-name">{row[owner_c]}</div>
                    <div class="award-value">${row['REV']:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)

    # --- PHẦN 2: PHÂN TÍCH CHI TIẾT COHORT (NHƯ CŨ) ---
    st.markdown("---")
    st.subheader("📊 Bảng xếp hạng chi tiết toàn Team G")
    st.dataframe(leaderboard.rename(columns={owner_c: 'Thành viên', 'REV': 'Tổng doanh số ($)'}).style.format({'Tổng doanh số ($)': '{:,.0f}'}), use_container_width=True)

    # Logic xử lý Cohort & Tách nguồn (Funnel/Cold Call) để khớp yêu cầu trước của bạn
    def classify_source(val):
        s = str(val).upper().replace(" ", "").replace(".", "")
        return 'COLD CALL' if 'CC' in s or 'COLDCALL' in s else 'FUNNEL'
    df_g['LOẠI_NGUỒN'] = df_g[src_c].apply(classify_source) if src_c else 'N/A'

    def assign_cohort_v2(row):
        if row['LOẠI_NGUỒN'] == 'COLD CALL': return "📦 NHÓM COLD CALL"
        try:
            y, m = int(float(row[w_c])), int(float(row[v_c]))
            return f"Funnel T{m:02d}/{y}" if y == current_year else f"Funnel Trước {current_year}"
        except: return "❌ Thiếu ngày nhận Lead"

    df_g['NHÓM_PHÂN_LOẠI'] = df_g.apply(assign_cohort_v2, axis=1)
    df_g['TH_CHOT_NUM'] = df_g[e_c].apply(lambda v: int(float(v)) if pd.notna(v) and 1 <= int(float(v)) <= 12 else None)

    matrix_rev = df_g.pivot_table(index='NHÓM_PHÂN_LOẠI', columns='TH_CHOT_NUM', values='REV', aggfunc='sum').fillna(0)
    matrix_rev = matrix_rev.reindex(columns=range(1, 13)).fillna(0)
    matrix_rev.columns = [f"Tháng {int(c)}" for c in matrix_rev.columns]

    st.markdown("---")
    st.subheader("💵 Ma trận doanh số chi tiết theo nguồn")
    st.dataframe(matrix_rev.style.format("${:,.0f}"), use_container_width=True)

    # XUẤT EXCEL
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        leaderboard.to_excel(writer, sheet_name='Leaderboard_Vinh_Danh', index=False)
        matrix_rev.to_excel(writer, sheet_name='Revenue_Cohort_TeamG')
        df_g.to_excel(writer, index=False, sheet_name='Data_Source_TeamG')
    st.sidebar.download_button("📥 Tải Báo Cáo Vinh Danh & Doanh Số", output.getvalue(), f"Team_G_Vinh_Danh_{current_year}.xlsx")

st.sidebar.title("🛡️ Team G Management")
f = st.file_uploader("Nạp file Masterlife để vinh danh", type=['csv', 'xlsx'])
if f: process_honors(f)
