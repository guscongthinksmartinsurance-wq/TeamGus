import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from io import BytesIO

# --- 1. CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="Team GUS - Management Portal", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #00D4FF !important; font-weight: 900 !important; font-size: 2.2rem !important; }
    [data-testid="stChart"] { height: 350px !important; }
    .award-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #ffd700;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 10px rgba(255, 215, 0, 0.15);
    }
    .award-name { color: #ffffff; font-size: 1.2rem; font-weight: bold; margin: 5px 0; }
    .award-value { color: #ffd700; font-size: 1.1rem; font-weight: bold; }
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

# --- 3. ENGINE XỬ LÝ DỮ LIỆU ---
def main():
    st.sidebar.title("🛡️ Team G Portal")
    menu = st.sidebar.radio("Chọn công cụ xem:", ["📊 Phân tích Cohort", "🏆 Vinh danh cá nhân"])
    f = st.sidebar.file_uploader("Nạp file Masterlife", type=['csv', 'xlsx'])
    
    if f:
        df = smart_load(f)
        if df is None: return

        current_year = datetime.now().year
        cols = df.columns
        c_list = [" ".join(str(c).upper().split()) for c in cols]
        def get_c(keys):
            for i, c in enumerate(c_list):
                if all(k in c for k in keys): return cols[i]
            return None

        m_c, e_c, v_c, w_c, id_c, src_c, team_c, owner_c = get_c(['TARGET', 'PREMIUM']), get_c(['THÁNG', 'NHẬN', 'FILE']), get_c(['THÁNG', 'NHẬN', 'LEAD']), get_c(['NĂM', 'NHẬN', 'LEAD']), get_c(['LEAD', 'ID']), get_c(['SOURCE']), get_c(['TEAM']), get_c(['OWNER'])

        # --- LÀM SẠCH & LỌC TEAM G ---
        df = df[df[team_c].astype(str).str.upper().str.contains('G', na=False)].copy()
        df['REV'] = df[m_c].apply(lambda v: float(re.sub(r'[^0-9.]', '', str(v))) if pd.notna(v) and re.sub(r'[^0-9.]', '', str(v)) != '' else 0.0)
        
        # PHÂN LOẠI NGUỒN & COHORT
        df['LOẠI_NGUỒN'] = df[src_c].apply(lambda v: 'COLD CALL' if any(x in str(v).upper().replace(" ", "") for x in ['CC', 'COLDCALL']) else 'FUNNEL')
        
        def assign_cohort(row):
            if row['LOẠI_NGUỒN'] == 'COLD CALL': return "📦 NHÓM COLD CALL"
            try:
                y, m = int(float(row[w_c])), int(float(row[v_c]))
                return f"Funnel T{m:02d}/{y}" if y == current_year else f"Funnel Trước {current_year}"
            except: return "❌ Thiếu ngày nhận Lead"
        
        df['NHÓM_PHÂN_LOẠI'] = df.apply(assign_cohort, axis=1)
        df['TH_CHOT_NUM'] = df[e_c].apply(lambda v: int(float(v)) if pd.notna(v) and 1 <= int(float(v)) <= 12 else None)

        # --- TÍNH TOÁN TẤT CẢ DỮ LIỆU (ĐỂ KHÔNG BỊ LỖI EXPORT) ---
        # 1. Ma trận
        mtx_rev = df.pivot_table(index='NHÓM_PHÂN_LOẠI', columns='TH_CHOT_NUM', values='REV', aggfunc='sum').fillna(0).reindex(columns=range(1, 13)).fillna(0)
        mtx_rev.columns = [f"Tháng {int(c)}" for c in mtx_rev.columns]
        
        mtx_cnt = df.pivot_table(index='NHÓM_PHÂN_LOẠI', columns='TH_CHOT_NUM', values=id_c, aggfunc='nunique').fillna(0).reindex(columns=range(1, 13)).fillna(0)
        mtx_cnt.columns = [f"Tháng {int(c)}" for c in mtx_cnt.columns]

        # 2. Vinh danh
        leaderboard = df.groupby(owner_c).agg({'REV': 'sum', id_c: 'nunique'}).sort_values(by='REV', ascending=False).reset_index()
        leaderboard.columns = ['Thành viên', 'Tổng doanh số ($)', 'Số hợp đồng']

        # --- HIỂN THỊ THEO MENU ---
        if menu == "📊 Phân tích Cohort":
            st.title(f"🚀 Team G Analysis - {current_year}")
            chart_data = df.groupby(['TH_CHOT_NUM', 'LOẠI_NGUỒN'])['REV'].sum().unstack().reindex(range(1, 13)).fillna(0)
            chart_data.index = [f"Tháng {i:02d}" for i in range(1, 13)]
            st.bar_chart(chart_data)

            c1, c2, c3 = st.columns(3)
            c1.metric("💰 TỔNG DOANH SỐ G", f"${df['REV'].sum():,.2f}")
            c2.metric("📋 TỔNG HỢP ĐỒNG", f"{df[id_c].nunique():,}")
            c3.metric("🎯 NGUỒN FUNNEL", f"${df[df['LOẠI_NGUỒN']=='FUNNEL']['REV'].sum():,.2f}")

            t_money, t_count = st.tabs(["💵 Ma trận Doanh số ($)", "🔢 Ma trận Số lượng (HĐ)"])
            with t_money: st.dataframe(mtx_rev.style.format("${:,.0f}"), use_container_width=True)
            with t_count: st.dataframe(mtx_cnt.style.format("{:,.0f}"), use_container_width=True)

        else:
            st.title("🏆 Top TEAM - Policy")
            top_5 = leaderboard.head(5)
            cols_vinh = st.columns(5)
            medals = ["🥇 Hạng 1", "🥈 Hạng 2", "🥉 Hạng 3", "🏅 Hạng 4", "🏅 Hạng 5"]
            for i, (idx, row) in enumerate(top_5.iterrows()):
                with cols_vinh[i]:
                    st.markdown(f"""<div class="award-card"><div style="font-size:0.8rem;color:#ffd700;">{medals[i]}</div>
                        <div class="award-name">{row['Thành viên']}</div><div class="award-value">${row['Tổng doanh số ($)']:,.0f}</div>
                        <div style="color:#8B949E;font-size:0.8rem;">{row['Số hợp đồng']} Hợp đồng</div></div>""", unsafe_allow_html=True)
            st.markdown("---")
            st.dataframe(leaderboard.style.format({'Tổng doanh số ($)': '{:,.0f}', 'Số hợp đồng': '{:,.0f}'}), use_container_width=True)

        # --- XUẤT EXCEL (LUÔN CÓ ĐỦ DỮ LIỆU) ---
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            leaderboard.to_excel(writer, sheet_name='Leaderboard', index=False)
            mtx_rev.to_excel(writer, sheet_name='Cohort_Revenue')
            mtx_cnt.to_excel(writer, sheet_name='Cohort_Count')
            df.to_excel(writer, index=False, sheet_name='Raw_Data_TeamG')
            
        st.sidebar.markdown("---")
        st.sidebar.download_button("📥 Tải Báo Cáo Strategic (.xlsx)", output.getvalue(), f"Team_G_Report_{current_year}.xlsx")

if __name__ == "__main__":
    main()

