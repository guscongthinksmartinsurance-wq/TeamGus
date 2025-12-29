import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from io import BytesIO

# --- 1. GIAO DIỆN DARK MODE & STYLE CAO CẤP ---
st.set_page_config(page_title="Team G Performance Center", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #00FF7F !important; font-weight: 900 !important; font-size: 2.5rem !important; }
    
    .podium-card {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border-radius: 20px; padding: 25px; text-align: center;
        border: 1px solid #334155; transition: all 0.3s ease;
    }
    .rank-1-glow { border: 3px solid #ffd700 !important; box-shadow: 0 0 30px rgba(255, 215, 0, 0.4); transform: scale(1.08); }
    .rank-call-glow { border: 3px solid #00D4FF !important; box-shadow: 0 0 30px rgba(0, 212, 255, 0.4); transform: scale(1.08); }
    
    .staff-name-highlight {
        color: #FFFFFF !important; font-size: 1.5rem !important;
        font-weight: 900 !important; text-transform: uppercase;
        display: block; text-shadow: 2px 2px 8px rgba(0,0,0,0.8);
        margin-bottom: 5px;
    }
    .rev-val { font-size: 1.8rem; font-weight: bold; }
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
                header_row = i; break
        file.seek(0)
        return pd.read_excel(file, skiprows=header_row) if file.name.endswith(('.xlsx', '.xls')) else pd.read_csv(file, sep=None, engine='python', skiprows=header_row, encoding='utf-8', errors='ignore')
    except: return None

# --- 3. MODULE CALL LOG (Vinh danh 5 người rực rỡ & STT từ 1) ---
def process_call_log(file):
    st.title("📞 Call Performance Analytics")
    try:
        df_c = pd.read_csv(file, encoding='utf-8-sig', sep=None, engine='python', on_bad_lines='skip')
        df_c['Ref'] = df_c['From'].fillna(df_c['Extension'])
        df_c['Staff'] = df_c['Extension'].apply(lambda x: str(x).split('-')[-1].strip() if '-' in str(x) else (str(x) if str(x)!='nan' else "Ẩn danh"))
        
        stat = df_c.groupby('Staff')['Ref'].count().sort_values(ascending=False).reset_index()
        stat.columns = ['Nhân viên', 'Tổng cuộc gọi']
        
        st.subheader("🏆 Top 5 Chiến thần Telesale")
        cols = st.columns(5)
        # Sắp xếp bục 4-2-1-3-5
        d_map = [{'i':3,'t':"🏅 Hạng 4"}, {'i':1,'t':"🥈 Hạng 2"}, {'i':0,'t':"👑 VÔ ĐỊCH"}, {'i':2,'t':"🥉 Hạng 3"}, {'i':4,'t':"🏅 Hạng 5"}]
        
        for i, item in enumerate(d_map):
            idx = item['i']
            if idx < len(stat):
                row = stat.iloc[idx]
                is_top = (idx == 0)
                with cols[i]:
                    st.markdown(f"""<div class="podium-card {'rank-call-glow' if is_top else ''}">
                        <div style="color:#00D4FF; font-weight:bold;">{item['t']}</div>
                        <span class="staff-name-highlight">{row['Nhân viên']}</span>
                        <div class="rev-val" style="color:#00D4FF;">{row['Tổng cuộc gọi']:,}</div>
                    </div>""", unsafe_allow_html=True)
        
        stat.index = np.arange(1, len(stat) + 1)
        st.markdown("---")
        st.dataframe(stat, use_container_width=True)
    except: st.error("Lỗi file Call Log.")

# --- 4. ENGINE PHÂN TÍCH TEAM G ---
def process_team_g(file, show_vinh_danh=False):
    df = smart_load(file)
    if df is None: return

    current_year = datetime.now().year
    cols = df.columns
    c_clean = [" ".join(str(c).upper().split()) for c in cols]
    def get_c(ks):
        for i, c in enumerate(c_clean):
            if all(k in c for k in ks): return cols[i]
        return None

    m_c, e_c, v_c, w_c, id_c, team_c, owner_c = get_c(['TARGET','PREMIUM']), get_c(['THÁNG','FILE']), get_c(['THÁNG','LEAD']), get_c(['NĂM','LEAD']), get_c(['LEAD','ID']), get_c(['TEAM']), get_c(['OWNER'])
    
    if team_c:
        df = df[df[team_c].astype(str).str.upper().str.contains('G', na=False)].copy()
    
    df['REV'] = df[m_c].apply(lambda v: float(re.sub(r'[^0-9.]', '', str(v))) if pd.notna(v) and re.sub(r'[^0-9.]', '', str(v)) != '' else 0.0)

    # Chỉ số tổng
    st.title(f"📊 Team G Strategic Report - {current_year}")
    m1, m2 = st.columns(2)
    m1.metric("💰 TỔNG DOANH THU TEAM G", f"${df['REV'].sum():,.2f}")
    m2.metric("📋 TỔNG HỢP ĐỒNG TEAM G", f"{df[id_c].nunique():,}")

    # --- FIX LỖI ĐỎ CÔNG CỤ 1 TẠI ĐÂY ---
    def safe_cohort(row):
        try:
            val_v = str(row[v_c]).strip()
            val_w = str(row[w_c]).strip()
            if val_v == "" or val_v.lower() == "nan": return "📦 Nhóm Khác"
            return f"Lead T{int(float(val_v)):02d}/{int(float(val_w))}"
        except: return "📦 Nhóm Khác"

    df['NHÓM'] = df.apply(safe_cohort, axis=1)
    df['T_CHOT'] = df[e_c].apply(lambda v: int(float(v)) if pd.notna(v) and str(v).replace('.','').isdigit() and 1<=int(float(v))<=12 else None)

    if show_vinh_danh:
        lb = df.groupby(owner_c).agg({'REV':'sum', id_c:'nunique'}).sort_values('REV', ascending=False).reset_index()
        lb.columns = ['Thành viên', 'Doanh số', 'Hợp đồng']
        
        st.subheader("🏆 Hall of Fame - Team G")
        cols_v = st.columns(5)
        d_map = [{'i':3,'t':"🏅 Hạng 4"}, {'i':1,'t':"🥈 Hạng 2"}, {'i':0,'t':"👑 VÔ ĐỊCH"}, {'i':2,'t':"🥉 Hạng 3"}, {'i':4,'t':"🏅 Hạng 5"}]
        for i, item in enumerate(d_map):
            idx = item['i']
            if idx < len(lb):
                row = lb.iloc[idx]
                is_top = (idx == 0)
                with cols_v[i]:
                    st.markdown(f"""<div class="podium-card {'rank-1-glow' if is_top else ''}">
                        <div style="color:#ffd700; font-weight:bold;">{item['t']}</div>
                        <span class="staff-name-highlight">{row['Thành viên']}</span>
                        <div class="rev-val" style="color:#ffd700;">${row['Doanh số']:,.0f}</div>
                    </div>""", unsafe_allow_html=True)
        
        lb.index = np.arange(1, len(lb) + 1)
        st.markdown("---")
        st.dataframe(lb.style.format({'Doanh số': '{:,.0f}'}), use_container_width=True)
    else:
        # BIỂU ĐỒ & MA TRẬN
        st.area_chart(df.groupby('T_CHOT')['REV'].sum().reindex(range(1,13)).fillna(0), color="#00FF7F")
        t1, t2 = st.tabs(["💵 Doanh số ($)", "🔢 Số lượng hồ sơ"])
        with t1: st.dataframe(df.pivot_table(index='NHÓM', columns='T_CHOT', values='REV', aggfunc='sum').fillna(0).reindex(columns=range(1,13)).fillna(0), use_container_width=True)
        with t2: st.dataframe(df.pivot_table(index='NHÓM', columns='T_CHOT', values=id_c, aggfunc='nunique').fillna(0).reindex(columns=range(1,13)).fillna(0), use_container_width=True)

    # Nút tải báo cáo
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data_Detail')
    st.sidebar.markdown("---")
    st.sidebar.download_button("📥 Tải Báo Cáo Strategic", output.getvalue(), f"TeamG_Report_{datetime.now().strftime('%Y%m%d')}.xlsx")

# --- 5. ĐIỀU HƯỚNG ---
menu = st.sidebar.radio("Chọn công cụ xem:", ["📊 Phân tích Cohort", "🏆 Vinh danh cá nhân", "📞 Phân tích Call Log"])
f = st.sidebar.file_uploader("Nạp file dữ liệu", type=['csv', 'xlsx'])

if f:
    if menu == "📊 Phân tích Cohort": process_team_g(f, False)
    elif menu == "🏆 Vinh danh cá nhân": process_team_g(f, True)
    elif menu == "📞 Phân tích Call Log": process_call_log(f)
