import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from io import BytesIO

# --- 1. GIAO DIỆN & STYLE CAO CẤP ---
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

# --- 2. HÀM TRỢ GIÚP (LÀM SẠCH DỮ LIỆU) ---
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

def get_cols(df):
    c_clean = [" ".join(str(c).upper().split()) for c in df.columns]
    def find_it(ks):
        for i, c in enumerate(c_clean):
            if all(k in c for k in ks): return df.columns[i]
        return None
    return {
        'm': find_it(['TARGET','PREMIUM']), 'e': find_it(['THÁNG','FILE']),
        'v': find_it(['THÁNG','LEAD']), 'w': find_it(['NĂM','LEAD']),
        'id': find_it(['LEAD','ID']), 'team': find_it(['TEAM']), 'owner': find_it(['OWNER'])
    }

def process_rev(df, m_c):
    return df[m_c].apply(lambda v: float(re.sub(r'[^0-9.]', '', str(v))) if pd.notna(v) and re.sub(r'[^0-9.]', '', str(v)) != '' else 0.0)

# --- 3. CÁC CÔNG CỤ CHI TIẾT ---
def tool_cohort_vinhdanh(f, mode):
    df = smart_load(f)
    if df is None: return
    c = get_cols(df)
    curr_y = datetime.now().year
    df = df[df[c['team']].astype(str).str.upper().str.contains('G', na=False)].copy()
    df['REV'] = process_rev(df, c['m'])
    
    # Logic Cohort gom nhóm năm cũ
    df['NHÓM'] = df.apply(lambda r: f"Trước năm {curr_y}" if (pd.notna(r[c['w']]) and int(float(r[c['w']])) < curr_y) else (f"Lead T{int(float(r[c['v']])):02d}/{int(float(r[c['w']]))}" if pd.notna(r[c['v']]) else "Khác"), axis=1)
    df['T_CHOT'] = df[c['e']].apply(lambda v: int(float(v)) if pd.notna(v) and str(v).replace('.','').isdigit() and 1<=int(float(v))<=12 else None)

    if mode == "vinh_danh":
        st.title(f"🏆 Vinh Danh Team G {curr_y}")
        lb = df.groupby(c['owner']).agg({'REV':'sum', c['id']:'nunique'}).sort_values('REV', ascending=False).reset_index()
        lb.columns = ['Thành viên', 'Doanh số', 'Hợp đồng']
        cols = st.columns(5)
        d_map = [{'i':3,'t':"🏅 Hạng 4"}, {'i':1,'t':"🥈 Hạng 2"}, {'i':0,'t':"👑 VÔ ĐỊCH"}, {'i':2,'t':"🥉 Hạng 3"}, {'i':4,'t':"🏅 Hạng 5"}]
        for i, item in enumerate(d_map):
            if item['i'] < len(lb):
                row = lb.iloc[item['i']]
                with cols[i]:
                    st.markdown(f"<div class='podium-card {'rank-1-glow' if item['i']==0 else ''}'><div style='color:#ffd700; font-weight:bold;'>{item['t']}</div><span class='staff-name-highlight'>{row['Thành viên']}</span><div class='rev-val' style='color:#ffd700;'>${row['Doanh số']:,.0f}</div></div>", unsafe_allow_html=True)
        lb.index = np.arange(1, len(lb)+1)
        st.dataframe(lb.style.format({'Doanh số': '{:,.0f}'}), use_container_width=True)
    else:
        st.title(f"📊 Phân tích Cohort {curr_y}")
        st.metric("💰 TỔNG DOANH THU", f"${df['REV'].sum():,.2f}")
        st.area_chart(df.groupby('T_CHOT')['REV'].sum().reindex(range(1,13)).fillna(0), color="#00FF7F")
        mtx = df.pivot_table(index='NHÓM', columns='T_CHOT', values='REV', aggfunc='sum').fillna(0).reindex(columns=range(1,13)).fillna(0)
        st.dataframe(mtx.style.format("${:,.0f}"), use_container_width=True)
    
    # Nút Export
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data_Detail')
    st.sidebar.download_button("📥 Tải Báo Cáo Detail", output.getvalue(), "TeamG_Detail.xlsx")

def tool_comparison(f_curr, f_n1, f_n2):
    st.title("📈 So Sánh Dòng Tiền 3 Năm")
    curr_y = datetime.now().year
    all_c = []
    for y, f in [(curr_y, f_curr), (curr_y-1, f_n1), (curr_y-2, f_n2)]:
        tmp = smart_load(f)
        if tmp is not None:
            c = get_cols(tmp)
            tmp = tmp[tmp[c['team']].astype(str).str.upper().str.contains('G', na=False)].copy()
            tmp['REV'] = process_rev(tmp, c['m'])
            val = tmp.groupby(c['e'])['REV'].sum().reindex(range(1, 13)).fillna(0)
            val.name = f"Năm {y}"
            all_c.append(val)
    if all_c:
        res = pd.concat(all_c, axis=1)
        res.index = [f"T{m:02d}" for m in res.index]
        st.line_chart(res)
        st.dataframe(res.style.format("${:,.0f}"), use_container_width=True)

# --- 4. ĐIỀU HƯỚNG CHÍNH ---
def main():
    menu = st.sidebar.radio("Chọn công cụ:", ["📊 Phân tích Cohort", "🏆 Vinh danh cá nhân", "📈 So sánh dòng tiền", "📞 Phân tích Call Log"])
    
    if menu == "📈 So sánh dòng tiền":
        f1 = st.sidebar.file_uploader("File 2025", type=['csv', 'xlsx'])
        f2 = st.sidebar.file_uploader("File 2024", type=['csv', 'xlsx'])
        f3 = st.sidebar.file_uploader("File 2023", type=['csv', 'xlsx'])
        if f1 or f2 or f3: tool_comparison(f1, f2, f3)
    
    elif menu == "📞 Phân tích Call Log":
        f_c = st.sidebar.file_uploader("Nạp file Call Log", type=['csv'])
        if f_c:
            st.title("📞 Call Performance (Engine V2)")
            counts = {}
            for chunk in pd.read_csv(f_c, sep=None, engine='python', chunksize=50000, on_bad_lines='skip'):
                if 'Extension' in chunk.columns:
                    chunk['Staff'] = chunk['Extension'].apply(lambda x: str(x).split('-')[-1].strip() if '-' in str(x) else str(x))
                    for s, c in chunk['Staff'].value_counts().to_dict().items(): counts[s] = counts.get(s,0) + c
            stat = pd.DataFrame(list(counts.items()), columns=['Nhân viên', 'Tổng cuộc gọi']).sort_values('Tổng cuộc gọi', ascending=False)
            stat.index = np.arange(1, len(stat)+1)
            st.dataframe(stat, use_container_width=True)
            
    else: # Cohort & Vinh danh
        f_m = st.sidebar.file_uploader("Nạp file Masterlife", type=['csv', 'xlsx'])
        if f_m:
            mode = "vinh_danh" if menu == "🏆 Vinh danh cá nhân" else "cohort"
            tool_cohort_vinhdanh(f_m, mode)

if __name__ == "__main__": main()
