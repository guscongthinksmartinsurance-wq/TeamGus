import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from io import BytesIO

# --- 1. GIAO DIỆN DARK MODE & STYLE NÂNG CAO ---
st.set_page_config(page_title="Team G Performance Center", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #00D4FF !important; font-weight: 900 !important; font-size: 2.5rem !important; }
    
    /* Hiệu ứng thẻ Podium */
    .podium-card {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border-radius: 20px;
        padding: 25px;
        text-align: center;
        border: 1px solid #334155;
        transition: all 0.3s ease;
    }
    
    /* Làm nổi bật Hạng 1 */
    .rank-1 {
        border: 3px solid #ffd700 !important;
        box-shadow: 0 0 30px rgba(255, 215, 0, 0.3);
        transform: scale(1.05);
    }
    
    /* Tên nhân viên TRẮNG SÁNG & ĐẬM */
    .staff-name-highlight {
        color: #FFFFFF !important;
        font-size: 1.6rem !important;
        font-weight: 900 !important;
        text-transform: uppercase;
        margin: 10px 0;
        display: block;
        text-shadow: 2px 2px 8px rgba(0,0,0,0.8);
    }
    
    .rev-gold { color: #ffd700; font-size: 1.8rem; font-weight: bold; }
    .rev-blue { color: #00D4FF; font-size: 1.8rem; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HÀM ĐỌC FILE (GIỮ NGUYÊN) ---
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

# --- 3. MODULE CALL LOG (NỔI BẬT) ---
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
        
        st.subheader("📞 Chiến thần Telesale (Top 5)")
        # Sắp xếp hiển thị 2-1-3-4-5
        top_5 = stat.head(5).copy()
        if len(top_5) >= 3:
            order = [1, 0, 2, 3, 4]
            cols = st.columns(5)
            titles = ["🥈 HẠNG 2", "👑 HẠNG 1", "🥉 HẠNG 3", "🏅 HẠNG 4", "🏅 HẠNG 5"]
            for i, idx in enumerate(order):
                if idx < len(top_5):
                    row = top_5.iloc[idx]
                    is_top = (idx == 0)
                    with cols[i]:
                        st.markdown(f"""<div class="podium-card {'rank-1' if is_top else ''}">
                            <div style="color:{'#ffd700' if is_top else '#00D4FF'};font-weight:bold;">{titles[idx]}</div>
                            <span class="staff-name-highlight">{row['Nhân viên']}</span>
                            <div class="rev-blue">{row['Tổng cuộc gọi']}</div>
                            <div style="color:#8B949E;font-size:0.8rem;">CUỘC GỌI</div>
                        </div>""", unsafe_allow_html=True)
        st.markdown("---")
        st.dataframe(stat, use_container_width=True)
    except: st.error("Lỗi file Call Log.")

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
        st.title("🏆 Hall of Fame - Team G")
        lb = df.groupby(owner_c).agg({'REV':'sum', id_c:'nunique'}).sort_values('REV', ascending=False).reset_index()
        lb.columns = ['Thành viên', 'Doanh số', 'Hợp đồng']
        
        # Podium Display 2-1-3-4-5
        top_5 = lb.head(5).copy()
        order = [1, 0, 2, 3, 4]
        cols_v = st.columns(5)
        titles = ["🥈 HẠNG 2", "👑 VÔ ĐỊCH", "🥉 HẠNG 3", "🏅 HẠNG 4", "🏅 HẠNG 5"]
        
        for i, idx in enumerate(order):
            if idx < len(top_5):
                row = top_5.iloc[idx]
                is_top = (idx == 0)
                with cols_v[i]:
                    st.markdown(f"""<div class="podium-card {'rank-1' if is_top else ''}">
                        <div style="color:{'#ffd700' if is_top else '#8B949E'};font-weight:bold;">{titles[idx]}</div>
                        <span class="staff-name-highlight">{row['Thành viên']}</span>
                        <div class="rev-gold">${row['Doanh số']:,.0f}</div>
                        <div style="color:#00D4FF;font-weight:bold;">{row['Hợp đồng']} Hợp đồng</div>
                    </div>""", unsafe_allow_html=True)
        st.markdown("---")
        st.dataframe(lb.style.format({'Doanh số': '{:,.0f}'}), use_container_width=True)
        return

    # --- LOGIC COHORT GỐC ---
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
