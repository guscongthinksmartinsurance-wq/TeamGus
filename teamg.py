import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from io import BytesIO

# --- 1. GIAO DIỆN & STYLE (GIỮ NGUYÊN) ---
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

# --- 2. HÀM HỖ TRỢ ĐỌC FILE (CÔNG CỤ 1, 2, 3) ---
def smart_load(file):
    try:
        if file.name.endswith(('.xlsx', '.xls')):
            return pd.read_excel(file, skiprows=0) # Sẽ tự động tìm header trong hàm main
        file.seek(0)
        return pd.read_csv(file, sep=None, engine='python', encoding='utf-8', errors='ignore')
    except: return None

# --- 3. ĐỘNG CƠ MẠNH MẼ CHO CALL LOG (XỬ LÝ FILE 90MB+) ---
def process_call_log_heavy(file):
    st.title("📞 Call Performance Analytics (Engine V2)")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Sử dụng Chunking để không bị treo RAM
        chunk_size = 50000
        counts = {}
        
        # Đọc file theo từng phần nhỏ
        for i, chunk in enumerate(pd.read_csv(file, sep=None, engine='python', encoding='utf-8-sig', chunksize=chunk_size, on_bad_lines='skip')):
            status_text.text(f"Đang xử lý gói dữ liệu thứ {i+1}...")
            
            # Chỉ lấy các cột cần thiết để tối ưu
            if 'Extension' in chunk.columns:
                # Trích xuất tên nhân viên từ Extension (Logic cũ của anh)
                chunk['Staff'] = chunk['Extension'].apply(lambda x: str(x).split('-')[-1].strip() if '-' in str(x) else (str(x) if str(x)!='nan' else "Ẩn danh"))
                
                # Cộng dồn kết quả
                current_counts = chunk['Staff'].value_counts().to_dict()
                for staff, count in current_counts.items():
                    counts[staff] = counts.get(staff, 0) + count
            
            progress_bar.progress(min((i + 1) * 10 / 100, 1.0))

        # Chuyển kết quả về DataFrame để vinh danh
        stat = pd.DataFrame(list(counts.items()), columns=['Nhân viên', 'Tổng cuộc gọi']).sort_values('Tổng cuộc gọi', ascending=False)
        
        # KHÔI PHỤC BẢNG VINH DANH (4-2-1-3-5)
        st.subheader("🏆 Top 5 Chiến thần Telesale")
        cols_v = st.columns(5)
        d_map = [{'i':3,'t':"🏅 Hạng 4"}, {'i':1,'t':"🥈 Hạng 2"}, {'i':0,'t':"👑 VÔ ĐỊCH"}, {'i':2,'t':"🥉 Hạng 3"}, {'i':4,'t':"🏅 Hạng 5"}]
        
        top_5 = stat.head(5).reset_index(drop=True)
        for i, item in enumerate(d_map):
            idx = item['i']
            if idx < len(top_5):
                row = top_5.iloc[idx]
                with cols_v[i]:
                    st.markdown(f"""<div class="podium-card {'rank-call-glow' if idx==0 else ''}">
                        <div style="color:#00D4FF; font-weight:bold;">{item['t']}</div>
                        <span class="staff-name-highlight">{row['Nhân viên']}</span>
                        <div class="rev-val" style="color:#00D4FF;">{row['Tổng cuộc gọi']:,}</div>
                    </div>""", unsafe_allow_html=True)
        
        # Bảng kê chi tiết
        stat.index = np.arange(1, len(stat) + 1)
        st.markdown("---")
        st.dataframe(stat, use_container_width=True)
        
        status_text.text("✅ Hoàn tất xử lý file lớn!")
        progress_bar.empty()
        
    except Exception as e:
        st.error(f"Lỗi động cơ xử lý: {e}")

# --- 4. CÔNG CỤ 1, 2, 3 (GIỮ NGUYÊN LOGIC CŨ) ---
# [Đoạn này giữ nguyên các hàm process_team_g và process_comparison_v2 như bản trước của chúng ta]
# (Em tóm lược để anh dễ nhìn, khi code em sẽ bê nguyên si logic chuẩn vào)

# --- 5. ĐIỀU HƯỚNG ---
menu = st.sidebar.radio("Chọn công cụ xem:", ["📊 Phân tích Cohort", "🏆 Vinh danh cá nhân", "📈 So sánh dòng tiền", "📞 Phân tích Call Log"])

if menu == "📞 Phân tích Call Log":
    f_call = st.sidebar.file_uploader("Nạp file Call Log (Hỗ trợ file cực lớn)", type=['csv'], key='fcall_v2')
    if f_call:
        process_call_log_heavy(f_call)
# ... [Các phần Menu khác giữ nguyên logic nạp file Masterlife]
