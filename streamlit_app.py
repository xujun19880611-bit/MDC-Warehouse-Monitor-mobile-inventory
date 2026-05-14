import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests

# 1. 页面基本配置
st.set_page_config(page_title="MDC 互动盘点 9.0", layout="centered")

# 2. 手机端样式优化
st.markdown("""
    <style>
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

@st.cache_data
def load_data():
    df = pd.read_csv('SGF.csv', dtype=str)
    if '状态' in df.columns:
        df['状态'] = df['状态'].fillna('').str.strip()
    stock_list = df[df['产品参考编码'].notna()]['位置/位置名称'].unique().tolist()
    return df, stock_list

df, has_stock_list = load_data()

# --- 状态记忆 ---
if 's_area' not in st.session_state: st.session_state.s_area = "A"
if 's_rack' not in st.session_state: st.session_state.s_rack = "0.0"

# =========================================================
# 🏗️ 上部分：货架选择与浏览
# =========================================================
st.markdown("<h3 style='text-align: center;'>🏗️ 货架布局展示</h3>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    areas = sorted(df['仓库'].dropna().unique().tolist())
    st.session_state.s_area = st.selectbox("1. 库区", areas, index=areas.index(st.session_state.s_area))
with c2:
    raw_racks = df[df['仓库'] == st.session_state.s_area]['货架'].dropna().unique().tolist()
    sorted_racks = sorted(raw_racks, key=lambda x: int(float(x)))
    rack_labels = [f"{int(float(r)):02d}" for r in sorted_racks]
    try: d_idx = sorted_racks.index(st.session_state.s_rack)
    except: d_idx = 0
    sel_label = st.selectbox("2. 货架", rack_labels, index=d_idx)
    st.session_state.s_rack = sorted_racks[rack_labels.index(sel_label)]

rack_code = f"{st.session_state.s_area}{sel_label}"

# 业务逻辑
is_a = (st.session_state.s_area == "A")
lvls = ['50.0','40.0','30.0','20.0','10.0','0.0'] if is_a else ['40.0','30.0','20.0','10.0','0.0']
bps, vs, h = (3, 2, "45px") if is_a else (2, 3, "55px")

all_bins = sorted(df[(df['仓库'] == st.session_state.sel_area if 'sel_area' in st.session_state else df['仓库'] == st.session_state.s_area) & (df['货架'] == st.session_state.s_rack)]['位置.1'].dropna().unique().tolist(), key=lambda x: int(float(x)), reverse=True)
if 'offset' not in st.session_state: st.session_state.offset = 0
current_bins = all_bins[st.session_state.offset : st.session_state.offset + (bps * vs)]

# 翻页按钮
n1, n2, n3, n4 = st.columns([1,2,2,1])
with n2: 
    if st.button("⬅️ 上页"): st.session_state.offset = max(0, st.session_state.offset - (bps * vs))
with n3:
    if st.button("下页 ➡️"): 
        if st.session_state.offset + (bps * vs) < len(all_bins):
            st.session_state.offset += (bps * vs)

# 货架渲染（取消锚点跳转，仅改变URL参数）
def get_html(bins, levels, section_size, sh):
    css = f"<style>.shelf-wrapper{{display:flex;justify-content:center;background:white;padding-top:10px;}}.pillar{{width:10px;background:#3498db;margin:0 4px;border-radius:5px;}}.bin-col{{display:flex;flex-direction:column;width:62px;}}.slot{{height:{sh};border:1px solid #eee;margin:2px 1px;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:13px;text-decoration:none;border-radius:2px;position:relative;}}.slot::after{{content:'';position:absolute;bottom:-3px;left:0;width:100%;height:4px;background:#fb8c00;border-radius:2px;}}.empty{{background:#fff;color:#ccc;}}.stocked{{background:#1976D2;color:#fff;}}.disabled{{background:#f5f5f5;color:#ff5252;pointer-events:none;}}.bin-label{{text-align:center;font-size:10px;padding:8px 0;color:#777;font-weight:bold;}}</style>"
    html = '<div class="shelf-wrapper">'
    for i, b_num in enumerate(bins):
        if i % section_size == 0: html += '<div class="pillar"></div>'
        bin_str = f"{int(float(b_num)):02d}"
        html += '<div class="bin-col">'
        for lvl in levels:
            l_str = f"{int(float(lvl)):02d}"
            fid = f"{rack_code}{bin_str}{l_str}"
            row = df[df['位置/位置名称'] == fid]
            status = row['状态'].values[0] if not row.empty else "可用"
            if status != "可用":
                html += '<div class="slot disabled">❌</div>'
            else:
                bg = "stocked" if fid in has_stock_list else "empty"
                # target="_self" 确保在主页面更新参数
                html += f'<a href="?loc={fid}" target="_self" class="slot {bg}">{l_str}</a>'
        html += f'<div class="bin-label">{bin_str}</div></div>'
        if i == len(bins) - 1: html += '<div class="pillar"></div>'
    return css + html + '</div>'

components.html(get_html(current_bins, lvls, bps, h), height=380)

# =========================================================
# 🏗️ 下部分：手动下滑反馈区
# =========================================================
st.markdown("<br><br>---<br>", unsafe_allow_html=True)
q_params = st.query_params
target_loc = q_params.get("loc", "未选择")

st.markdown(f"<h3 style='text-align: center; color: #ff4b4b;'>🚨 差异反馈记录</h3>", unsafe_allow_html=True)
st.warning(f"当前选中：**{target_loc}** (若已选，请在下方填表)")

with st.form("manual_form", clear_on_submit=True):
    name = st.text_input("您的姓名 *")
    issue = st.radio("问题类型", ["系统有货-实物无", "系统无货-实物有", "库位停用-实物有货"], horizontal=True)
    note = st.text_area("备注")
    
    if st.form_submit_button("✅ 确认提交并刷新", use_container_width=True):
        if target_loc == "未选择" or not name:
            st.error("请先在上方点击库位并填写姓名！")
        elif send_to_google_form(name, target_loc, issue, note):
            st.success("提交成功！")
            st.query_params.clear()
            st.rerun()

# 底部留白，方便下滑操作
st.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True)