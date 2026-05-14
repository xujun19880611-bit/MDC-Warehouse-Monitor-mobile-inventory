import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import json

st.set_page_config(page_title="MDC 互动盘点 7.0", layout="centered")

# 1. 基础 CSS
st.markdown("""
    <style>
    [data-testid="column"] { width: calc(50% - 0.5rem) !important; flex: 1 1 calc(50% - 0.5rem) !important; }
    #MainMenu, header, footer {visibility: hidden;}
    .stSelectbox { margin-bottom: -10px; }
    </style>
""", unsafe_allow_html=True)

# --- 数据处理 ---
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
if 'target_loc' not in st.session_state: st.session_state.target_loc = None

# =========================================================
# 🏗️ 顶部：货架选择
# =========================================================
st.markdown("<h3 style='text-align: center; margin-top: -20px;'>🏗️ 货架布局展示</h3>", unsafe_allow_html=True)

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

# 业务规则逻辑
is_area_a = (selected_area == "A")
levels_raw = ['50.0','40.0','30.0','20.0','10.0','0.0'] if is_area_a else ['40.0','30.0','20.0','10.0','0.0']
bps, view_sections, slot_h = (3, 2, "45px") if is_area_a else (2, 3, "55px")
all_bins_raw = df[(df['仓库'] == selected_area) & (df['货架'] == st.session_state.selected_rack)]['位置.1'].dropna().unique().tolist()
all_bins = sorted(all_bins_raw, key=lambda x: int(float(x)), reverse=True)

if 'offset' not in st.session_state: st.session_state.offset = 0
current_bins = all_bins[st.session_state.offset : st.session_state.offset + (bps * view_sections)]

# =========================================================
# 🎨 核心：漂亮的 HTML 货架 + JS 通信
# =========================================================
def render_custom_shelf(bins, lvls, section_size, h):
    # 构建库位数据，传给 JS
    shelf_data = []
    for b_num in bins:
        bin_str = f"{int(float(b_num)):02d}"
        levels_data = []
        for lvl in lvls:
            lvl_str = f"{int(float(lvl)):02d}"
            full_id = f"{rack_code}{bin_str}{lvl_str}"
            row = df[df['位置/位置名称'] == full_id]
            status = row['状态'].values[0] if not row.empty else "可用"
            is_stocked = full_id in has_stock_list
            levels_data.append({"id": full_id, "lvl": lvl_str, "status": status, "is_stocked": is_stocked})
        shelf_data.append({"bin": bin_str, "levels": levels_data})

    # HTML 模板：点击库位通过 Streamlit.setComponentValue 与父页面通信
    html_code = f"""
    <div id="shelf-container"></div>
    <script>
    const data = {json.dumps(shelf_data)};
    const container = document.getElementById('shelf-container');
    
    let html = `<style>
        .shelf-wrapper {{ display: flex; justify-content: center; background: white; font-family: sans-serif; }}
        .pillar {{ width: 10px; background: #3498db; margin: 0 4px; border-radius: 5px; }}
        .bin-col {{ display: flex; flex-direction: column; width: 62px; }}
        .slot {{ 
            height: {h}; border: 1px solid #eee; margin: 2px 1px; 
            display: flex; align-items: center; justify-content: center; 
            font-weight: bold; font-size: 13px; border-radius: 2px; position: relative; cursor: pointer;
        }}
        .slot::after {{ content: ""; position: absolute; bottom: -3px; left: 0; width: 100%; height: 4px; background: #fb8c00; border-radius: 2px; }}
        .empty {{ background: #fff; color: #ccc; }}
        .stocked {{ background: #1976D2; color: #fff; }}
        .disabled {{ background: #f5f5f5; color: #ff5252; cursor: not-allowed; }}
        .bin-label {{ text-align: center; font-size: 10px; padding: 8px 0; color: #777; font-weight: bold; }}
    </style><div class="shelf-wrapper">`;

    data.forEach((bin, index) => {{
        if (index % {section_size} === 0) html += '<div class="pillar"></div>';
        html += '<div class="bin-col">';
        bin.levels.forEach(lvl => {{
            let cls = lvl.status !== "可用" ? "disabled" : (lvl.is_stocked ? "stocked" : "empty");
            let content = lvl.status !== "可用" ? "❌" : lvl.lvl;
            html += `<div class="slot ${{cls}}" onclick="selectLoc('${{lvl.id}}')">${{content}}</div>`;
        }});
        html += `<div class="bin-label">${{bin.bin}}</div></div>`;
    }});
    html += '<div class="pillar"></div></div>';
    container.innerHTML = html;

    function selectLoc(id) {{
        // 关键：不刷新页面，直接发送数据给 Streamlit
        window.parent.postMessage({{type: 'streamlit:setComponentValue', value: id}}, '*');
        // 平滑滚动到下方反馈区
        window.parent.scrollTo({{ top: 800, behavior: 'smooth' }});
    }}
    </script>
    """
    return components.html(html_code, height=380)

# 监听库位选择
selected_id = render_custom_shelf(current_bins, levels_raw, bps, slot_h)
if selected_id:
    st.session_state.target_loc = selected_id

# =========================================================
# 🏗️ 底部：反馈记录区
# =========================================================
st.divider()
target = st.session_state.target_loc if st.session_state.target_loc else "尚未选择"

st.markdown(f"<h3 style='text-align: center; color: #ff4b4b;'>🚨 差异反馈记录</h3>", unsafe_allow_html=True)
st.info(f"📍 当前库位：**{target}**")

with st.form("final_form", clear_on_submit=True):
    name = st.text_input("姓名 *")
    issue = st.radio("异常类型", ["系统有货-实物无", "系统无货-实物有", "库位停用-实物有货"], horizontal=True)
    note = st.text_area("备注")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.form_submit_button("✅ 确认提交", use_container_width=True):
            if target == "尚未选择" or not name:
                st.error("请选择库位并填姓名")
            else:
                # 提交逻辑 (此处省略 send_to_google_form 调用，同前)
                st.success("同步成功！")
                st.session_state.target_loc = None
                st.rerun()
    with c2:
        if st.form_submit_button("❌ 重置顶部", use_container_width=True):
            st.session_state.target_loc = None
            st.rerun()