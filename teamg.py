import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from io import BytesIO

# --- 1. CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="TMC Management System", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #00D4FF !important; font-weight: 900 !important; }
    .award-card, .call-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 12px; padding: 15px; text-align: center;
        box-shadow: 0 4px 10px rgba(0, 212, 255, 0.15);
    }
    .award-card { border: 1px solid #ffd700; }
    .call-card { border: 1px solid #00D4FF; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HÀM ĐỌC FILE THÔNG MINH (CHỐNG LỖI MÃ HÓA & CẤU TRÚC) ---
def safe_load_df(file, is_master=True):
    try:
        if file.name.endswith(('.xlsx', '.xls')):
            if is_master:
                raw = pd.read_excel(file, header=None)
                skip = 0
                for i, row in raw.head(20).iterrows():
                    if 'TARGET PREMIUM' in " ".join(str(val).upper() for val in row):
                        skip = i; break
                return pd.read_excel(file, skiprows=skip)
            return pd.read_excel(file)
        else:
            # Thử nhiều bảng mã và tự dò dấu phân cách cho CSV
            for enc in ['utf-8-sig', 'latin1', 'cp1252']:
                try:
                    file.seek(0)
                    return pd.read_csv(file, encoding=enc, sep=None, engine='python', on_bad_lines='skip')
                except: continue
            return pd.read_csv(file, encoding='utf-8', errors='ignore', on_bad_lines='skip')
    except: return None

# --- 3. CHƯƠNG TRÌNH CHÍNH ---
def main():
    st.sidebar.title("🛡️ TMC Portal")
    menu = st.sidebar.radio("Chọn công cụ:", ["📊 Phân tích Cohort", "🏆 Vinh danh Doanh số", "📞 Phân tích Call Log"])

    # --- MODULE 1 & 2: MASTERLIFE (DOANH SỐ) ---
    if menu in ["📊 Phân tích Cohort", "🏆 Vinh danh Doanh số"]:
        f_m = st.sidebar.file_uploader("Nạp file Masterlife", type=['csv', 'xlsx'], key="m_up")
        if f_m:
            df_m = safe_load_df(f_m, is_master=True)
            if df_m is not None:
                try:
                    # Logic dọn dẹp dữ liệu Masterlife
                    curr_y = datetime.now().year
                    cols = df_m.columns
                    c_c = [" ".join(str(c).upper().split()) for c in cols]
                    
                    def find_c(ks):
                        for i, c in enumerate(c_c):
                            if all(k in c for k in ks): return cols[i]
                        return None

                    m_c, e_c, v_c, w_c, id_c, src_c, t_c, o_c = find_c(['TARGET','PREMIUM']), find_c(['THÁNG','FILE']), find_c(['THÁNG','LEAD']), find_c(['NĂM','LEAD']), find_c(['LEAD','ID']), find_c(['SOURCE']), find_c(['TEAM']), find_c(['OWNER'])
                    
                    # Lọc Team G và tính tiền
                    df_m = df_m[df_m[t_c].astype(str).str.upper().str.contains('G', na=False)].copy()
                    df_m['REV'] = df_m[m_c].apply(lambda v: float(re.sub(r'[^0-9.]', '', str(v))) if pd.notna(v) and re.sub(r'[^0-9.]', '', str(v)) != '' else 0.0)
                    
                    # Phân loại và Cohort (Xử lý lỗi ValueError dòng trống)
                    df_m['SRC_TYPE'] = df_m[src_c].apply(lambda v: 'COLD CALL' if any(x in str(v).upper() for x in ['CC','COLDCALL']) else 'FUNNEL')
                    
                    def get_cohort(r):
                        if r['SRC_TYPE'] == 'COLD CALL': return "📦 NHÓM COLD CALL"
                        try:
                            return f"Lead T{int(float(r[v_c])):02d}/{int(float(r[w_c]))}"
                        except: return "❌ Thiếu ngày nhận"
                    
                    df_m['NHÓM'] = df_m.apply(get_cohort, axis=1)
                    df_m['TH_CHOT'] = df_m[e_c].apply(lambda v: int(float(v)) if pd.notna(v) and 1<=int(float(v))<=12 else None)

                    if menu == "📊 Phân tích Cohort":
                        st.title("🚀 Team G - Phân tích Cohort")
                        st.bar_chart(df_m.groupby(['TH_CHOT', 'SRC_TYPE'])['REV'].sum().unstack().reindex(range(1,13)).fillna(0))
                        st.dataframe(df_m.pivot_table(index='NHÓM', columns='TH_CHOT', values='REV', aggfunc='sum').fillna(0).reindex(columns=range(1,13)).fillna(0), use_container_width=True)
                    else:
                        st.title("🏆 Team G - Vinh danh Doanh số")
                        lb = df_m.groupby(o_c).agg({'REV':'sum', id_c:'nunique'}).sort_values('REV', ascending=False).reset_index()
                        st.dataframe(lb, use_container_width=True)
                except Exception as e: st.error(f"Lỗi xử lý file Masterlife: {e}")

    # --- MODULE 3: CALL LOG (CUỘC GỌI) ---
    elif menu == "📞 Phân tích Call Log":
        st.title("📞 Call Performance Analytics")
        f_c = st.sidebar.file_uploader("Nạp file Log Cuộc gọi", type=['csv', 'xlsx'], key="c_up")
        btn = st.sidebar.button("🚀 Chạy phân tích cuộc gọi")
        
        if f_c and btn:
            df_call = safe_load_df(f_c, is_master=False)
            if df_call is not None:
                try:
                    # Logic bù trừ From/Extension
                    df_call['Ref'] = df_call['From'].fillna(df_call['Extension'])
                    
                    def get_stf(r):
                        ex = str(r['Extension']).strip()
                        return ex.split('-')[-1].strip() if '-' in ex else (ex if ex.lower() != 'nan' else "Unknown")
                    
                    df_call['Staff'] = df_call.apply(get_stf, axis=1)
                    
                    def to_s(t):
                        try:
                            h,m,s = map(int, str(t).split(':')); return h*3600+m*60+s
                        except: return 0
                    
                    df_call['Sec'] = df_call['Duration'].apply(to_s)
                    stat = df_call.groupby('Staff').agg({'Ref':'count', 'Sec':'sum'}).reset_index().sort_values('Ref', ascending=False)
                    stat['Time'] = stat['Sec'].apply(lambda x: f"{int(x//3600):02d}:{int((x%3600)//60):02d}:{int(x%60):02d}")

                    # Vinh danh Top 5
                    st.subheader("🏆 Top 5 Chiến thần Telesale")
                    cols = st.columns(5)
                    for i, (idx, row) in enumerate(stat.head(5).iterrows()):
                        with cols[i]:
                            st.markdown(f"""<div class="call-card"><div style="color:#00D4FF;">Hạng {i+1}</div>
                                <div style="color:white;font-weight:bold;">{row['Staff']}</div>
                                <div style="color:#00D4FF;font-size:1.5rem;font-weight:bold;">{row['Ref']}</div>
                                <div style="color:#8B949E;font-size:0.7rem;">{row['Time']}</div></div>""", unsafe_allow_html=True)
                    st.dataframe(stat[['Staff', 'Ref', 'Time']], use_container_width=True)
                except Exception as e: st.error(f"Lỗi xử lý file Call Log: {e}")

if __name__ == "__main__":
    main()
