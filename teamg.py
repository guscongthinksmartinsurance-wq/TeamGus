import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from io import BytesIO

# --- 1. CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="TMC Strategic System", layout="wide")
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
    div.stButton > button:first-child {
        background-color: #00D4FF; color: white; width: 100%; border-radius: 8px; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HÀM ĐỌC FILE THÔNG MINH (SỬA LỖI UNICODE) ---
def smart_load_call_log(file):
    if file.name.endswith(('.xlsx', '.xls')):
        return pd.read_excel(file)
    
    # Nếu là file CSV, thử nhiều bảng mã để tránh lỗi UnicodeDecodeError
    encodings = ['utf-8-sig', 'latin1', 'cp1252', 'utf-8']
    for enc in encodings:
        try:
            file.seek(0)
            return pd.read_csv(file, encoding=enc)
        except UnicodeDecodeError:
            continue
    # Cuối cùng nếu vẫn lỗi, đọc và bỏ qua các ký tự gây lỗi
    file.seek(0)
    return pd.read_csv(file, encoding='utf-8', errors='ignore')

def duration_to_seconds(time_str):
    try:
        if pd.isna(time_str) or str(time_str).strip() == "": return 0
        parts = list(map(int, str(time_str).split(':')))
        if len(parts) == 3: return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2: return parts[0] * 60 + parts[1]
        return 0
    except: return 0

def seconds_to_hms(seconds):
    h, m, s = int(seconds // 3600), int((seconds % 3600) // 60), int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

# --- 3. CHƯƠNG TRÌNH CHÍNH ---
def main():
    st.sidebar.title("🛡️ TMC Management")
    menu = st.sidebar.radio("Chọn công cụ:", ["📊 Phân tích Cohort", "🏆 Vinh danh Doanh số", "📞 Phân tích Call Log"])

    # --- MODULE A: MASTERLIFE ---
    if menu in ["📊 Phân tích Cohort", "🏆 Vinh danh Doanh số"]:
        f_master = st.sidebar.file_uploader("Nạp file Masterlife", type=['csv', 'xlsx'], key="master")
        if f_master:
            # (Phần này giữ nguyên logic lọc Team G và Doanh số của bạn)
            st.info("Module Masterlife đang sẵn sàng.")

    # --- MODULE B: CALL LOG (SỬA LỖI & THÊM NÚT RUN) ---
    elif menu == "📞 Phân tích Call Log":
        st.title("📞 Call Performance Analytics")
        f_call = st.sidebar.file_uploader("Nạp file Log Cuộc gọi", type=['csv', 'xlsx'], key="call_file")
        
        # Nút Run để kích hoạt tính toán
        run_call = st.sidebar.button("🚀 Chạy phân tích cuộc gọi")
        
        if f_call and run_call:
            with st.spinner('Đang xử lý dữ liệu cuộc gọi...'):
                df_call = smart_load_call_log(f_call)
                
                # Logic bù trừ: From trống lấy Extension
                df_call['Call_Ref'] = df_call['From'].fillna(df_call['Extension'])
                
                def parse_staff(row):
                    ext = str(row['Extension']).strip()
                    if '-' in ext: return ext.split('-')[-1].strip()
                    if ext.lower() != 'nan' and ext != '': return ext
                    return "Ẩn danh"
                
                df_call['Staff'] = df_call.apply(parse_staff, axis=1)
                df_call['Duration_Sec'] = df_call['Duration'].apply(duration_to_seconds)
                
                # Tổng hợp
                stats = df_call.groupby('Staff').agg({'Call_Ref': 'count', 'Duration_Sec': 'sum'}).reset_index()
                stats.columns = ['Nhân viên', 'Tổng cuộc gọi', 'Giây']
                stats['Thời lượng'] = stats['Giây'].apply(seconds_to_hms)
                stats = stats.sort_values(by='Tổng cuộc gọi', ascending=False)

                # Vinh danh Top 5
                st.subheader("🏆 Top 5 Chiến thần Telesale")
                top_5 = stats.head(5)
                cols = st.columns(5)
                medals = ["🥇 Hạng 1", "🥈 Hạng 2", "🥉 Hạng 3", "🏅 Hạng 4", "🏅 Hạng 5"]
                for i, (idx, row) in enumerate(top_5.iterrows()):
                    with cols[i]:
                        st.markdown(f"""<div class="call-card">
                            <div style="color:#00D4FF;font-weight:bold;">{medals[i]}</div>
                            <div style="color:white;font-weight:bold;margin:5px 0;">{row['Nhân viên']}</div>
                            <div style="color:#00D4FF;font-size:1.6rem;font-weight:bold;">{row['Tổng cuộc gọi']}</div>
                            <div style="color:#8B949E;font-size:0.7rem;">{row['Thời lượng']}</div>
                        </div>""", unsafe_allow_html=True)
                
                st.markdown("---")
                st.dataframe(stats[['Nhân viên', 'Tổng cuộc gọi', 'Thời lượng']], use_container_width=True)
                st.bar_chart(stats.set_index('Nhân viên')['Tổng cuộc gọi'])
        
        elif f_call and not run_call:
            st.warning("👈 Nhấn nút **'🚀 Chạy phân tích cuộc gọi'** ở thanh bên để xem kết quả.")

if __name__ == "__main__":
    main()
