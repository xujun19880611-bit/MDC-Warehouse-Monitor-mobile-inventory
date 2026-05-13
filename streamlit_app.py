import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime
import requests

# 页面配置
st.set_page_config(page_title="MDC 互动盘点", layout="centered")

# --- 强制按钮并排的 CSS ---
st.markdown("""
    <style>
    /* 强制让 columns 在手机端不堆叠，保持水平排列 */
    [data-testid="column"] {
        width: calc(25% - 1rem) !important;
        flex: 1 1 calc(25% - 1rem) !important;
        min-width: 50px !important;
    }
    /* 隐藏手机端可能出现的重复侧边栏控制按钮 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 1. Google Form 提交函数 (保持不变) ---
def send_to_google_form(name, loc, p_type, note):
    form_id = "1FAIpQLScdB2DC7CKJKly5vaaqTykfo5wrsdMSIgy3I01KvxAUY_emJQ" 
    url = f"https://docs.google.com/forms/d/e/{form_id}/formResponse"
    payload = {
        "entry.1669427102": name,   
        "entry.738175923": loc,     
        "entry.1676630815": p_type, 
        "entry.914821861": note     
    }
    try:
        res = requests.post(url, data=payload)
        return res.status_code == 200
    except: return False

# --- 2. 数据加载 ---
@st.cache_data
def load_and_process_data():
    df = pd.read_csv('SGF.csv', dtype=str)
    if '状态' in df.columns:
        df['状态'] = df['状态'].fillna('').str.strip()
    structure = df[df['产品参考编码'].isna()].copy()
    stock_locations = df[df['产品参考编码'].notna()]['位置/位置名称'].unique().tolist()
    return structure, stock_locations

df_struct, has_stock_list = load_and_process_data()

# --- 3. 侧边栏：仅保留货架选择器，避免逻辑重复 ---
with st.sidebar:
    st.header("⚙️ 筛选")
    areas = sorted(df_struct['仓库'].dropna().unique().tolist())
    selected_area = st.selectbox("库区", areas)
    raw_racks = df_struct[df_struct['仓库'] == selected_area]['货架'].dropna().unique().tolist()
    sorted_racks = sorted(raw_racks, key=lambda x: int(float(x)))
    selected_rack_raw = st.selectbox("货架", sorted_racks, format_func=lambda x: f"{selected_area}{int(float(x)):02d}")
    rack_code = f"{selected_area}{int(float(selected_rack_raw)):02d}"

# --- 4. 货架参数与翻页 ---
is_area_a = (selected_area == "A")
levels_raw = ['50.0','40.0','30.0','20.0','10.0','0.0'] if is_area_a else ['40.0','30.0','20.0','10.0','0.0']
bps, view_sections, slot_h = (3, 2, "45px") if is_area_a else (2, 3, "55px")

total_bins_view = bps * view_sections
raw_bins = df_struct[(df_struct['仓库'] == selected_area) & (df_struct['货架'] == selected_rack_raw)]['位置.1'].dropna().unique().tolist()
all_bins = sorted(raw_bins, key=lambda x: int(float(x)), reverse=True)

if 'offset' not in st.session_state: st.session_state.offset = 0

st.markdown(f"<h3 style='text-align: center; margin-bottom: 0px;'>🏗️ {rack_code} 盘点</h3>", unsafe_allow_html=True)

# --- 5. 修复后的左右按钮 (并排结构) ---
nav_cols = st.columns(4) # 创建4列，利用中间两列放置按钮
with nav_cols[1]:
    if st.button("⬅️", use_container_width=True):
        st.session_state.offset = max(0, st.session_state.offset - total_bins_view)
with nav_cols[2]:
    if st.button("➡️", use_container_width=True):
        if st.session_state.offset + total_bins_view < len(all_bins):
            st.session_state.offset += total_bins_view

current_bins = all_bins[st.session_state.offset : st.session_state.offset + total_bins_view]

# --- 6. 货架 HTML 渲染 ---
def render_shelf(bins, lvls, section_size, h):
    css = f"""
    <style>
        .shelf-wrapper {{ display: flex; justify-content: center; padding: 5px 0; background: white; }}
        .pillar {{ width: 10px; background: #3498db; border-radius: 5px; margin: 0 3px; }}
        .bin-col {{ display: flex; flex-direction: column; width: 62px; }}
        .slot {{
            height: {h}; border: 1.5px solid #eee; margin: 1px;
            display: flex; align-items: center; justify-content: center;
            font-weight: bold; font-size: 13px; text-decoration: none; border-radius: 4px;
        }}
        .empty {{ background: #ffffff; color: #ccc; }} 
        .stocked {{ background: #1976D2; color: #fff; }} 
        .disabled {{ background: #f5f5f5; color: #ff5252; pointer-events: none; }} 
        .bin-label {{ text-align: center; font-size: 10px; padding: 4px 0; color: #777; font-weight: bold; }}
    </style>
    """
    html = '<div class="shelf-wrapper">'
    for i, b_num in enumerate(bins):
        if i % section_size == 0: html += '<div class="pillar"></div>'
        bin_str = f"{int(float(b_num)):02d}"
        html += '<div class="bin-col">'
        for lvl in lvls:
            lvl_str = f"{int(float(lvl)):02d}"
            full_id = f"{rack_code}{bin_str}{lvl_str}"
            row = df_struct[df_struct['位置/位置名称'] == full_id]
            status = row['状态'].values[0] if not row.empty else "可用"
            if status != "可用":
                html += f'<div class="slot disabled">❌</div>'
            else:
                bg = "stocked" if full_id in has_stock_list else "empty"
                html += f'<a href="?check_loc={full_id}" target="_self" class="slot {bg}">{lvl_str}</a>'
        html += f'<div class="bin-label">{bin_str}</div></div>'
        if i == len(bins) - 1: html += '<div class="pillar"></div>'
    html += '</div>'
    return css + html

components.html(render_shelf(current_bins, levels_raw, bps, slot_h), height=380)

# --- 7. 反馈表单 (彻底移除侧边栏触发，仅在主页显示) ---
q_params = st.query_params
if "check_loc" in q_params:
    target_loc = q_params["check_loc"]
    st.markdown("---")
    # 表单外框，手机端更显眼
    with st.container():
        st.warning(f"📍 异常上报: **{target_loc}**")
        with st.form("feedback_form", clear_on_submit=True):
            # 员工姓名设置为 Session State 记忆，避免重复输入
            staff_name = st.text_input("姓名 *")
            issue_type = st.radio("问题类型", ["系统有货，实际无货", "系统无货，实际有货", "系统不可用，实际有货"], horizontal=True)
            memo = st.text_input("备注")
            
            btn_cols = st.columns(2)
            with btn_cols[0]:
                if st.form_submit_button("提交报表", use_container_width=True):
                    if not staff_name:
                        st.error("请填姓名")
                    elif send_to_google_form(staff_name, target_loc, issue_type, memo):
                        st.success("✅ 已同步")
                        st.query_params.clear()
                        st.rerun()
            with btn_cols[1]:
                if st.form_submit_button("取消", use_container_width=True):
                    st.query_params.clear()
                    st.rerun()