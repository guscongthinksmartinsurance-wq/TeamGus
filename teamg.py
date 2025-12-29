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
    .award-card, .call-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 12px; padding: 15px; text-align: center;
        box-shadow: 0 4px 10px rgba(0, 212, 255, 0.15);
    }
    .award-card { border: 1px solid #ffd700; }
    .call-card { border: 1px solid #00D4FF; }
    /* Tùy chỉnh nút Run */
    div.stButton > button:first-child {
        background-color: #00D4FF; color: white; width: 100%; border-radius: 8px; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HÀM HỖ TRỢ ---
def duration_to_seconds(time_str):
    try:
        if pd.isna(time_str) or str(time_str).strip() == "": return 0
        h, m, s = map(int, str(time_str).split(':'))
        return h * 3600 + m * 60 + s
    except: return 0

def seconds_to_hms(seconds):
    h, m, s = int(seconds // 3600), int((seconds % 3600) // 60), int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def get_column(c_list, original_cols, keys):
    for i, c in enumerate(c_list):
        if all(k in c for k in keys): return original_cols[i]
    return None

# --- 3. CHƯƠNG TRÌNH CHÍNH ---
def main():
    st.sidebar.title("🛡️ TMC Management")
    menu = st.sidebar.radio("Chọn công cụ:", ["📊 Phân tích Cohort", "🏆 Vinh danh Doanh số", "📞 Phân tích Call Log"])

    # --- MODULE A: MASTERLIFE (COHORT & VINH DANH) ---
    if menu in ["📊 Phân tích Cohort", "🏆 Vinh danh Doanh số"]:
        f_master = st.sidebar.file_uploader("Nạp file Masterlife", type=['csv', 'xlsx'], key="master_file")
        if f_master:
            raw_df = pd.read_excel(f_master, header=None) if f_master.name.endswith(('.xlsx', '.xls')) else pd.read_csv(f_master, header=None)
            header_row = 0
            for i, row in raw_df.head(20).iterrows():
                if 'TARGET PREMIUM' in " ".join(str(val).upper() for val in row):
                    header_row = i; break
            df = pd.read_excel(f_master, skiprows=header_row) if f_master.name.endswith(('.xlsx', '.xls')) else pd.read_csv(f_master, skiprows=header_row)
            
            # Logic xử lý (Giữ nguyên như bản 100% trước đó)
            current_year = datetime.now().year
            cols = df.columns
            c_clean = [" ".join(str(c).upper().split()) for c in cols]
            m_c, e_c, v_c, w_c, id_c, src_c, team_c, own_c = get_column(c_clean, cols, ['TARGET', 'PREMIUM']), get_column(c_clean, cols, ['THÁNG', 'NHẬN', 'FILE']), get_column(c_clean, cols, ['THÁNG', 'NHẬN', 'LEAD']), get_column(c_clean, cols, ['NĂM', 'NHẬN', 'LEAD']), get_column(c_clean, cols, ['LEAD', 'ID']), get_column(c_clean, cols, ['SOURCE']), get_column(c_clean, cols, ['TEAM']), get_column(c_clean, cols, ['OWNER'])
            
            df = df[df[team_c].astype(str).str.upper().str.contains('G', na=False)].copy()
            df['REV'] = df[m_c].apply(lambda v: float(re.sub(r'[^0-9.]', '', str(v))) if pd.notna(v) and re.sub(r'[^0-9.]', '', str(v)) != '' else 0.0)
            df['SOURCE_TYPE'] = df[src_c].apply(lambda v: 'COLD CALL' if any(x in str(v).upper().replace(" ", "") for x in ['CC', 'COLDCALL']) else 'FUNNEL')
            df['NHÓM_PHÂN_LOẠI'] = df.apply(lambda r: f"Lead T{int(float(r[v_c])):02d}/{int(float(r[w_c]))}" if r['SOURCE_TYPE'] == 'FUNNEL' and pd.notna(r[v_c]) else ("📦 NHÓM COLD CALL" if r['SOURCE_TYPE'] == 'COLD CALL' else "❌ Thiếu thông tin"), axis=1)
            df['TH_CHOT_NUM'] = df[e_c].apply(lambda v: int(float(v)) if pd.notna(v) and 1 <= int(float(v)) <= 12 else None)

            if menu == "📊 Phân tích Cohort":
                st.title(f"🚀 Phân tích Cohort Team G - {current_year}")
                st.bar_chart(df.groupby(['TH_CHOT_NUM', 'SOURCE_TYPE'])['REV'].sum().unstack().reindex(range(1, 13)).fillna(0))
                st.dataframe(df.pivot_table(index='NHÓM_PHÂN_LOẠI', columns='TH_CHOT_NUM', values='REV', aggfunc='sum').fillna(0).reindex(columns=range(1, 13)).fillna(0), use_container_width=True)
            else:
                st.title("🏆 Hall of Fame - Team G Winners")
                leaderboard = df.groupby(own_c).agg({'REV': 'sum', id_c: 'nunique'}).sort_values(by='REV', ascending=False).reset_index()
                st.dataframe(leaderboard, use_container_width=True)

    # --- MODULE B: CALL LOG (CÓ NÚT RUN) ---
    elif menu == "📞 Phân tích Call Log":
        st.title("📞 Call Performance Analytics")
        f_call = st.sidebar.file_uploader("Nạp file Log Cuộc gọi", type=['csv', 'xlsx'], key="call_file")
        
        # Thêm nút Run vào Sidebar
        run_button = st.sidebar.button("🚀 Chạy phân tích cuộc gọi")
        
        if f_call and run_button:
            df_call = pd.read_excel(f_call) if f_call.name.endswith('.xlsx') else pd.read_csv(f_call)
            
            # Logic bù trừ From/Extension
            df_call['Call_Ref'] = df_call['From'].fillna(df_call['Extension'])
            
            def parse_name(row):
                ext = str(row['Extension']).strip()
                if '-' in ext: return ext.split('-')[-1].strip()
                if ext.lower() != 'nan' and ext != '': return ext
                return "Unknown"
            
            df_call['Staff'] = df_call.apply(parse_name, axis=1)
            df_call['Sec'] = df_call['Duration'].apply(duration_to_seconds)
            
            call_stats = df_call.groupby('Staff').agg({'Call_Ref': 'count', 'Sec': 'sum'}).reset_index().sort_values(by='Call_Ref', ascending=False)
            call_stats.columns = ['Nhân viên', 'Tổng cuộc gọi', 'Giây']
            call_stats['Thời lượng'] = call_stats['Giây'].apply(seconds_to_hms)

            # Vinh danh Top 5
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
        elif f_call and not run_button:
            st.info("👆 Vui lòng nhấn nút **'🚀 Chạy phân tích cuộc gọi'** ở thanh bên trái để bắt đầu.")

if __name__ == "__main__":
    main()
