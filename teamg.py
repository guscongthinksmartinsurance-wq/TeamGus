import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from io import BytesIO

# --- 1. GIAO DIỆN & STYLE ---
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
    .staff-name-highlight { color: #FFFFFF !important; font-size: 1.5rem !important; font-weight: 900 !important; text-transform: uppercase; display: block; text-shadow: 2px 2px 8px rgba(0,0,0,0.8); }
    .rev-val { font-size: 1.8rem; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HÀM HỖ TRỢ ---
def smart_load(file):
    if file is None: return None
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

def clean_rev(df, m_c):
    return df[m_c].apply(lambda v: float(re.sub(r'[^0-9.]', '', str(v))) if pd.notna(v) and re.sub(r'[^0-9.]', '', str(v)) != '' else 0.0)

# --- 3. ĐIỀU HƯỚNG & XỬ LÝ ---
def main():
    menu = st.sidebar.radio("Chọn công cụ xem:", ["📊 Phân tích Cohort", "🏆 Vinh danh cá nhân", "📈 So sánh dòng tiền", "📞 Phân tích Call Log"])
    curr_y = datetime.now().year

    # CÔNG CỤ 4: SO SÁNH DÒNG TIỀN (3 FILE RIÊNG BIỆT)
    if menu == "📈 So sánh dòng tiền":
        st.title("📈 So Sánh Dòng Tiền 3 Năm")
        st.sidebar.markdown("### Nạp dữ liệu so sánh:")
        f_curr = st.sidebar.file_uploader(f"File Masterlife {curr_y} (Hiện tại)", type=['csv', 'xlsx'])
        f_n1 = st.sidebar.file_uploader(f"File Masterlife {curr_y-1} (N-1)", type=['csv', 'xlsx'])
        f_n2 = st.sidebar.file_uploader(f"File Masterlife {curr_y-2} (N-2)", type=['csv', 'xlsx'])
        
        all_comp = []
        for y, f in [(curr_y, f_curr), (curr_y-1, f_n1), (curr_y-2, f_n2)]:
            df_tmp = smart_load(f)
            if df_tmp is not None:
                c_c = [" ".join(str(c).upper().split()) for c in df_tmp.columns]
                tm_c = df_tmp.columns[[idx for idx, c in enumerate(c_c) if 'TEAM' in c][0]]
                rv_c = df_tmp.columns[[idx for idx, c in enumerate(c_c) if all(k in c for k in ['TARGET','PREMIUM'])][0]]
                th_c = df_tmp.columns[[idx for idx, c in enumerate(c_c) if all(k in c for k in ['THÁNG','FILE'])][0]]
                
                df_tmp = df_tmp[df_tmp[tm_c].astype(str).str.upper().str.contains('G', na=False)].copy()
                df_tmp['REV'] = clean_rev(df_tmp, rv_c)
                yr_rev = df_tmp.groupby(th_c)['REV'].sum().reindex(range(1, 13)).fillna(0)
                yr_rev.name = f"Năm {y}"
                all_comp.append(yr_rev)
        
        if all_comp:
            comp_df = pd.concat(all_comp, axis=1)
            comp_df.index = [f"T{m:02d}" for m in comp_df.index]
            st.line_chart(comp_df)
            st.dataframe(comp_df.style.format("${:,.0f}"), use_container_width=True)
            
            # Nút tải riêng cho Công cụ 4
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                comp_df.to_excel(writer, sheet_name='Comparison_Report')
            st.sidebar.download_button("📥 Tải Báo Cáo So Sánh", output.getvalue(), "So_sanh_dong_tien.xlsx")
        else:
            st.info("Vui lòng nạp ít nhất 1 file để xem so sánh.")

    # CÔNG CỤ 1 & 2
    elif menu in ["📊 Phân tích Cohort", "🏆 Vinh danh cá nhân"]:
        f_master = st.sidebar.file_uploader("Nạp file Masterlife chính", type=['csv', 'xlsx'])
        if f_master:
            df = smart_load(f_master)
            if df is not None:
                c_clean = [" ".join(str(c).upper().split()) for c in df.columns]
                def get_c(ks):
                    for i, c in enumerate(c_clean):
                        if all(k in c for k in ks): return df.columns[i]
                    return None

                m_c, e_c, v_c, w_c, id_c, team_c, owner_c = get_c(['TARGET','PREMIUM']), get_c(['THÁNG','FILE']), get_c(['THÁNG','LEAD']), get_c(['NĂM','LEAD']), get_c(['LEAD','ID']), get_c(['TEAM']), get_c(['OWNER'])
                df = df[df[team_c].astype(str).str.upper().str.contains('G', na=False)].copy()
                df['REV'] = clean_rev(df, m_c)
                
                df['NHÓM'] = df.apply(lambda r: f"Trước năm {curr_y}" if (pd.notna(r[w_c]) and int(float(r[w_c])) < curr_y) else (f"Lead T{int(float(r[v_c])):02d}/{int(float(r[w_c]))}" if pd.notna(r[v_c]) else "Khác"), axis=1)
                df['T_CHOT'] = df[e_c].apply(lambda v: int(float(v)) if pd.notna(v) and str(v).replace('.','').isdigit() and 1<=int(float(v))<=12 else None)

                if menu == "🏆 Vinh danh cá nhân":
                    st.title(f"🏆 Vinh Danh Team G {curr_y}")
                    lb = df.groupby(owner_c).agg({'REV':'sum', id_c:'nunique'}).sort_values('REV', ascending=False).reset_index()
                    lb.columns = ['Thành viên', 'Doanh số', 'Hợp đồng']
                    cols = st.columns(5)
                    d_map = [{'i':3,'t':"🏅 Hạng 4"}, {'i':1,'t':"🥈 Hạng 2"}, {'i':0,'t':"👑 VÔ ĐỊCH"}, {'i':2,'t':"🥉 Hạng 3"}, {'i':4,'t':"🏅 Hạng 5"}]
                    for i, item in enumerate(d_map):
                        if item['i'] < len(lb):
                            row = lb.iloc[item['i']]
                            with cols[i]:
                                st.markdown(f"""<div class="podium-card {'rank-1-glow' if item['i']==0 else ''}">
                                    <div style="color:#ffd700; font-weight:bold;">{item['t']}</div>
                                    <span class="staff-name-highlight">{row['Thành viên']}</span>
                                    <div class="rev-val" style="color:#ffd700;">${row['Doanh số']:,.0f}</div>
                                </div>""", unsafe_allow_html=True)
                    lb.index = np.arange(1, len(lb)+1)
                    st.dataframe(lb.style.format({'Doanh số': '{:,.0f}'}), use_container_width=True)
                else:
                    st.title(f"📊 Phân tích Cohort {curr_y}")
                    st.metric("💰 TỔNG DOANH THU", f"${df['REV'].sum():,.2f}")
                    st.area_chart(df.groupby('T_CHOT')['REV'].sum().reindex(range(1,13)).fillna(0), color="#00FF7F")
                    mtx_r = df.pivot_table(index='NHÓM', columns='T_CHOT', values='REV', aggfunc='sum').fillna(0).reindex(columns=range(1,13)).fillna(0)
                    st.dataframe(mtx_r.style.format("${:,.0f}"), use_container_width=True)

                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Data_Detail')
                st.sidebar.download_button("📥 Tải Báo Cáo Detail", output.getvalue(), "TeamG_Detail.xlsx")

    # CÔNG CỤ 3: CALL LOG
    elif menu == "📞 Phân tích Call Log":
        f_call = st.sidebar.file_uploader("Nạp file Call Log (Hỗ trợ file lớn)", type=['csv'])
        if f_call:
            st.title("📞 Call Performance (Engine V2)")
            counts = {}
            for chunk in pd.read_csv(f_call, sep=None, engine='python', encoding='utf-8-sig', chunksize=50000, on_bad_lines='skip'):
                if 'Extension' in chunk.columns:
                    chunk['Staff'] = chunk['Extension'].apply(lambda x: str(x).split('-')[-1].strip() if '-' in str(x) else str(x))
                    c_counts = chunk['Staff'].value_counts().to_dict()
                    for s, c in c_counts.items(): counts[s] = counts.get(s, 0) + c
            stat = pd.DataFrame(list(counts.items()), columns=['Nhân viên', 'Tổng cuộc gọi']).sort_values('Tổng cuộc gọi', ascending=False)
            stat.index = np.arange(1, len(stat)+1)
            st.dataframe(stat, use_container_width=True)

if __name__ == "__main__": main()
