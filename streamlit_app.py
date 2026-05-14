import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests

# 1. 页面基本配置
st.set_page_config(page_title="MDC 互动盘点 5.0", layout="centered")

# 2. 增强版 CSS (包含平滑滚动效果)
st.markdown("""
    <style>
    html { scroll-behavior: smooth; } /* 让滚动变得平滑，像电梯一样 */
    [data-testid="column"] { width: calc(50% - 0.5rem) !important; flex: 1 1 calc(50% - 0.5rem) !important; }
    #MainMenu, header, footer {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    /* 橙色横梁 */
    .slot::after {
        content: ""; position: absolute; bottom: -3px; left: 0;
        width: 100%; height: 4px; background: #fb8c00; border-radius: 2px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 提交函数 ---
def send_to_google_form(name, loc, p_type, note):
    form_id = "1FAIpQLScdB2DC7CKJKly5vaaqTykfo5wrsdMSIgy3I01KvxAUY_emJQ" 
    url = f"https://docs.google.com/forms/d/e/{form_id}/formResponse"
    payload = {
        "entry.1669427102": name, "entry.738175923": loc,     
        "entry.1676630815": p_type, "entry.914821861": note     
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

# --- 状态记忆 ---
if 'selected_area' not in st.session_state: st.session_state.selected_area = "A"
if 'selected_rack' not in st.session_state: st.session_state.selected_rack = "0.0"

# =========================================================
# 🏗️ 上半部分：货架展示区 (ID: top-zone)
# =========================================================
st.markdown('<div id="top-zone"></div>', unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; margin-top: -10px;'>🏗️ 货架布局展示</h3>", unsafe_allow_html=True)

sel_c1, sel_c2 = st.columns(2)
with sel_c1:
    areas = sorted(df['仓库'].dropna().unique().tolist())
    selected_area = st.selectbox("1. 库区", areas, index=areas.index(st.session_state.selected_area))
    st.session_state.selected_area = selected_area

with sel_c2:
    raw_racks = df[df['仓库'] == selected_area]['货架'].dropna().unique().tolist()
    sorted_racks = sorted(raw_racks, key=lambda x: int(float(x)))
    rack_options = [f"{int(float(x)):02d}" for x in sorted_racks]
    try: default_idx = sorted_racks.index(st.session_state.selected_rack)
    except: default_idx = 0
    selected_rack_display = st.selectbox("2. 货架", rack_options, index=default_idx)
    st.session_state.selected_rack = sorted_racks[rack_options.index(selected_rack_display)]

rack_code = f"{selected_area}{selected_rack_display}"

# 业务逻辑渲染
is_area_a = (selected_area == "A")
levels_raw = ['50.0','40.0','30.0','20.0','10.0','0.0'] if is_area_a else ['40.0','30.0','20.0','10.0','0.0']
bps, view_sections, slot_h = (3, 2, "45px") if is_area_a else (2, 3, "55px")
all_bins_raw = df[(df['仓库'] == selected_area) & (df['货架'] == st.session_state.selected_rack)]['位置.1'].dropna().unique().tolist()
all_bins = sorted(all_bins_raw, key=lambda x: int(float(x)), reverse=True)

if 'offset' not in st.session_state: st.session_state.offset = 0
total_bins_view = bps * view_sections

nav_cols = st.columns([1, 2, 2, 1])
with nav_cols[1]:
    if st.button("⬅️ 上一页", use_container_width=True):
        st.session_state.offset = max(0, st.session_state.offset - total_bins_view)
with nav_cols[2]:
    if st.button("下一页 ➡️", use_container_width=True):
        if st.session_state.offset + total_bins_view < len(all_bins):
            st.session_state.offset += total_bins_view

current_bins = all_bins[st.session_state.offset : st.session_state.offset + total_bins_view]

# 货架图：点击后跳转锚点并触发 JS 滚动
def get_shelf_html(bins, lvls, section_size, h):
    css = f"<style>.shelf-wrapper{{display:flex;justify-content:center;background:white;padding-top:10px;}}.pillar{{width:10px;background:#3498db;margin:0 4px;border-radius:5px;}}.bin-col{{display:flex;flex-direction:column;width:62px;}}.slot{{height:{h};border:1px solid #eee;margin:2px 1px;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:13px;text-decoration:none;border-radius:2px;position:relative;}}.slot::after{{content:'';position:absolute;bottom:-3px;left:0;width:100%;height:4px;background:#fb8c00;border-radius:2px;}}.empty{{background:#fff;color:#ccc;}}.stocked{{background:#1976D2;color:#fff;}}.disabled{{background:#f5f5f5;color:#ff5252;pointer-events:none;}}.bin-label{{text-align:center;font-size:10px;padding:8px 0;color:#777;font-weight:bold;}}</style>"
    html = '<div class="shelf-wrapper">'
    for i, b_num in enumerate(bins):
        if i % section_size == 0: html += '<div class="pillar"></div>'
        bin_str = f"{int(float(b_num)):02d}"
        html += '<div class="bin-col">'
        for lvl in lvls:
            lvl_str = f"{int(float(lvl)):02d}"
            full_id = f"{rack_code}{bin_str}{lvl_str}"
            row = df[df['位置/位置名称'] == full_id]
            status = row['状态'].values[0] if not row.empty else "可用"
            if status != "可用":
                html += '<div class="slot disabled">❌</div>'
            else:
                bg = "stocked" if full_id in has_stock_list else "empty"
                # 重点：href 链接带锚点 #feedback-zone
                html += f'<a href="?check_loc={full_id}#feedback-zone" target="_self" class="slot {bg}">{lvl_str}</a>'
        html += f'<div class="bin-label">{bin_str}</div></div>'
        if i == len(bins) - 1: html += '<div class="pillar"></div>'
    return css + html + '</div>'

components.html(get_shelf_html(current_bins, levels_raw, bps, slot_h), height=380)

# =========================================================
# 🏗️ 下半部分：反馈反馈区 (ID: feedback-zone)
# =========================================================
st.markdown('<br><br><div id="feedback-zone"></div>', unsafe_allow_html=True)
st.divider()

q_params = st.query_params
target_loc = q_params.get("check_loc", "尚未选择库位")

st.markdown(f"<h3 style='text-align: center; color: #ff4b4b;'>🚨 差异反馈记录</h3>", unsafe_allow_html=True)
st.info(f"📍 当前针对库位：**{target_loc}**")

# 如果没选库位，表单也会显示，但提交按钮不可用或提醒选择
with st.form("inventory_form", clear_on_submit=True):
    staff_name = st.text_input("盘点人姓名 *", placeholder="请输入姓名")
    issue_type = st.radio("异常情况", ["系统有货-实物无", "系统无货-实物有", "库位停用-实物有货"], horizontal=True)
    memo = st.text_area("备注说明")
    
    c1, c2 = st.columns(2)
    with c1:
        submit_btn = st.form_submit_button("✅ 确认提交并回顶部", use_container_width=True)
        if submit_btn:
            if "尚未选择" in target_loc:
                st.error("请先点击上方货架中的库位！")
            elif not staff_name:
                st.error("请填写姓名")
            else:
                if send_to_google_form(staff_name, target_loc, issue_type, memo):
                    st.success("提交成功！")
                    # 清除参数并触发刷新，回到页面顶部
                    st.query_params.clear()
                    st.rerun()
    with c2:
        if st.form_submit_button("❌ 取消重置回顶部", use_container_width=True):
            st.query_params.clear()
            st.rerun()

# 💡 页面底端留白，确保“电梯”能滚得动
st.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True)