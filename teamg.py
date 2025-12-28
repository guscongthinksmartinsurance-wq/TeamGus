import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from io import BytesIO

# --- 1. GIAO DIỆN ---
st.set_page_config(page_title="Team G Detailed Analysis", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #00D4FF !important; font-weight: 900 !important; }
    [data-testid="stChart"] { height: 380px !important; }
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
def process_team_g_final(file):
    df = smart_load(file)
    if df is None: return

    current_year = datetime.now().year
    cols = df.columns
    c_list = [" ".join(str(c).upper().split()) for c in cols]
    def get_c(keys):
        for i, c in enumerate(c_list):
            if all(k in c for k in keys): return cols[i]
        return None

    m_c, e_c, v_c, w_c, id_c, src_c, team_c = get_c(['TARGET', 'PREMIUM']), get_c(['THÁNG', 'NHẬN', 'FILE']), get_c(['THÁNG', 'NHẬN', 'LEAD']), get_c(['NĂM', 'NHẬN', 'LEAD']), get_c(['LEAD', 'ID']), get_c(['SOURCE']), get_c(['TEAM'])

    # 1. Lọc Team G
    df = df[df[team_c].astype(str).str.upper().str.contains('G', na=False)].copy()

    # 2. Phân loại Nguồn
    def classify_source(val):
        s = str(val).upper().replace(" ", "").replace(".", "")
        return 'COLD CALL' if 'CC' in s or 'COLDCALL' in s else 'FUNNEL'
    df['LOẠI_NGUỒN'] = df[src_c].apply(classify_source)

    # 3. Làm sạch tiền
    df['REV'] = df[m_c].apply(lambda v: float(re.sub(r'[^0-9.]', '', str(v))) if pd.notna(v) and re.sub(r'[^0-9.]', '', str(v)) != '' else 0.0)
    
    # 4. Logic Nhóm Lead (Xử lý riêng cho Cold Call)
    def assign_cohort_v2(row):
        if row['LOẠI_NGUỒN'] == 'COLD CALL':
            return "📦 NHÓM COLD CALL"
        try:
            if pd.isna(row[v_c]) or pd.isna(row[w_c]): return "❌ Thiếu ngày nhận Lead"
            y, m = int(float(row[w_c])), int(float(row[v_c]))
            return f"Funnel T{m:02d}/{y}" if y == current_year else f"Funnel Trước {current_year}"
        except: return "❌ Lỗi định dạng ngày"

    df['NHÓM_PHÂN_LOẠI'] = df.apply(assign_cohort_v2, axis=1)
    df['TH_CHOT_NUM'] = df[e_c].apply(lambda v: int(float(v)) if pd.notna(v) and 1 <= int(float(v)) <= 12 else None)

    # --- TẠO MA TRẬN ---
    def create_mtx(val_col, agg_func):
        mtx = df.pivot_table(index='NHÓM_PHÂN_LOẠI', columns='TH_CHOT_NUM', values=val_col, aggfunc=agg_func).fillna(0)
        mtx = mtx.reindex(columns=range(1, 13)).fillna(0)
        mtx.columns = [f"Tháng {int(c)}" for c in mtx.columns]
        # Sắp xếp để Cold Call nằm riêng biệt
        idx = sorted([i for i in mtx.index if "Funnel" in i]) + [i for i in mtx.index if "COLD CALL" in i] + [i for i in mtx.index if "❌" in i]
        return mtx.reindex(idx)

    matrix_rev = create_mtx('REV', 'sum')
    matrix_count = create_mtx(id_c, 'nunique')

    # --- HIỂN THỊ ---
    st.title(f"🚀 Team G Performance: Funnel & Cold Call ({current_year})")
    
    # Biểu đồ cột chồng
    chart_data = df.groupby(['TH_CHOT_NUM', 'LOẠI_NGUỒN'])['REV'].sum().unstack().reindex(range(1, 13)).fillna(0)
    chart_data.index = [f"Tháng {i:02d}" for i in range(1, 13)]
    st.bar_chart(chart_data)

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 TỔNG DOANH SỐ G", f"${df['REV'].sum():,.2f}")
    c2.metric("🎯 DOANH SỐ FUNNEL", f"${df[df['LOẠI_NGUỒN']=='FUNNEL']['REV'].sum():,.2f}")
    c3.metric("📞 DOANH SỐ COLD CALL", f"${df[df['LOẠI_NGUỒN']=='COLD CALL']['REV'].sum():,.2f}")

    tab1, tab2 = st.tabs(["💵 Ma trận Doanh số ($)", "🔢 Ma trận Số lượng (Hồ sơ)"])
    with tab1: st.dataframe(matrix_rev.style.format("${:,.0f}"), use_container_width=True)
    with tab2: st.dataframe(matrix_count.style.format("{:,.0f}"), use_container_width=True)

    # XUẤT EXCEL
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        matrix_rev.to_excel(writer, sheet_name='Revenue_Detail')
        matrix_count.to_excel(writer, sheet_name='Count_Detail')
        df.to_excel(writer, index=False, sheet_name='Clean_Data_TeamG')
    st.sidebar.download_button("📥 Tải Báo Cáo Team G", output.getvalue(), f"Team_G_Analysis_{current_year}.xlsx")

st.title("🛡️ Strategic Portal - Team G")
f = st.file_uploader("Nạp file Masterlife", type=['csv', 'xlsx'])
if f: process_team_g_final(f)
