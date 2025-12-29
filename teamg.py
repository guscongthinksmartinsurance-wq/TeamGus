import streamlit as st
import pandas as pd
import numpy as np
import re, csv, io
from datetime import datetime
from io import BytesIO

# --- 1. STYLE & GIAO DIỆN (GIỮ NGUYÊN) ---
st.set_page_config(page_title="Team G Performance Center", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #FFFFFF; }
    .podium-card {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border-radius: 20px; padding: 25px; text-align: center;
        border: 1px solid #334155;
    }
    .rank-call-glow { border: 3px solid #00D4FF !important; box-shadow: 0 0 30px rgba(0, 212, 255, 0.4); }
    .staff-name-highlight { color: #FFFFFF !important; font-size: 1.2rem !important; font-weight: 900 !important; text-transform: uppercase; display: block; }
    .rev-val { font-size: 1.8rem; font-weight: bold; color: #00D4FF; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HÀM TRỢ GIÚP MASTERLIFE (GIỮ NGUYÊN) ---
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
    if df is None: return None
    c_clean = [" ".join(str(c).upper().split()) for c in df.columns]
    def find_it(ks):
        for i, c in enumerate(c_clean):
            if all(k in c for k in ks): return df.columns[i]
        return None
    return {'m': find_it(['TARGET','PREMIUM']), 'e': find_it(['THÁNG','FILE']), 'v': find_it(['THÁNG','LEAD']), 'w': find_it(['NĂM','LEAD']), 'id': find_it(['LEAD','ID']), 'team': find_it(['TEAM']), 'owner': find_it(['OWNER'])}

# --- 3. ĐIỀU HƯỚNG ---
def main():
    menu = st.sidebar.radio("Chọn công cụ:", ["📊 Phân tích Cohort", "🏆 Vinh danh cá nhân", "📈 So sánh dòng tiền", "📞 Phân tích Call Log"])
    curr_y = datetime.now().year

    # 🔥 ĐỘNG CƠ SIÊU NHẸ CHO CALL LOG (KHÔNG DÙNG PANDAS ĐỂ ĐỌC FILE)
    if menu == "📞 Phân tích Call Log":
        f_c = st.sidebar.file_uploader("Nạp file Call Log (Tối ưu file cực lớn)", type=['csv'], key='f_call_pro')
        if f_c:
            st.title("📞 Call Performance Analytics (v3.0 Ultra-Light)")
            counts = {}
            try:
                # Đọc thô từng dòng để tránh tràn RAM
                stringio = io.StringIO(f_c.getvalue().decode("utf-8", errors="ignore"))
                reader = csv.DictReader(stringio)
                
                # Tìm tên cột Extension chính xác
                ext_col_name = next((c for c in reader.fieldnames if 'Extension' in c), None)
                
                if ext_col_name:
                    for row in reader:
                        val = row[ext_col_name]
                        if val:
                            staff = str(val).split('-')[-1].strip() if '-' in str(val) else str(val)
                            counts[staff] = counts.get(staff, 0) + 1
                
                if counts:
                    stat = pd.DataFrame(list(counts.items()), columns=['Nhân viên', 'Tổng cuộc gọi']).sort_values('Tổng cuộc gọi', ascending=False)
                    st.subheader("🏆 Top 5 Chiến thần Telesale")
                    v_cols = st.columns(5)
                    top_5 = stat.head(5)
                    d_map = [{'i':3,'t':"🏅 Hạng 4"}, {'i':1,'t':"🥈 Hạng 2"}, {'i':0,'t':"👑 VÔ ĐỊCH"}, {'i':2,'t':"🥉 Hạng 3"}, {'i':4,'t':"🏅 Hạng 5"}]
                    for i, item in enumerate(d_map):
                        if item['i'] < len(top_5):
                            row = top_5.iloc[item['i']]
                            with v_cols[i]:
                                st.markdown(f"<div class='podium-card rank-call-glow'><div style='color:#00D4FF;'>{item['t']}</div><span class='staff-name-highlight'>{row['Nhân viên']}</span><div class='rev-val'>{row['Tổng cuộc gọi']:,}</div></div>", unsafe_allow_html=True)
                    stat.index = np.arange(1, len(stat)+1)
                    st.markdown("---")
                    st.dataframe(stat, use_container_width=True)
            except Exception as e:
                st.error("File quá lớn hoặc lỗi định dạng. Hãy thử lọc bớt cột rác trước khi nạp.")
        return

    # CÁC CÔNG CỤ MASTERLIFE (GIỮ NGUYÊN LOGIC ỔN ĐỊNH)
    f_m = st.sidebar.file_uploader("Nạp file Masterlife", type=['csv', 'xlsx'], key='f_main')
    if f_m:
        df = smart_load(f_m); c = get_cols(df)
        if df is not None and c['m']:
            df = df[df[c['team']].astype(str).str.upper().str.contains('G', na=False)].copy()
            df['REV'] = df[c['m']].apply(lambda v: float(re.sub(r'[^0-9.]', '', str(v))) if pd.notna(v) and re.sub(r'[^0-9.]', '', str(v)) != '' else 0.0)

            if menu == "📈 So sánh dòng tiền":
                st.title("📈 So Sánh Dòng Tiền 3 Năm")
                f_n1, f_n2 = st.sidebar.file_uploader("File 2024", type=['csv', 'xlsx']), st.sidebar.file_uploader("File 2023", type=['csv', 'xlsx'])
                all_y = [df.groupby(c['e'])['REV'].sum().reindex(range(1,13)).fillna(0)]
                all_y[0].name = f"Năm {curr_y}"
                for i, f_ex in enumerate([f_n1, f_n2]):
                    df_e = smart_load(f_ex)
                    if df_e is not None:
                        c_e = get_cols(df_e)
                        df_e = df_e[df_e[c_e['team']].astype(str).str.upper().str.contains('G', na=False)].copy()
                        df_e['REV'] = df_e[c_e['m']].apply(lambda v: float(re.sub(r'[^0-9.]', '', str(v))) if pd.notna(v) and re.sub(r'[^0-9.]', '', str(v)) != '' else 0.0)
                        val_e = df_e.groupby(c_e['e'])['REV'].sum().reindex(range(1,13)).fillna(0)
                        val_e.name = f"Năm {curr_y-(i+1)}"; all_y.append(val_e)
                st.line_chart(pd.concat(all_y, axis=1))
            
            elif menu in ["📊 Phân tích Cohort", "🏆 Vinh danh cá nhân"]:
                def sanitize(row):
                    try:
                        y, m = int(float(str(row[c['w']]))), int(float(str(row[c['v']])))
                        return f"Trước năm {curr_y}" if y < curr_y else f"Lead T{m:02d}/{y}"
                    except: return "📦 Nhóm Khác"
                df['NHÓM'] = df.apply(sanitize, axis=1)
                df['T_CHOT'] = df[c['e']].apply(lambda v: int(float(v)) if (pd.notna(v) and str(v).replace('.','').isdigit()) else None)
                
                if menu == "📊 Phân tích Cohort":
                    st.title(f"📊 Team G - {curr_y}")
                    st.metric("💰 TỔNG DOANH THU", f"${df['REV'].sum():,.0f}")
                    st.dataframe(df.pivot_table(index='NHÓM', columns='T_CHOT', values='REV', aggfunc='sum').fillna(0).reindex(columns=range(1,13)).fillna(0).style.format("${:,.0f}"), use_container_width=True)
                else:
                    st.title(f"🏆 Hall of Fame")
                    lb = df.groupby(c['owner']).agg({'REV':'sum', c['id']:'nunique'}).sort_values('REV', ascending=False).reset_index()
                    lb.columns = ['Thành viên', 'Doanh số', 'Hợp đồng']
                    lb.index = np.arange(1, len(lb)+1); st.dataframe(lb.style.format({'Doanh số': '{:,.0f}'}), use_container_width=True)

            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Data_Detail')
            st.sidebar.download_button("📥 TẢI BÁO CÁO DETAIL", output.getvalue(), "TeamG_Report.xlsx")

if __name__ == "__main__": main()
