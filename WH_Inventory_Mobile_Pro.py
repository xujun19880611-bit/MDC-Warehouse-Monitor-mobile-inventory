import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. 页面配置 ---
st.set_page_config(page_title="MDC Mobile Pro (Cloud)", layout="wide")

# --- 2. Google Sheets 连接逻辑 ---
# 建立连接
conn = st.connection("gsheets", type=GSheetsConnection)

def save_to_gsheets(loc, status, staff):
    # 读取现有数据
    existing_data = conn.read(ttl=0) # ttl=0 确保每次读取最新
    
    # 准备新数据
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_entry = pd.DataFrame([{
        "loc": loc,
        "real_status": status,
        "staff": staff,
        "update_time": now
    }])
    
    # 合并数据（如果库位已存在则更新，否则追加）
    if not existing_data.empty:
        # 去掉旧的重复记录
        updated_data = pd.concat([existing_data, new_entry], ignore_index=True)
        updated_data = updated_data.drop_duplicates(subset=['loc'], keep='last')
    else:
        updated_data = new_entry
        
    # 写回 Google Sheets
    conn.update(data=updated_data)
    st.cache_data.clear() # 清除缓存强制刷新视图

def get_audited_dict():
    try:
        df = conn.read(ttl=5) # 缓存5秒，平衡性能和实时性
        if df.empty: return {}
        return dict(zip(df['loc'], df['real_status']))
    except:
        return {}

# --- 3. 样式配置 (保持不变) ---
st.markdown("""
    <style>
    .bin-box { width: 34px; height: 30px; display: flex; align-items: center; justify-content: center; border-radius: 2px; font-size: 10px; font-weight: bold; border: 1px solid #f0f0f0; background-color: white; transition: 0.3s; }
    .status-used { background-color: #3498db !important; color: white; border: none; }
    .status-empty { background-color: #2ecc71 !important; color: white; border: none; }
    .status-disabled { background-color: #95a5a6 !important; color: white; border: none; }
    .status-selected { border: 3px solid #FF4B4B !important; transform: scale(1.15); z-index: 100; box-shadow: 0 0 12px rgba(255, 75, 75, 0.9); }
    .status-audited { position: relative; }
    .status-audited::after { content: '✅'; position: absolute; top: -6px; right: -6px; font-size: 10px; }
    .total-card { background: linear-gradient(135deg, #1e3c72, #2a5298); padding: 15px; border-radius: 10px; color: white; text-align: center; margin-bottom: 20px; }
    .shelf-container { display: flex; flex-wrap: nowrap; overflow-x: auto; padding: 15px; background: #fff; border: 1px solid #eee; }
    .orange-beam { width: 100%; height: 3px; background-color: #ff9800; margin: 1px 0; }
    .pillar { width: 0; height: 200px; border-left: 3px dotted #3498db; margin: 0 10px; opacity: 0.6; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. 数据处理 (load_data 逻辑同前) ---
@st.cache_data(ttl=60)
def load_data():
    if not os.path.exists("SGF.csv"): return None, None
    # ... (此处省略与之前相同的 Pandas 处理代码，请保留原样) ...
    # 确保返回 l_map, wh_stats
    return l_map, wh_stats

l_map, wh_stats = load_data()
audited_data = get_audited_dict() # 从 Google Sheets 获取

# --- 5. 侧边栏与主界面 ---
# 这一部分逻辑与之前的联动版完全一致，只需将原来的 save_audit 替换为新定义的 save_to_gsheets 即可。

if l_map:
    # ... (语言切换逻辑) ...
    
    with st.sidebar:
        # ... (仓库、货道、库位三级联动选择器) ...
        if st.sidebar.button("确认提交 (Confirm)"):
            with st.spinner("正在同步到云端表格..."):
                save_to_gsheets(loc_input, new_status, staff)
                st.sidebar.success("同步成功！")
                st.rerun()

    # --- 6. 绘图逻辑 (保持不变) ---
    # ... (使用 l_map 和 audited_data 绘图) ...

    # 盘点历史：直接显示 Google Sheets 的最新内容
    with st.expander("🕒 实时云端记录 (Google Sheets)"):
        df_view = conn.read(ttl=0)
        st.dataframe(df_view.sort_values("update_time", ascending=False).head(10))

else:
    st.error("数据加载失败。")