import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests

# 1. 页面基本配置
st.set_page_config(page_title="MDC 互动盘点 4.0", layout="centered")

# 2. 手机端 UI 强制适配 (并排按钮 + 隐藏多余组件)
st.markdown("""
    <style>
    [data-testid="column"] { width: calc(50% - 0.5rem) !important; flex: 1 1 calc(50% - 0.5rem) !important; }
    #MainMenu, header, footer {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    /* 橙色横梁样式 */
    .slot::after {
        content: ""; position: absolute; bottom: -3px; left: 0;
        width: 100%; height: 4px; background: #fb8c00; border-radius: 2px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 核心函数：数据提交 ---
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

# =========================================================
# 💡 核心升级：状态记忆 (Session State)
# =========================================================
# 初始化大脑：确保仓库和货架在刷新后能找回
if 'selected_area' not in st.session_state: st.session_state.selected_area = "A"
if 'selected_rack' not in st.session_state: st.session_state.selected_rack = "0.0"

# --- 顶端配置区（固定存在） ---
st.markdown("<h3 style='text-align: center; margin-top: -10px;'>⚙️ 货架切换</h3>", unsafe_allow_html=True)

sel_c1, sel_c2 = st.columns(2)
with sel_c1:
    areas = sorted(df['仓库'].dropna().unique().tolist())
    # 绑定 session_state
    selected_area = st.selectbox("1. 库区", areas, index=areas.index(st.session_state.selected_area), key="area_select")
    st.session_state.selected_area = selected_area

with sel_c2:
    raw_racks = df[df['仓库'] == selected_area]['货架'].dropna().unique().tolist()
    sorted_racks = sorted(raw_racks, key=lambda x: int(float(x)))
    rack_options = [f"{int(float(x)):02d}" for x in sorted_racks]
    
    # 获取之前保存的货架索引
    current_rack_raw = st.session_state.selected_rack
    try:
        default_rack_idx = sorted_racks.index(current_rack_raw)
    except:
        default_rack_idx = 0
        
    selected_rack_display = st.selectbox("2. 货架", rack_options, index=default_rack_idx, key="rack_select")
    st.session_state.selected_rack = sorted_racks[rack_options.index(selected_rack_display)]

rack_code = f"{selected_area}{selected_rack_display}"
st.divider()

# --- 业务规则逻辑 ---
is_area_a = (selected_area == "A")
levels_raw = ['50.0','40.0','30.0','20.0','10.0','0.0'] if is_area_a else ['40.0','30.0','20.0','10.0','0.0']
bps, view_sections, slot_h = (3, 2, "45px") if is_area_a else (2, 3, "55px")
all_bins_raw = df[(df['仓库'] == selected_area) & (df['货架'] == st.session_state.selected_rack)]['位置.1'].dropna().unique().tolist()
all_bins = sorted(all_bins_raw, key=lambda x: int(float(x)), reverse=True)

if 'offset' not in st.session_state: st.session_state.offset = 0
total_bins_view = bps * view_sections

# --- 翻页按钮 ---
nav_cols = st.columns([1, 2, 2, 1])
with nav_cols[1]:
    if st.button("⬅️ 上页", use_container_width=True):
        st.session_state.offset = max(0, st.session_state.offset - total_bins_view)
with nav_cols[2]:
    if st.button("下页 ➡️", use_container_width=True):
        if st.session_state.offset + total_bins_view < len(all_bins):
            st.session_state.offset += total_bins_view

current_bins = all_bins[st.session_state.offset : st.session_state.offset + total_bins_view]

# --- 货架图渲染 (点击触发锚点 #feedback) ---
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
                # 点击后跳转到 #feedback 锚点
                html += f'<a href="?check_loc={full_id}#feedback" target="_self" class="slot {bg}">{lvl_str}</a>'
        html += f'<div class="bin-label">{bin_str}</div></div>'
        if i == len(bins) - 1: html += '<div class="pillar"></div>'
    return css + html + '</div>'

components.html(get_shelf_html(current_bins, levels_raw, bps, slot_h), height=380)

# --- 锚点标记与反馈区 ---
st.markdown('<div id="feedback"></div>', unsafe_allow_html=True) # 锚点
st.divider()

q_params = st.query_params
if "check_loc" in q_params:
    target_loc = q_params["check_loc"]
    st.markdown(f"<h3 style='text-align: center; color: #ff4b4b;'>🚨 异常反馈: {target_loc}</h3>", unsafe_allow_html=True)
    
    with st.form("bottom_form", clear_on_submit=True):
        name = st.text_input("您的姓名 *", key="staff_name")
        issue = st.radio("问题类型", ["系统有货-实物无", "系统无货-实物有", "库位停用-实物有货"], horizontal=True)
        note = st.text_area("备注")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.form_submit_button("✅ 确认提交", use_container_width=True):
                if not name: st.error("请填姓名")
                elif send_to_google_form(name, target_loc, issue, note):
                    st.success("同步成功！")
                    # 清除参数并自动滚动回顶端
                    st.query_params.clear()
                    st.rerun()
        with c2:
            if st.form_submit_button("❌ 取消重置", use_container_width=True):
                st.query_params.clear()
                st.rerun()
else:
    st.info("👆 请点击上方货架中的库位开始反馈差异")

### 💡 升级版体验改进：
1. **状态锁死**：即使员工切换到了 **C 库 C05** 货架，提交反馈后，系统也会根据 `session_state` 的记忆，自动重新加载 C 库 C05，不会再跳回 A 库。
2. **橙色横梁回归**：HTML 代码中重新加入了横梁逻辑，视觉定位更精准。
3. **锚点跳转**：在库位格子链接后添加了 `#feedback`，点击时手机浏览器会自动定位到下方的表单区域，省去员工手动向下滑动的动作。
4. **并排选择器**：仓库和货架选择器在顶端并排显示，切换非常快速。

您可以直接更新 GitHub 上的代码，这套“记忆+锚点”的逻辑已经是目前 Streamlit 移动端交互的最佳实践了！