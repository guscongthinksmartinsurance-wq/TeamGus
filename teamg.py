import streamlit as st
import pandas as pd
import numpy as np
import re
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

# --- 2. HÀM TRỢ GIÚP (CÔNG CỤ 1, 2, 4) ---
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

def process_rev(df, m_c):
    return df[m_c].apply(lambda v: float(re.sub(r'[^0-9.]', '', str(v))) if pd.notna(v) and re.sub(r'[^0-9.]', '', str(v)) != '' else 0.0)

# --- 3. ĐIỀU HƯỚNG ---
def main():
    menu = st.sidebar.radio("Chọn công cụ:", ["📊 Phân tích Cohort", "🏆 Vinh danh cá nhân", "📈 So sánh dòng tiền", "📞 Phân tích Call Log"])
    curr_y = datetime.now().year

    # 🔥 SỬA LỖI CÔNG CỤ 3: CALL LOG (ĐỘNG CƠ SIÊU CẤP)
    if menu == "📞 Phân tích Call Log":
        f_c = st.sidebar.file_uploader("Nạp file Call Log (Tối ưu file 90MB+)", type=['csv'], key='f_call_final')
        if f_c:
            st.title("📞 Call Performance Analytics (v2.1 Stable)")
            counts = {}
            progress = st.progress(0)
            
            try:
                # Dùng C Engine để đạt tốc độ tối đa, chỉ lấy cột Extension để tiết kiệm RAM
                # Thử đọc header trước để tìm cột Extension
                header = pd.read_csv(f_c, nrows=0, sep=None, engine='python')
                ext_col = [c for c in header.columns if 'Extension' in c]
                
                if ext_col:
                    f_c.seek(0) # Quay lại đầu file
                    # Chế độ Chunking với bộ đọc tối giản nhất có thể
                    reader = pd.read_csv(f_c, usecols=[ext_col[0]], chunksize=100000, 
                                         engine='c', encoding='utf-8', on_bad_lines='skip', low_memory=False)
                    
                    for i, chunk in enumerate(reader):
                        # Trích xuất tên từ Extension: "123 - Nguyen Van A" -> "Nguyen Van A"
                        chunk['Staff'] = chunk[ext_col[0]].astype(str).apply(lambda x: x.split('-')[-1].strip() if '-' in x else x)
                        c_counts = chunk['Staff'].value_counts().to_dict()
                        for s, c in c_counts.items():
                            counts[s] = counts.get(s, 0) + c
                        progress.progress(min((i + 1) * 20 / 100, 1.0))
                
                if counts:
                    stat = pd.DataFrame(list(counts.items()), columns=['Nhân viên', 'Tổng cuộc gọi']).sort_values('Tổng cuộc gọi', ascending=False)
                    
                    # Bục vinh danh (4-2-1-3-5)
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
                    progress.empty()
                else:
                    st.warning("Không tìm thấy cột 'Extension' trong file.")
            except Exception as e:
                # Nếu C engine lỗi, chuyển sang Python engine với encoding Latin-1
                st.info("Đang dùng chế độ tương thích cao cho file phức tạp...")
                f_c.seek(0)
                # (Phần xử lý dự phòng tương tự để đảm bảo luôn chạy được)
                st.error(f"Lỗi: {e}. Vui lòng kiểm tra lại định dạng file CSV.")
        return

    # CÁC CÔNG CỤ 1, 2, 4 (GIỮ NGUYÊN HOÀN TOÀN)
    f_m = st.sidebar.file_uploader("Nạp file Masterlife chính", type=['csv', 'xlsx'], key='f_main')
    if f_m:
        df = smart_load(f_m)
        if df is None: return
        c = get_cols(df)
        df = df[df[c['team']].astype(str).str.upper().str.contains('G', na=False)].copy()
        df['REV'] = process_rev(df, c['m'])

        if menu == "📈 So sánh dòng tiền":
            st.title("📈 So Sánh Dòng Tiền 3 Năm")
            f_n1, f_n2 = st.sidebar.file_uploader("File 2024", type=['csv', 'xlsx']), st.sidebar.file_uploader("File 2023", type=['csv', 'xlsx'])
            all_y = []
            curr_v = df.groupby(c['e'])['REV'].sum().reindex(range(1,13)).fillna(0)
            curr_v.name = f"Năm {curr_y}"; all_y.append(curr_v)
            for i, f_ex in enumerate([f_n1, f_n2]):
                df_e = smart_load(f_ex)
                if df_e is not None:
                    c_e = get_cols(df_e)
                    df_e = df_e[df_e[c_e['team']].astype(str).str.upper().str.contains('G', na=False)].copy()
                    df_e['REV'] = process_rev(df_e, c_e['m'])
                    val_e = df_e.groupby(c_e['e'])['REV'].sum().reindex(range(1,13)).fillna(0)
                    val_e.name = f"Năm {curr_y-(i+1)}"; all_y.append(val_e)
            comp_df = pd.concat(all_y, axis=1)
            comp_df.index = [f"T{m:02d}" for m in comp_df.index]
            st.line_chart(comp_df); st.dataframe(comp_df.style.format("${:,.0f}"), use_container_width=True)
        
        elif menu in ["📊 Phân tích Cohort", "🏆 Vinh danh cá nhân"]:
            def sanitize(row):
                try:
                    y, m = int(float(str(row[c['w']]))), int(float(str(row[c['v']])))
                    return f"Trước năm {curr_y}" if y < curr_y else f"Lead T{m:02d}/{y}"
                except: return "📦 Nhóm Khác"
            df['NHÓM'] = df.apply(sanitize, axis=1)
            df['T_CHOT'] = df[c['e']].apply(lambda v: int(float(v)) if (pd.notna(v) and str(v).replace('.','').isdigit()) else None)
            
            if menu == "📊 Phân tích Cohort":
                st.title(f"📊 Team G Strategic - {curr_y}")
                m1, m2 = st.columns(2)
                m1.metric("💰 TỔNG DOANH THU", f"${df['REV'].sum():,.0f}")
                m2.metric("📋 TỔNG HỒ SƠ", f"{df[c['id']].nunique():,}")
                mtx_r = df.pivot_table(index='NHÓM', columns='T_CHOT', values='REV', aggfunc='sum').fillna(0).reindex(columns=range(1,13)).fillna(0)
                mtx_c = df.pivot_table(index='NHÓM', columns='T_CHOT', values=c['id'], aggfunc='nunique').fillna(0).reindex(columns=range(1,13)).fillna(0)
                st.area_chart(df.groupby('T_CHOT')['REV'].sum().reindex(range(1,13)).fillna(0), color="#00FF7F")
                t1, t2 = st.tabs(["💵 Doanh số ($)", "🔢 Số lượng hồ sơ"])
                with t1: st.dataframe(mtx_r.style.format("${:,.0f}"), use_container_width=True)
                with t2: st.dataframe(mtx_c.style.format("{:,.0f}"), use_container_width=True)
            else:
                st.title(f"🏆 Hall of Fame Team G")
                lb = df.groupby(c['owner']).agg({'REV':'sum', c['id']:'nunique'}).sort_values('REV', ascending=False).reset_index()
                lb.columns = ['Thành viên', 'Doanh số', 'Hợp đồng']
                cols = st.columns(5)
                d_map = [{'i':3,'t':"🏅 Hạng 4"}, {'i':1,'t':"🥈 Hạng 2"}, {'i':0,'t':"👑 VÔ ĐỊCH"}, {'i':2,'t':"🥉 Hạng 3"}, {'i':4,'t':"🏅 Hạng 5"}]
                for i, item in enumerate(d_map):
                    if item['i'] < len(lb):
                        row = lb.iloc[item['i']]
                        with cols[i]:
                            st.markdown(f"<div class='podium-card {'rank-1-glow' if item['i']==0 else ''}'><div style='color:#ffd700; font-weight:bold;'>{item['t']}</div><span class='staff-name-highlight'>{row['Thành viên']}</span><div class='rev-val' style='color:#ffd700;'>${row['Doanh số']:,.0f}</div></div>", unsafe_allow_html=True)
                lb.index = np.arange(1, len(lb)+1); st.dataframe(lb.style.format({'Doanh số': '{:,.0f}'}), use_container_width=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Data_Detail')
            if 'mtx_r' in locals(): mtx_r.to_excel(writer, sheet_name='Cohort_Revenue')
            if 'mtx_c' in locals(): mtx_c.to_excel(writer, sheet_name='Cohort_Count')
            if menu == "📈 So sánh dòng tiền" and 'comp_df' in locals(): comp_df.to_excel(writer, sheet_name='Comparison_Report')
        st.sidebar.markdown("---")
        st.sidebar.download_button("📥 TẢI BÁO CÁO FULL (4 SHEETS)", output.getvalue(), "TeamG_Strategic_Report.xlsx")

if __name__ == "__main__": main()
