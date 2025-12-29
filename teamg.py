import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from io import BytesIO

# --- 1. GIAO DIỆN & STYLE (GIỮ NGUYÊN) ---
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
    .rank-1-glow {
        border: 3px solid #ffd700 !important;
        box-shadow: 0 0 30px rgba(255, 215, 0, 0.4);
        transform: scale(1.08);
    }
    .staff-name-highlight {
        color: #FFFFFF !important; font-size: 1.6rem !important;
        font-weight: 900 !important; text-transform: uppercase;
        display: block; text-shadow: 2px 2px 8px rgba(0,0,0,0.8);
    }
    .rev-gold { color: #ffd700; font-size: 1.8rem; font-weight: bold; }
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
def process_team_g(file, show_vinh_danh=False):
    df = smart_load(file)
    if df is None: return

    current_year = datetime.now().year
    cols = df.columns
    c_clean = [" ".join(str(c).upper().split()) for c in cols]
    def get_c(keys):
        for i, c in enumerate(c_clean):
            if all(k in c for k in keys): return cols[i]
        return None

    m_c, e_c, v_c, w_c, id_c, team_c, owner_c = get_c(['TARGET','PREMIUM']), get_c(['THÁNG','FILE']), get_c(['THÁNG','LEAD']), get_c(['NĂM','LEAD']), get_c(['LEAD','ID']), get_c(['TEAM']), get_c(['OWNER'])
    
    if team_c:
        df = df[df[team_c].astype(str).str.upper().str.contains('G', na=False)].copy()
    
    df['REV'] = df[m_c].apply(lambda v: float(re.sub(r'[^0-9.]', '', str(v))) if pd.notna(v) and re.sub(r'[^0-9.]', '', str(v)) != '' else 0.0)

    # --- CHỈ SỐ TỔNG ---
    st.title(f"📊 Team G Strategic Report - {current_year}")
    m1, m2 = st.columns(2)
    m1.metric("💰 TỔNG DOANH THU TEAM G", f"${df['REV'].sum():,.2f}")
    m2.metric("📋 TỔNG HỢP ĐỒNG TEAM G", f"{df[id_c].nunique():,}")

    # --- CHUẨN BỊ DỮ LIỆU MA TRẬN CHO CẢ DASHBOARD VÀ DOWNLOAD ---
    def assign_cohort(row):
        try:
            y, m = int(float(row[w_c])), int(float(row[v_c]))
            return f"Lead T{m:02d}/{y}" if y == current_year else f"Trước năm {current_year}"
        except: return "❌ Thiếu thông tin Lead"

    df['NHÓM_LEAD'] = df.apply(assign_cohort, axis=1)
    df['TH_CHOT_NUM'] = df[e_c].apply(lambda v: int(float(v)) if pd.notna(v) and 1 <= int(float(v)) <= 12 else None)
    
    matrix_rev = df.pivot_table(index='NHÓM_LEAD', columns='TH_CHOT_NUM', values='REV', aggfunc='sum').fillna(0)
    matrix_count = df.pivot_table(index='NHÓM_LEAD', columns='TH_CHOT_NUM', values=id_c, aggfunc='nunique').fillna(0)

    def sort_mtx(mtx):
        mtx = mtx.reindex(columns=range(1, 13)).fillna(0)
        mtx.columns = [f"Tháng {int(c)}" for c in mtx.columns]
        idx_current = sorted([i for i in mtx.index if f"/{current_year}" in i])
        final_idx = ([f"Trước năm {current_year}"] if f"Trước năm {current_year}" in mtx.index else []) + idx_current + ([i for i in mtx.index if "❌" in i])
        return mtx.reindex(final_idx)

    final_rev_mtx = sort_mtx(matrix_rev)
    final_count_mtx = sort_mtx(matrix_count)

    # --- HIỂN THỊ ---
    if show_vinh_danh:
        lb = df.groupby(owner_c).agg({'REV':'sum', id_c:'nunique'}).sort_values('REV', ascending=False).reset_index()
        lb.columns = ['Thành viên', 'Doanh số', 'Hợp đồng']
        
        # Podium logic (Kenny Vô địch ở giữa)
        top_5 = lb.head(5).copy()
        display_map = [
            {'idx': 1, 'title': "🥈 HẠNG 2", 'glow': False}, 
            {'idx': 0, 'title': "👑 VÔ ĐỊCH", 'glow': True},  
            {'idx': 2, 'title': "🥉 HẠNG 3", 'glow': False}, 
            {'idx': 3, 'title': "🏅 HẠNG 4", 'glow': False}, 
            {'idx': 4, 'title': "🏅 HẠNG 5", 'glow': False}
        ]
        cols_v = st.columns(5)
        for i, item in enumerate(display_map):
            idx = item['idx']
            if idx < len(top_5):
                row = top_5.iloc[idx]
                with cols_v[i]:
                    st.markdown(f"""<div class="podium-card {'rank-1-glow' if item['glow'] else ''}">
                        <div style="color:{'#ffd700' if item['glow'] else '#8B949E'};font-weight:bold;">{item['title']}</div>
                        <span class="staff-name-highlight">{row['Thành viên']}</span>
                        <div class="rev-gold">${row['Doanh số']:,.0f}</div>
                        <div style="color:#00D4FF;font-weight:bold;">{row['Hợp đồng']} Hợp đồng</div>
                    </div>""", unsafe_allow_html=True)
        st.markdown("---")
        st.dataframe(lb.style.format({'Doanh số': '{:,.0f}'}), use_container_width=True)
    else:
        chart_data = df.groupby('TH_CHOT_NUM')['REV'].sum().reindex(range(1, 13)).fillna(0)
        chart_df = pd.DataFrame({'Tháng': [f"Tháng {i:02d}" for i in range(1, 13)], 'Doanh Số G': chart_data.values}).set_index('Tháng')
        st.area_chart(chart_df, color="#00FF7F")
        t1, t2 = st.tabs(["💵 Doanh số ($)", "🔢 Số lượng hồ sơ"])
        with t1: st.dataframe(final_rev_mtx.style.format("${:,.0f}"), use_container_width=True)
        with t2: st.dataframe(final_count_mtx.style.format("{:,.0f}"), use_container_width=True)

    # --- NÚT TẢI BÁO CÁO ĐA SHEET (SỬA LỖI THIẾU DỮ LIỆU) ---
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        final_rev_mtx.to_excel(writer, sheet_name='Cohort_Revenue')
        final_count_mtx.to_excel(writer, sheet_name='Cohort_Count')
        df.to_excel(writer, index=False, sheet_name='Data_Detail_TeamG')
        
        # Thêm màu mè cho Excel (tùy chọn)
        workbook = writer.book
        fmt = workbook.add_format({'num_format': '#,##0'})
        writer.sheets['Cohort_Revenue'].set_column('B:M', 15, fmt)
        writer.sheets['Cohort_Count'].set_column('B:M', 12, fmt)

    st.sidebar.markdown("---")
    st.sidebar.download_button(
        label="📥 Tải Báo Cáo Full (3 Sheets)",
        data=output.getvalue(),
        file_name=f"TeamG_Strategic_Report_{datetime.now().strftime('%d%m%Y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --- 4. MODULE CALL LOG (DỮ LIỆU RIÊNG) ---
def process_call_log(file):
    st.title("📞 Call Performance Analytics")
    try:
        df_c = pd.read_csv(file, encoding='utf-8-sig', sep=None, engine='python', on_bad_lines='skip')
        df_c['Ref'] = df_c['From'].fillna(df_c['Extension'])
        df_c['Staff'] = df_c['Extension'].apply(lambda x: str(x).split('-')[-1].strip() if '-' in str(x) else str(x))
        stat = df_c.groupby('Staff')['Ref'].count().sort_values(ascending=False).reset_index()
        stat.columns = ['Nhân viên', 'Tổng cuộc gọi']
        
        st.subheader("🏆 Top 5 Chiến thần Telesale")
        c = st.columns(5)
        for i, (idx, row) in enumerate(stat.head(5).iterrows()):
            with c[i]:
                st.markdown(f"<div class='podium-card' style='border-color:#00D4FF'><b>{row['Nhân viên']}</b><br><span style='font-size:1.8rem; color:#00D4FF'>{row['Tổng cuộc gọi']}</span></div>", unsafe_allow_html=True)
        st.dataframe(stat, use_container_width=True)
    except: st.error("Lỗi file Call Log.")

# --- 5. ĐIỀU HƯỚNG ---
menu = st.sidebar.radio("Chọn công cụ xem:", ["📊 Phân tích Cohort", "🏆 Vinh danh cá nhân", "📞 Phân tích Call Log"])
f = st.sidebar.file_uploader("Nạp file Masterlife", type=['csv', 'xlsx'])

if f:
    if menu == "📊 Phân tích Cohort": process_team_g(f, False)
    elif menu == "🏆 Vinh danh cá nhân": process_team_g(f, True)
    elif menu == "📞 Phân tích Call Log": process_call_log(f)
