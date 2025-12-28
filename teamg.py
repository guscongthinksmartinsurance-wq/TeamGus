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

# --- 3. XỬ LÝ DỮ LIỆU TÁCH BIỆT NGUỒN ---
def process_team_g_detail(file):
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

    # --- LỌC TEAM G & PHÂN LOẠI NGUỒN ---
    if team_c and src_c:
        # 1. Chỉ lấy Team G
        df = df[df[team_c].astype(str).str.upper().str.contains('G', na=False)].copy()
        
        # 2. Phân loại Funnel vs Cold Call (Dựa trên cột Source)
        def classify_source(val):
            s = str(val).upper().replace(" ", "").replace(".", "")
            if 'CC' in s or 'COLDCALL' in s:
                return 'COLD CALL'
            return 'FUNNEL'
        
        df['LOẠI_NGUỒN'] = df[src_c].apply(classify_source)
    else:
        st.error("❌ Thiếu cột 'Team' hoặc 'Source'.")
        return

    # Làm sạch tiền
    df['REV'] = df[m_c].apply(lambda v: float(re.sub(r'[^0-9.]', '', str(v))) if pd.notna(v) and re.sub(r'[^0-9.]', '', str(v)) != '' else 0.0)
    
    # Nhóm Lead & Tháng chốt
    df['NHÓM_LEAD'] = df.apply(lambda r: f"Lead T{int(float(r[v_c])):02d}/{int(float(r[w_c]))}" if pd.notna(r[v_c]) and int(float(r[w_c])) == current_year else f"Trước năm {current_year}", axis=1)
    df['TH_CHOT_NUM'] = df[e_c].apply(lambda v: int(float(v)) if pd.notna(v) and 1 <= int(float(v)) <= 12 else None)

    # --- TẠO MA TRẬN PHÂN CẤP (NGUỒN TRONG NHÓM LEAD) ---
    def create_detail_matrix(val_col, agg_func):
        mtx = df.pivot_table(index=['NHÓM_LEAD', 'LOẠI_NGUỒN'], columns='TH_CHOT_NUM', values=val_col, aggfunc=agg_func).fillna(0)
        mtx = mtx.reindex(columns=range(1, 13)).fillna(0)
        mtx.columns = [f"Tháng {int(c)}" for c in mtx.columns]
        return mtx

    matrix_rev = create_detail_matrix('REV', 'sum')
    matrix_count = create_detail_matrix(id_c, 'nunique')

    # --- HIỂN THỊ DASHBOARD ---
    st.title(f"📊 Team G Performance Detail - {current_year}")

    # Biểu đồ cột chồng (Stacked Bar) thể hiện đóng góp Funnel vs Cold Call
    st.subheader("📈 Tỷ trọng đóng góp Doanh số (Funnel vs Cold Call)")
    chart_data = df.groupby(['TH_CHOT_NUM', 'LOẠI_NGUỒN'])['REV'].sum().unstack().reindex(range(1, 13)).fillna(0)
    chart_data.index = [f"Tháng {i:02d}" for i in range(1, 13)]
    st.bar_chart(chart_data)

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 TỔNG DOANH SỐ G", f"${df['REV'].sum():,.2f}")
    c2.metric("🎯 FUNNEL CHỐT", f"${df[df['LOẠI_NGUỒN']=='FUNNEL']['REV'].sum():,.2f}")
    c3.metric("📞 COLD CALL CHỐT", f"${df[df['LOẠI_NGUỒN']=='COLD CALL']['REV'].sum():,.2f}")

    st.markdown("---")
    t1, t2 = st.tabs(["💵 Chi tiết Doanh số ($)", "🔢 Chi tiết Số lượng (Hồ sơ)"])
    
    with t1:
        st.write("Bảng phân tích doanh số tách bạch Funnel và Cold Call:")
        st.dataframe(matrix_rev.style.format("${:,.0f}"), use_container_width=True)
    with t2:
        st.write("Bảng phân tích số lượng hồ sơ chốt:")
        st.dataframe(matrix_count.style.format("{:,.0f}"), use_container_width=True)

    # XUẤT EXCEL
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        matrix_rev.to_excel(writer, sheet_name='Revenue_Detail')
        matrix_count.to_excel(writer, sheet_name='Count_Detail')
        df.to_excel(writer, index=False, sheet_name='Raw_Data_TeamG')

    st.sidebar.download_button("📥 Tải Báo Cáo Chi Tiết Team G", output.getvalue(), f"Team_G_Detail_{current_year}.xlsx")

st.title("🛡️ Strategic Portal - Team G")
f = st.file_uploader("Nạp file Masterlife", type=['csv', 'xlsx'])
if f: process_team_g_detail(f)
