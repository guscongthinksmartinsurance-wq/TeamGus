import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from io import BytesIO

# --- 1. GIAO DIỆN DARK MODE ---
st.set_page_config(page_title="Team G Performance Center", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #00D4FF !important; font-weight: 900 !important; font-size: 2.5rem !important; }
    [data-testid="stMetricLabel"] p { color: #8B949E !important; font-size: 0.9rem !important; letter-spacing: 1px; }
    [data-testid="stChart"] { height: 350px !important; }
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

# --- 3. ENGINE PHÂN TÍCH TEAM G ---
def process_team_g(file):
    df = smart_load(file)
    if df is None: return

    current_year = datetime.now().year
    cols = df.columns
    c_list = [" ".join(str(c).upper().split()) for c in cols]
    
    def get_c(keys):
        for i, c in enumerate(c_list):
            if all(k in c for k in keys): return cols[i]
        return None

    m_c = get_c(['TARGET', 'PREMIUM'])
    e_c = get_c(['THÁNG', 'NHẬN', 'FILE'])
    v_c = get_c(['THÁNG', 'NHẬN', 'LEAD'])
    w_c = get_c(['NĂM', 'NHẬN', 'LEAD'])
    id_c = get_c(['LEAD', 'ID'])
    team_c = get_c(['TEAM']) # Dò cột Team (Cột F)

    # --- LOGIC LỌC TEAM G ---
    if team_c:
        # Giữ lại các dòng có chứa chữ "G" trong cột Team
        df = df[df[team_c].astype(str).str.upper().str.contains('G', na=False)]
    else:
        st.error("❌ Không tìm thấy cột 'Team'. Vui lòng kiểm tra lại file.")
        return

    # Làm sạch tiền
    df['REV'] = df[m_c].apply(lambda v: float(re.sub(r'[^0-9.]', '', str(v))) if pd.notna(v) and re.sub(r'[^0-9.]', '', str(v)) != '' else 0.0)
    
    # Phân nhóm Lead
    def assign_cohort(row):
        try:
            y, m = int(float(row[w_c])), int(float(row[v_c]))
            return f"Lead T{m:02d}/{y}" if y == current_year else f"Trước năm {current_year}"
        except: return "❌ Thiếu thông tin Lead"

    df['NHÓM_LEAD'] = df.apply(assign_cohort, axis=1)
    df['TH_CHOT_NUM'] = df[e_c].apply(lambda v: int(float(v)) if pd.notna(v) and 1 <= int(float(v)) <= 12 else None)

    # --- DỮ LIỆU BIỂU ĐỒ ---
    chart_data = df.groupby('TH_CHOT_NUM')['REV'].sum().reindex(range(1, 13)).fillna(0)
    chart_df = pd.DataFrame({'Tháng': [f"Tháng {i:02d}" for i in range(1, 13)], 'Doanh Số G': chart_data.values}).set_index('Tháng')

    # Ma trận Doanh số & Số lượng
    matrix_rev = df.pivot_table(index='NHÓM_LEAD', columns='TH_CHOT_NUM', values='REV', aggfunc='sum').fillna(0)
    matrix_count = df.pivot_table(index='NHÓM_LEAD', columns='TH_CHOT_NUM', values=id_c, aggfunc='nunique').fillna(0)

    def sort_mtx(mtx):
        mtx = mtx.reindex(columns=range(1, 13)).fillna(0)
        mtx.columns = [f"Tháng {int(c)}" for c in mtx.columns]
        idx_current = sorted([i for i in mtx.index if f"/{current_year}" in i])
        final_idx = ([f"Trước năm {current_year}"] if f"Trước năm {current_year}" in mtx.index else []) + idx_current + ([i for i in mtx.index if "❌" in i])
        return mtx.reindex(final_idx)

    matrix_rev = sort_mtx(matrix_rev)
    matrix_count = sort_mtx(matrix_count)

    # --- HIỂN THỊ DASHBOARD ---
    st.title(f"📊 Team G Strategic Report - {current_year}")
    st.area_chart(chart_df, color="#00FF7F") # Đổi sang màu xanh lá cho Team G

    col1, col2 = st.columns(2)
    col1.metric("💰 TỔNG DOANH THU TEAM G", f"${df['REV'].sum():,.2f}")
    col2.metric("📋 TỔNG HỢP ĐỒNG TEAM G", f"{df[id_c].nunique():,}")

    t1, t2 = st.tabs(["💵 Doanh số ($)", "🔢 Số lượng hồ sơ"])
    with t1: st.dataframe(matrix_rev.style.format("${:,.0f}"), use_container_width=True)
    with t2: st.dataframe(matrix_count.style.format("{:,.0f}"), use_container_width=True)

    # --- XUẤT EXCEL ĐA SHEET ---
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        matrix_rev.to_excel(writer, sheet_name='TeamG_Revenue')
        ws1 = writer.sheets['TeamG_Revenue']
        ws1.conditional_format(1, 1, len(matrix_rev), 12, {'type': '3_color_scale', 'min_color': "#F0FFF0", 'mid_color': "#90EE90", 'max_color': "#006400"})
        
        matrix_count.to_excel(writer, sheet_name='TeamG_Count')
        ws2 = writer.sheets['TeamG_Count']
        ws2.conditional_format(1, 1, len(matrix_count), 12, {'type': '3_color_scale', 'min_color': "#FFF5EE", 'mid_color': "#FDAE6B", 'max_color': "#7F2704"})
        
        df.to_excel(writer, index=False, sheet_name='TeamG_Data_Detail')

    st.sidebar.markdown("---")
    st.sidebar.download_button(f"📥 Tải Báo Cáo Team G ({current_year})", output.getvalue(), f"Team_G_Report_{current_year}.xlsx")

st.title("🛡️ Team G Management Portal")
f = st.file_uploader("Nạp file Masterlife để lọc Team G", type=['csv', 'xlsx'])
if f: process_team_g(f)
