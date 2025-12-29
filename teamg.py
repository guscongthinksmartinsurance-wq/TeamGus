import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from io import BytesIO

# --- 1. CẤU HÌNH GIAO DIỆN & STYLE ---
st.set_page_config(page_title="TMC Strategic System", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #00D4FF !important; font-weight: 900 !important; font-size: 2.2rem !important; }
    [data-testid="stChart"] { height: 350px !important; }
    .award-card, .call-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 12px; padding: 15px; text-align: center;
        box-shadow: 0 4px 10px rgba(0, 212, 255, 0.15);
    }
    .award-card { border: 1px solid #ffd700; }
    .call-card { border: 1px solid #00D4FF; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HÀM HỖ TRỢ (HELPERS) ---
def duration_to_seconds(time_str):
    try:
        if pd.isna(time_str) or str(time_str).strip() == "": return 0
        h, m, s = map(int, str(time_str).split(':'))
        return h * 3600 + m * 60 + s
    except: return 0

def seconds_to_hms(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def get_column(c_list, original_cols, keys):
    for i, c in enumerate(c_list):
        if all(k in c for k in keys): return original_cols[i]
    return None

# --- 3. CHƯƠNG TRÌNH CHÍNH ---
def main():
    st.sidebar.title("🛡️ TMC Management")
    menu = st.sidebar.radio("Chọn công cụ:", ["📊 Phân tích Cohort", "🏆 Vinh danh Doanh số", "📞 Phân tích Call Log"])

    # --- MODULE A: MASTERLIFE (COHORT & VINH DANH DOANH SỐ) ---
    if menu in ["📊 Phân tích Cohort", "🏆 Vinh danh Doanh số"]:
        f_master = st.sidebar.file_uploader("Nạp file Masterlife", type=['csv', 'xlsx'], key="master")
        
        if f_master:
            # Đọc header chuẩn (skip rows để tìm 'TARGET PREMIUM')
            raw_df = pd.read_excel(f_master, header=None) if f_master.name.endswith(('.xlsx', '.xls')) else pd.read_csv(f_master, header=None)
            header_row = 0
            for i, row in raw_df.head(20).iterrows():
                if 'TARGET PREMIUM' in " ".join(str(val).upper() for val in row):
                    header_row = i; break
            
            df = pd.read_excel(f_master, skiprows=header_row) if f_master.name.endswith(('.xlsx', '.xls')) else pd.read_csv(f_master, skiprows=header_row)
            
            # Dò tìm cột tự động
            current_year = datetime.now().year
            original_cols = df.columns
            c_clean = [" ".join(str(c).upper().split()) for c in original_cols]
            
            m_c = get_column(c_clean, original_cols, ['TARGET', 'PREMIUM'])
            e_c = get_column(c_clean, original_cols, ['THÁNG', 'NHẬN', 'FILE'])
            v_c = get_column(c_clean, original_cols, ['THÁNG', 'NHẬN', 'LEAD'])
            w_c = get_column(c_clean, original_cols, ['NĂM', 'NHẬN', 'LEAD'])
            id_c = get_column(c_clean, original_cols, ['LEAD', 'ID'])
            src_c = get_column(c_clean, original_cols, ['SOURCE'])
            team_c = get_column(c_clean, original_cols, ['TEAM'])
            own_c = get_column(c_clean, original_cols, ['OWNER'])

            # Lọc Team G và Làm sạch dữ liệu
            df = df[df[team_c].astype(str).str.upper().str.contains('G', na=False)].copy()
            df['REV'] = df[m_c].apply(lambda v: float(re.sub(r'[^0-9.]', '', str(v))) if pd.notna(v) and re.sub(r'[^0-9.]', '', str(v)) != '' else 0.0)
            
            # Phân loại Nguồn & Nhóm Lead (Cohort)
            df['SOURCE_TYPE'] = df[src_c].apply(lambda v: 'COLD CALL' if any(x in str(v).upper().replace(" ", "") for x in ['CC', 'COLDCALL']) else 'FUNNEL')
            
            def assign_group(row):
                if row['SOURCE_TYPE'] == 'COLD CALL': return "📦 NHÓM COLD CALL"
                try:
                    y, m = int(float(row[w_c])), int(float(row[v_c]))
                    return f"Lead T{m:02d}/{y}" if y == current_year else f"Trước năm {current_year}"
                except: return "❌ Thiếu thông tin Lead"
            
            df['NHÓM_PHÂN_LOẠI'] = df.apply(assign_group, axis=1)
            df['TH_CHOT_NUM'] = df[e_c].apply(lambda v: int(float(v)) if pd.notna(v) and 1 <= int(float(v)) <= 12 else None)

            # Tính toán ma trận và leaderboard ngay lập tức (tránh lỗi UnboundLocalError)
            mtx_rev = df.pivot_table(index='NHÓM_PHÂN_LOẠI', columns='TH_CHOT_NUM', values='REV', aggfunc='sum').fillna(0).reindex(columns=range(1, 13)).fillna(0)
            mtx_rev.columns = [f"Tháng {int(c):02d}" for c in mtx_rev.columns]
            
            mtx_cnt = df.pivot_table(index='NHÓM_PHÂN_LOẠI', columns='TH_CHOT_NUM', values=id_c, aggfunc='nunique').fillna(0).reindex(columns=range(1, 13)).fillna(0)
            mtx_cnt.columns = [f"Tháng {int(c):02d}" for c in mtx_cnt.columns]
            
            leaderboard = df.groupby(own_c).agg({'REV': 'sum', id_c: 'nunique'}).sort_values(by='REV', ascending=False).reset_index()
            leaderboard.columns = ['Thành viên', 'Doanh số', 'Số hợp đồng']

            # GIAO DIỆN PHÂN TÍCH COHORT
            if menu == "📊 Phân tích Cohort":
                st.title(f"🚀 Phân tích Cohort Team G - {current_year}")
                chart_data = df.groupby(['TH_CHOT_NUM', 'SOURCE_TYPE'])['REV'].sum().unstack().reindex(range(1, 13)).fillna(0)
                chart_data.index = [f"Tháng {i:02d}" for i in range(1, 13)]
                st.bar_chart(chart_data)
                
                c1, c2, c3 = st.columns(3)
                c1.metric("💰 TỔNG DOANH SỐ G", f"${df['REV'].sum():,.2f}")
                c2.metric("🎯 FUNNEL", f"${df[df['SOURCE_TYPE']=='FUNNEL']['REV'].sum():,.2f}")
                c3.metric("📞 COLD CALL", f"${df[df['SOURCE_TYPE']=='COLD CALL']['REV'].sum():,.2f}")

                t_rev, t_cnt = st.tabs(["💵 Ma trận Doanh số ($)", "🔢 Ma trận Số lượng (HĐ)"])
                with t_rev: st.dataframe(mtx_rev.style.format("${:,.0f}"), use_container_width=True)
                with t_cnt: st.dataframe(mtx_cnt.style.format("{:,.0f}"), use_container_width=True)

            # GIAO DIỆN VINH DANH DOANH SỐ
            else:
                st.title("🏆 Hall of Fame - Team G Winners")
                top_5 = leaderboard.head(5)
                cols_v = st.columns(5)
                medals = ["🥇 Hạng 1", "🥈 Hạng 2", "🥉 Hạng 3", "🏅 Hạng 4", "🏅 Hạng 5"]
                for i, (idx, row) in enumerate(top_5.iterrows()):
                    with cols_v[i]:
                        st.markdown(f"""<div class="award-card">
                            <div style="color:#ffd700;font-size:0.8rem;">{medals[i]}</div>
                            <div style="color:white;font-weight:bold;margin:5px 0;">{row['Thành viên']}</div>
                            <div style="color:#ffd700;font-size:1.4rem;font-weight:bold;">${row['Doanh số']:,.0f}</div>
                            <div style="color:#8B949E;font-size:0.8rem;">{row['Số hợp đồng']} HĐ</div>
                        </div>""", unsafe_allow_html=True)
                st.markdown("---")
                st.dataframe(leaderboard.style.format({'Doanh số': '{:,.0f}'}), use_container_width=True)

            # NÚT EXCEL TỔNG HỢP
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                leaderboard.to_excel(writer, sheet_name='Leaderboard', index=False)
                mtx_rev.to_excel(writer, sheet_name='Cohort_Revenue')
                mtx_cnt.to_excel(writer, sheet_name='Cohort_Count')
                df.to_excel(writer, index=False, sheet_name='Data_Detail_TeamG')
            st.sidebar.markdown("---")
            st.sidebar.download_button("📥 Tải Báo Cáo Strategic", output.getvalue(), f"TMC_Report_{current_year}.xlsx")

    # --- MODULE B: CALL LOG (VINH DANH TELESALE) ---
    elif menu == "📞 Phân tích Call Log":
        st.title("📞 Call Performance Analytics")
        f_call = st.sidebar.file_uploader("Nạp file Log Cuộc gọi", type=['csv', 'xlsx'], key="call_log")
        
        if f_call:
            df_call = pd.read_excel(f_call) if f_call.name.endswith('.xlsx') else pd.read_csv(f_call)
            
            # LOGIC BÙ TRỪ: From trống lấy Extension
            df_call['Call_Ref'] = df_call['From'].fillna(df_call['Extension'])
            
            # Định danh nhân viên
            def parse_name(row):
                ext = str(row['Extension']).strip()
                if '-' in ext: return ext.split('-')[-1].strip()
                if ext.lower() != 'nan' and ext != '': return ext
                return "Unknown / Guest"
            
            df_call['Staff'] = df_call.apply(parse_name, axis=1)
            df_call['Sec'] = df_call['Duration'].apply(duration_to_seconds)
            
            # Tổng hợp
            call_stats = df_call.groupby('Staff').agg({'Call_Ref': 'count', 'Sec': 'sum'}).reset_index()
            call_stats.columns = ['Nhân viên', 'Tổng cuộc gọi', 'Giây']
            call_stats['Thời lượng'] = call_stats['Giây'].apply(seconds_to_hms)
            call_stats = call_stats.sort_values(by='Tổng cuộc gọi', ascending=False)

            # VINH DANH TOP 5 CALLS
            st.subheader("🏆 Top 5 Chiến thần Telesale")
            top_5_c = call_stats.head(5)
            cols_c = st.columns(5)
            for i, (idx, row) in enumerate(top_5_c.iterrows()):
                with cols_c[i]:
                    st.markdown(f"""<div class="call-card">
                        <div style="color:#00D4FF;font-weight:bold;">Hạng {i+1}</div>
                        <div style="color:white;font-weight:bold;margin:5px 0;">{row['Nhân viên']}</div>
                        <div style="color:#00D4FF;font-size:1.6rem;font-weight:bold;">{row['Tổng cuộc gọi']}</div>
                        <div style="color:#8B949E;font-size:0.7rem;">{row['Thời lượng']}</div>
                    </div>""", unsafe_allow_html=True)
            
            st.markdown("---")
            st.dataframe(call_stats[['Nhân viên', 'Tổng cuộc gọi', 'Thời lượng']], use_container_width=True)
            st.bar_chart(call_stats.set_index('Nhân viên')['Tổng cuộc gọi'])

if __name__ == "__main__":
    main()
