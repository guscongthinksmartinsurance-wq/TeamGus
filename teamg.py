import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from io import BytesIO

# --- 1. CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="TMC Strategic Portal", layout="wide")
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

# --- 2. HÀM HỖ TRỢ ---
def smart_load(file):
    try:
        if file.name.endswith(('.xlsx', '.xls')):
            return pd.read_excel(file)
        return pd.read_csv(file, encoding='utf-8', errors='ignore')
    except: return None

def duration_to_seconds(time_str):
    try:
        h, m, s = map(int, str(time_str).split(':'))
        return h * 3600 + m * 60 + s
    except: return 0

def seconds_to_hms(seconds):
    h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

# --- 3. CHƯƠNG TRÌNH CHÍNH ---
def main():
    st.sidebar.title("🛡️ TMC Management")
    menu = st.sidebar.radio("Chọn công cụ:", ["📊 Phân tích Cohort", "🏆 Vinh danh Doanh số", "📞 Phân tích Call Log"])

    # --- MODULE 1 & 2: DÙNG FILE MASTERLIFE ---
    if menu in ["📊 Phân tích Cohort", "🏆 Vinh danh Doanh số"]:
        f_master = st.sidebar.file_uploader("Nạp file Masterlife", type=['csv', 'xlsx'], key="master")
        if f_master:
            # Đọc header chuẩn
            raw_df = pd.read_excel(f_master, header=None) if f_master.name.endswith(('.xlsx', '.xls')) else pd.read_csv(f_master, header=None)
            header_row = 0
            for i, row in raw_df.head(20).iterrows():
                if 'TARGET PREMIUM' in " ".join(str(val).upper() for val in row):
                    header_row = i; break
            df = pd.read_excel(f_master, skiprows=header_row) if f_master.name.endswith(('.xlsx', '.xls')) else pd.read_csv(f_master, skiprows=header_row)
            
            # --- LÀM SẠCH & LỌC TEAM G ---
            current_year = datetime.now().year
            cols = df.columns
            c_list = [" ".join(str(c).upper().split()) for c in cols]
            def get_c(keys):
                for i, c in enumerate(c_list):
                    if all(k in c for k in keys): return cols[i]
                return None

            m_c, e_c, v_c, w_c, id_c, src_c, team_c, owner_c = get_c(['TARGET', 'PREMIUM']), get_c(['THÁNG', 'NHẬN', 'FILE']), get_c(['THÁNG', 'NHẬN', 'LEAD']), get_c(['NĂM', 'NHẬN', 'LEAD']), get_c(['LEAD', 'ID']), get_c(['SOURCE']), get_c(['TEAM']), get_c(['OWNER'])
            
            df = df[df[team_c].astype(str).str.upper().str.contains('G', na=False)].copy()
            df['REV'] = df[m_c].apply(lambda v: float(re.sub(r'[^0-9.]', '', str(v))) if pd.notna(v) and re.sub(r'[^0-9.]', '', str(v)) != '' else 0.0)
            df['LOẠI_NGUỒN'] = df[src_c].apply(lambda v: 'COLD CALL' if any(x in str(v).upper().replace(" ", "") for x in ['CC', 'COLDCALL']) else 'FUNNEL')
            
            def assign_cohort(row):
                if row['LOẠI_NGUỒN'] == 'COLD CALL': return "📦 NHÓM COLD CALL"
                try:
                    y, m = int(float(row[w_c])), int(float(row[v_c]))
                    return f"Funnel T{m:02d}/{y}" if y == current_year else f"Funnel Trước {current_year}"
                except: return "❌ Thiếu ngày nhận Lead"
            
            df['NHÓM_PHÂN_LOẠI'] = df.apply(assign_cohort, axis=1)
            df['TH_CHOT_NUM'] = df[e_c].apply(lambda v: int(float(v)) if pd.notna(v) and 1 <= int(float(v)) <= 12 else None)

            # --- HIỂN THỊ COHORT ---
            if menu == "📊 Phân tích Cohort":
                st.title(f"🚀 Phân tích Cohort Team G - {current_year}")
                chart_data = df.groupby(['TH_CHOT_NUM', 'LOẠI_NGUỒN'])['REV'].sum().unstack().reindex(range(1, 13)).fillna(0)
                chart_data.index = [f"Tháng {i:02d}" for i in range(1, 13)]
                st.bar_chart(chart_data)
                
                c1, c2 = st.columns(2)
                c1.metric("💰 TỔNG DOANH SỐ G", f"${df['REV'].sum():,.0f}")
                c2.metric("📋 TỔNG HỢP ĐỒNG", f"{df[id_c].nunique():,}")
                
                mtx_rev = df.pivot_table(index='NHÓM_PHÂN_LOẠI', columns='TH_CHOT_NUM', values='REV', aggfunc='sum').fillna(0).reindex(columns=range(1, 13)).fillna(0)
                mtx_rev.columns = [f"Tháng {int(c)}" for c in mtx_rev.columns]
                st.dataframe(mtx_rev.style.format("${:,.0f}"), use_container_width=True)

            # --- HIỂN THỊ VINH DANH DOANH SỐ ---
            else:
                st.title("🏆 Vinh danh Chiến thần Doanh số")
                leaderboard = df.groupby(owner_c).agg({'REV': 'sum', id_c: 'nunique'}).sort_values(by='REV', ascending=False).reset_index()
                leaderboard.columns = ['Thành viên', 'Doanh số', 'Hợp đồng']
                
                top_5 = leaderboard.head(5)
                cols_v = st.columns(5)
                medals = ["🥇 Hạng 1", "🥈 Hạng 2", "🥉 Hạng 3", "🏅 Hạng 4", "🏅 Hạng 5"]
                for i, (idx, row) in enumerate(top_5.iterrows()):
                    with cols_v[i]:
                        st.markdown(f"""<div class="award-card"><div style="color:#ffd700;font-size:0.8rem;">{medals[i]}</div>
                            <div style="color:white;font-weight:bold;margin:5px 0;">{row['Thành viên']}</div>
                            <div style="color:#ffd700;font-size:1.3rem;font-weight:bold;">${row['Doanh số']:,.0f}</div>
                            <div style="color:#8B949E;font-size:0.8rem;">{row['Hợp đồng']} HĐ</div></div>""", unsafe_allow_html=True)
                st.markdown("---")
                st.dataframe(leaderboard.style.format({'Doanh số': '{:,.0f}'}), use_container_width=True)

    # --- NHÁNH 3: PHÂN TÍCH CALL LOG (LOGIC BÙ TRỪ FROM/EXTENSION) ---
    elif menu == "📞 Phân tích Call Log":
        st.title("📞 Call Performance Analytics")
        f_call = st.sidebar.file_uploader("Nạp file Log Cuộc gọi", type=['csv', 'xlsx'], key="call_log")
        
        if f_call:
            df_call = smart_load(f_call)
            if df_call is not None:
                # 1. Logic Bù trừ: Lấy From, nếu From trống thì lấy Extension để đếm
                df_call['Call_ID'] = df_call['From'].fillna(df_call['Extension'])
                
                # 2. Lấy tên hiển thị từ Extension
                def get_sale_name(row):
                    ext = str(row['Extension']).strip()
                    if '-' in ext: return ext.split('-')[-1].strip()
                    if ext.lower() != 'nan' and ext != '': return ext
                    return "Ẩn danh"
                
                df_call['Sales_Rep'] = df_call.apply(get_sale_name, axis=1)
                df_call['Duration_Sec'] = df_call['Duration'].apply(duration_to_seconds)
                
                # 3. Tổng hợp
                call_lead = df_call.groupby('Sales_Rep').agg({'Call_ID': 'count', 'Duration_Sec': 'sum'}).reset_index()
                call_lead.columns = ['Nhân viên', 'Tổng cuộc gọi', 'Giây']
                call_lead['Thời lượng'] = call_lead['Giây'].apply(seconds_to_hms)
                call_lead = call_lead.sort_values(by='Tổng cuộc gọi', ascending=False)

                # 4. Vinh danh Call Log
                st.subheader("🏆 Top 5 Chiến thần Telesale")
                top_5_c = call_lead.head(5)
                cols_c = st.columns(5)
                for i, (idx, row) in enumerate(top_5_c.iterrows()):
                    with cols_c[i]:
                        st.markdown(f"""<div class="call-card">
                            <div style="color:#00D4FF;font-weight:bold;">Hạng {i+1}</div>
                            <div style="color:white;font-weight:bold;margin:5px 0;">{row['Nhân viên']}</div>
                            <div style="color:#00D4FF;font-size:1.6rem;font-weight:bold;">{row['Tổng cuộc gọi']}</div>
                            <div style="color:#8B949E;font-size:0.7rem;">{row['Thời lượng']}</div></div>""", unsafe_allow_html=True)
                
                st.markdown("---")
                st.dataframe(call_lead[['Nhân viên', 'Tổng cuộc gọi', 'Thời lượng']], use_container_width=True)
                st.bar_chart(call_lead.set_index('Nhân viên')['Tổng cuộc gọi'])

if __name__ == "__main__":
    main()
