import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from io import BytesIO

# --- 1. GIAO DIỆN DARK MODE & STYLE NỔI BẬT ---
st.set_page_config(page_title="Team G Performance Center", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #00D4FF !important; font-weight: 900 !important; font-size: 2.5rem !important; }
    
    /* STYLE CHO THẺ VINH DANH TOP 5 */
    .award-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 2px solid #ffd700; /* Viền vàng dày hơn */
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 10px 20px rgba(255, 215, 0, 0.2); /* Đổ bóng vàng */
        transition: transform 0.3s;
    }
    .award-card:hover { transform: scale(1.05); }
    
    .rank-label { color: #ffd700; font-size: 0.9rem; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    .staff-name { color: #FFFFFF !important; font-size: 1.4rem !important; font-weight: 800 !important; margin: 10px 0; display: block; }
    .revenue-val { color: #ffd700; font-size: 1.6rem; font-weight: bold; }
    .contract-val { color: #8B949E; font-size: 0.85rem; }
    
    /* Style cho thẻ Call Log */
    .call-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 2px solid #00D4FF;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 10px 20px rgba(0, 212, 255, 0.2);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HÀM ĐỌC FILE (GIỮ NGUYÊN BẢN CHUẨN) ---
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

# --- 3. MODULE CALL LOG (SỬA LỖI HIỂN THỊ) ---
def process_call_log(file):
    try:
        for enc in ['utf-8-sig', 'latin1', 'cp1252']:
            try:
                file.seek(0)
                df_c = pd.read_csv(file, encoding=enc, sep=None, engine='python', on_bad_lines='skip')
                break
            except: continue
        
        df_c['Call_Ref'] = df_c['From'].fillna(df_c['Extension'])
        def get_name(ext):
            ext = str(ext)
            return ext.split('-')[-1].strip() if '-' in ext else (ext if ext.lower()!='nan' else "Ẩn danh")
        
        df_c['Staff'] = df_c['Extension'].apply(get_name)
        stat = df_c.groupby('Staff')['Call_Ref'].count().sort_values(ascending=False).reset_index()
        stat.columns = ['Nhân viên', 'Tổng cuộc gọi']
        
        st.subheader("📞 Top 5 Chiến thần Telesale")
        c = st.columns(5)
        for i, (idx, row) in enumerate(stat.head(5).iterrows()):
            with c[i]:
                st.markdown(f"""
                    <div class='call-card'>
                        <div style='color:#00D4FF; font-weight:bold;'>HẠNG {i+1}</div>
                        <span class='staff-name'>{row['Nhân viên']}</span>
                        <div style='color:#00D4FF; font-size:1.8rem; font-weight:bold;'>{row['Tổng cuộc gọi']}</div>
                        <div style='color:#8B949E; font-size:0.8rem;'>Cuộc gọi</div>
                    </div>
                """, unsafe_allow_html=True)
        st.markdown("---")
        st.dataframe(stat, use_container_width=True)
    except: st.error("Lỗi đọc file Call Log. Vui lòng kiểm tra lại định dạng file.")

# --- 4. ENGINE PHÂN TÍCH TEAM G ---
def process_team_g(file, show_vinh_danh=False):
    df = smart_load(file)
    if df is None: return

    current_year = datetime.now().year
    cols = df.columns
    c_list = [" ".join(str(c).upper().split()) for c in cols]
    def get_c(keys):
        for i, c in enumerate(c_list):
            if all(k in c for k in keys): return cols[i]
        return None

    m_c, e_c, v_c, w_c, id_c, team_c, owner_c = get_c(['TARGET','PREMIUM']), get_c(['THÁNG','FILE']), get_c(['THÁNG','LEAD']), get_c(['NĂM','LEAD']), get_c(['LEAD','ID']), get_c(['TEAM']), get_c(['OWNER'])

    if team_c:
        df = df[df[team_c].astype(str).str.upper().str.contains('G', na=False)]
    
    df['REV'] = df[m_c].apply(lambda v: float(re.sub(r'[^0-9.]', '', str(v))) if pd.notna(v) and re.sub(r'[^0-9.]', '', str(v)) != '' else 0.0)

    if show_vinh_danh:
        st.title("🏆 Vinh danh Doanh số Team G")
        lb = df.groupby(owner_c).agg({'REV':'sum', id_c:'nunique'}).sort_values('REV', ascending=False).reset_index()
        lb.columns = ['Thành viên', 'Doanh số', 'Hợp đồng']
        
        cols_v = st.columns(5)
        medals = ["🥇 HẠNG 1", "🥈 HẠNG 2", "🥉 HẠNG 3", "🏅 HẠNG 4", "🏅 HẠNG 5"]
        for i, (idx, row) in enumerate(lb.head(5).iterrows()):
            with cols_v[i]:
                st.markdown(f"""
                    <div class='award-card'>
                        <div class='rank-label'>{medals[i]}</div>
                        <span class='staff-name'>{row['Thành viên']}</span>
                        <div class='revenue-val'>${row['Doanh số']:,.0f}</div>
                        <div class='contract-val'>{row['Hợp đồng']} Hợp đồng</div>
                    </div>
                """, unsafe_allow_html=True)
        st.markdown("---")
        st.dataframe(lb.style.format({'Doanh số': '{:,.0f}'}), use_container_width=True)
        return

    # --- LOGIC COHORT GỐC CỦA BẠN ---
    def assign_cohort(row):
        try:
            y, m = int(float(row[w_c])), int(float(row[v_c]))
            return f"Lead T{m:02d}/{y}" if y == current_year else f"Trước năm {current_year}"
        except: return "❌ Thiếu thông tin Lead"

    df['NHÓM_LEAD'] = df.apply(assign_cohort, axis=1)
    df['TH_CHOT_NUM'] = df[e_c].apply(lambda v: int(float(v)) if pd.notna(v) and 1 <= int(float(v)) <= 12 else None)
    
    chart_data = df.groupby('TH_CHOT_NUM')['REV'].sum().reindex(range(1, 13)).fillna(0)
    chart_df = pd.DataFrame({'Tháng': [f"Tháng {i:02d}" for i in range(1, 13)], 'Doanh Số G': chart_data.values}).set_index('Tháng')

    matrix_rev = df.pivot_table(index='NHÓM_LEAD', columns='TH_CHOT_NUM', values='REV', aggfunc='sum').fillna(0)
    matrix_count = df.pivot_table(index='NHÓM_LEAD', columns='TH_CHOT_NUM', values=id_c, aggfunc='nunique').fillna(0)

    def sort_mtx(mtx):
        mtx = mtx.reindex(columns=range(1, 13)).fillna(0)
        mtx.columns = [f"Tháng {int(c)}" for c in mtx.columns]
        idx_current = sorted([i for i in mtx.index if f"/{current_year}" in i])
        final_idx = ([f"Trước năm {current_year}"] if f"Trước năm {current_year}" in mtx.index else []) + idx_current + ([i for i in mtx.index if "❌" in i])
        return mtx.reindex(final_idx)

    st.title(f"📊 Team G Strategic Report - {current_year}")
    st.area_chart(chart_df, color="#00FF7F")
    t1, t2 = st.tabs(["💵 Doanh số ($)", "🔢 Số lượng hồ sơ"])
    with t1: st.dataframe(sort_mtx(matrix_rev).style.format("${:,.0f}"), use_container_width=True)
    with t2: st.dataframe(sort_mtx(matrix_count).style.format("{:,.0f}"), use_container_width=True)

# --- 5. ĐIỀU HƯỚNG ---
menu = st.sidebar.radio("Menu Team G:", ["📊 Phân tích Cohort", "🏆 Vinh danh Doanh số", "📞 Phân tích Call Log"])
f = st.sidebar.file_uploader("Nạp file dữ liệu", type=['csv', 'xlsx'])

if f:
    if menu == "📊 Phân tích Cohort": process_team_g(f, False)
    elif menu == "🏆 Vinh danh Doanh số": process_team_g(f, True)
    elif menu == "📞 Phân tích Call Log": process_call_log(f)
