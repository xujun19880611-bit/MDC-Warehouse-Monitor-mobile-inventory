import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime
import requests

# 1. 页面配置（必须是第一行）
st.set_page_config(page_title="MDC 互动盘点", layout="centered")

# 2. 强制按钮并排及界面优化 CSS
st.markdown("""
    <style>
    /* 强制让 columns 在手机端不堆叠 */
    [data-testid="column"] {
        width: calc(25% - 1rem) !important;
        flex: 1 1 calc(25% - 1rem) !important;
        min-width: 50px !important;
    }
    /* 隐藏顶部多余的空白和菜单，减少干扰 */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    </style>
""", unsafe_allow_html=True)

# --- 核心逻辑：Google Form 提交 ---
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
        res = requests.post(url, data=payload, timeout=5)
        return res.status_code == 200
    except: return False

# --- 数据读取 ---
@st.cache_data
def load_data():
    df = pd.read_csv('SGF.csv', dtype=str)
    if '状态' in df.columns:
        df['状态'] = df['状态'].fillna('').str.strip()
    stock_list = df[df['产品参考编码'].notna()]['位置/位置名称'].unique().tolist()
    return df, stock_list

df, has_stock_list = load_data()

# --- 侧边栏：仅放筛选器 ---
with st.sidebar:
    st.header("⚙️ 筛选")
    areas = sorted(df['仓库'].dropna().unique().tolist())
    selected_area = st.selectbox("库区", areas)
    raw_racks = df[df['仓库'] == selected_area]['货架'].dropna().unique().tolist()
    sorted_racks = sorted(raw_racks, key=lambda x: int(float(x)))
    selected_rack_raw = st.selectbox("货架", sorted_racks, format_func=lambda x: f"{selected_area}{int(float(x)):02d}")
    rack_code = f"{selected_area}{int(float(selected_rack_raw)):02d}"

# --- 货架参数 ---
is_area_a = (selected_area == "A")
levels_raw = ['50.0','40.0','30.0','20.0','10.0','0.0'] if is_area_a else ['40.0','30.0','20.0','10.0','0.0']
bps, view_sections, slot_h = (3, 2, "45px") if is_area_a else (2, 3, "55px")
total_bins_view = bps * view_sections
raw_bins = df[(df['仓库'] == selected_area) & (df['货架'] == selected_rack_raw)]['位置.1'].dropna().unique().tolist()
all_bins = sorted(raw_bins, key=lambda x: int(float(x)), reverse=True)

if 'offset' not in st.session_state: st.session_state.offset = 0

# --- 【修复重点】统一标题与布局 ---
# 使用一个容器来确保标题在页面最上方且唯一
title_container = st.container()
q_params = st.query_params

# 如果有参数，标题显示“反馈中”，否则显示“正常盘点”
if "check_loc" in q_params:
    title_container.markdown(f"<h3 style='text-align: center; color: #ff4b4b;'>🚨 {rack_code} 反馈模式</h3>", unsafe_allow_html=True)
else:
    title_container.markdown(f"<h3 style='text-align: center;'>🏗️ {rack_code} 盘点</h3>", unsafe_allow_html=True)

# 翻页按钮（强制并排）
nav_cols = st.columns(4)
with nav_cols[1]:
    if st.button("⬅️", use_container_width=True):
        st.session_state.offset = max(0, st.session_state.offset - total_bins_view)
with nav_cols[2]:
    if st.button("➡️", use_container_width=True):
        if st.session_state.offset + total_bins_view < len(all_bins):
            st.session_state.offset += total_bins_view

current_bins = all_bins[st.session_state.offset : st.session_state.offset + total_bins_view]

# 货架渲染组件（保持方块化）
def get_shelf_html(bins, lvls, section_size, h):
    css = f"<style>.shelf-wrapper{{display:flex;justify-content:center;background:white;}}.pillar{{width:10px;background:#3498db;margin:0 3px;border-radius:5px;}}.bin-col{{display:flex;flex-direction:column;width:62px;}}.slot{{height:{h};border:1px solid #eee;margin:1px;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:13px;text-decoration:none;border-radius:4px;}}.empty{{background:#fff;color:#ccc;}}.stocked{{background:#1976D2;color:#fff;}}.disabled{{background:#f5f5f5;color:#ff5252;pointer-events:none;}}.bin-label{{text-align:center;font-size:10px;padding:4px 0;color:#777;}}</style>"
    html = '<div class="shelf-wrapper">'
    for i, b_num in enumerate(bins):
        if i % section_size == 0: html += '<div class="pillar"></div>'
        bin_str = f"{int(float(b_num)):02d}"
        html += '<div class="bin-col">'
        for lvl in lvls:
            lvl_str = f"{int(float(lvl)):02d}"
            full_id = f"{rack_code}{bin_str}{lvl_str}"
            status = df[df['位置/位置名称'] == full_id]['状态'].values[0] if not df[df['位置/位置名称'] == full_id].empty else "可用"
            if status != "可用":
                html += '<div class="slot disabled">❌</div>'
            else:
                bg = "stocked" if full_id in has_stock_list else "empty"
                html += f'<a href="?check_loc={full_id}" target="_self" class="slot {bg}">{lvl_str}</a>'
        html += f'<div class="bin-label">{bin_str}</div></div>'
        if i == len(bins) - 1: html += '<div class="pillar"></div>'
    return css + html + '</div>'

components.html(get_shelf_html(current_bins, levels_raw, bps, slot_h), height=360)

# --- 反馈表单区 ---
if "check_loc" in q_params:
    target_loc = q_params["check_loc"]
    st.markdown("---")
    st.warning(f"📍 正在反馈: **{target_loc}**")
    with st.form("main_feedback_form", clear_on_submit=True):
        name = st.text_input("您的姓名 *")
        issue = st.radio("异常情况", ["系统有货-实物无", "系统无货-实物有", "库位停用-实物有货"], horizontal=True)
        note = st.text_input("备注")
        
        b1, b2 = st.columns(2)
        with b1:
            if st.form_submit_button("确认提交", use_container_width=True):
                if not name: st.error("请填姓名")
                elif send_to_google_form(name, target_loc, issue, note):
                    st.success("✅ 提交成功")
                    st.query_params.clear() # 清除 URL 参数
                    st.rerun() # 彻底刷新页面
        with b2:
            if st.form_submit_button("取消", use_container_width=True):
                st.query_params.clear()
                st.rerun()