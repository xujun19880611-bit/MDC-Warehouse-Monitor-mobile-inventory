import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime
import requests

# 页面配置
st.set_page_config(page_title="MDC 互动盘点系统", layout="wide")

# --- 1. Google Form 提交函数 ---
def send_to_google_form(name, loc, p_type, note):
    # 1. 替换为你真实的表单 ID (从你的 URL 中提取)
    form_id = "1FAIpQLScdB2DC7CKJKly5vaaqTykfo5wrsdMSIgy3I01KvxAUY_emJQ" 
    url = f"https://docs.google.com/forms/d/e/{form_id}/formResponse"
    
    # 2. 这里的 entry.xxxx 需要你按照下面的步骤填入真实的数字 ID
    payload = {
        "entry.1669427102": name,   # 对应“员工姓名”
        "entry.738175923": loc,    # 对应“库位编号”
        "entry.1676630815": p_type, # 对应“问题类型”
        "entry.914821861": note    # 对应“备注”
    }
    
    try:
        res = requests.post(url, data=payload)
        return res.status_code == 200
    except:
        return False

# --- 2. 数据加载 (SGF.csv 放在 GitHub 根目录) ---
@st.cache_data
def load_and_process_data():
    df = pd.read_csv('SGF.csv', dtype=str)
    if '状态' in df.columns:
        df['状态'] = df['状态'].fillna('').str.strip()
    structure = df[df['产品参考编码'].isna()].copy()
    stock_locations = df[df['产品参考编码'].notna()]['位置/位置名称'].unique().tolist()
    return structure, stock_locations

try:
    df_struct, has_stock_list = load_and_process_data()
except Exception as e:
    st.error("请确保 SGF.csv 已上传至 GitHub 仓库根目录")
    st.stop()

# --- 3. 侧边栏与反馈表单 ---
with st.sidebar:
    st.header("⚙️ 盘点后台")
    
    areas = sorted(df_struct['仓库'].dropna().unique().tolist())
    selected_area = st.selectbox("1. 选择库区", areas)
    
    raw_racks = df_struct[df_struct['仓库'] == selected_area]['货架'].dropna().unique().tolist()
    sorted_racks = sorted(raw_racks, key=lambda x: int(float(x)))
    selected_rack_raw = st.selectbox("2. 选择货架", sorted_racks, 
                                    format_func=lambda x: f"{selected_area}{int(float(x)):02d}")
    
    rack_code = f"{selected_area}{int(float(selected_rack_raw)):02d}"

    # 差异反馈处理
    query_params = st.query_params
    if "check_loc" in query_params:
        target_loc = query_params["check_loc"]
        st.divider()
        st.warning(f"🚨 反馈库位：{target_loc}")
        
        with st.form("inventory_diff_form"):
            staff_name = st.text_input("员工姓名 * (必填)")
            p_type = st.radio("问题类型", [
                "系统有货，实际无货", 
                "系统无货，实际有货", 
                "系统不可用，实际有货"
            ])
            remark = st.text_input("备注说明")
            
            if st.form_submit_button("确认提交至云端"):
                if not staff_name:
                    st.error("请输入姓名！")
                else:
                    with st.spinner('正在同步至 Google Sheets...'):
                        success = send_to_google_form(staff_name, target_loc, p_type, remark)
                        if success:
                            st.success("✅ 同步成功！")
                            st.query_params.clear()
                            st.rerun()
                        else:
                            st.error("❌ 同步失败，请检查网络或表单ID")

# --- 4. 货架 UI 逻辑 (保持倒序和补零逻辑) ---
is_area_a = (selected_area == "A")
levels_raw = ['50.0','40.0','30.0','20.0','10.0','0.0'] if is_area_a else ['40.0','30.0','20.0','10.0','0.0']
bps, view_sections, slot_h = (3, 2, "60px") if is_area_a else (2, 3, "70px")

total_bins_view = bps * view_sections
raw_bins = df_struct[(df_struct['仓库'] == selected_area) & (df_struct['货架'] == selected_rack_raw)]['位置.1'].dropna().unique().tolist()
all_bins = sorted(raw_bins, key=lambda x: int(float(x)), reverse=True)

if 'offset' not in st.session_state: st.session_state.offset = 0

st.markdown(f"<h2 style='text-align: center; color: #1f77b4;'>🏗️ {rack_code} 互动盘点终端</h2>", unsafe_allow_html=True)

# 翻页按钮
c1, c2, c3, c4 = st.columns([3, 1, 1, 3])
with c2: 
    if st.button("⬅️ 上一页", use_container_width=True): st.session_state.offset = max(0, st.session_state.offset - total_bins_view)
with c3:
    if st.button("下一页 ➡️", use_container_width=True):
        if st.session_state.offset + total_bins_view < len(all_bins): st.session_state.offset += total_bins_view

current_bins = all_bins[st.session_state.offset : st.session_state.offset + total_bins_view]

# --- 5. HTML 渲染渲染 (点击格子触发 URL 参数) ---
def render_shelf_html(bins, lvls, section_size, h):
    css = f"""
    <style>
        .shelf-wrapper {{ display: flex; justify-content: center; background: #fff; padding: 10px; }}
        .pillar {{ width: 22px; background: #3498db; border-radius: 11px; margin: 0 10px; box-shadow: 2px 2px 5px #ccc; }}
        .bin-col {{ display: flex; flex-direction: column; width: 120px; }}
        .slot {{
            height: {h}; border: 2px solid #f0f0f0; margin: 2px 0;
            display: flex; align-items: center; justify-content: center;
            font-weight: 800; font-size: 20px; text-decoration: none; cursor: pointer;
        }}
        .empty {{ background: #ffffff; color: #bbb; }} 
        .stocked {{ background: #1976D2; color: #ffffff; }} 
        .disabled {{ background: #f0f0f0; color: #ff1744; border: 2px dashed #ccc; pointer-events: none; }} 
        .slot::after {{ content: ""; position: absolute; bottom: -6px; left: 0; width: 100%; height: 10px; background: #fb8c00; }}
        .bin-label {{ text-align: center; font-size: 16px; font-weight: bold; padding: 15px 0; color: #333; }}
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
        html += f'<div class="bin-label">{rack_code}{bin_str}</div></div>'
        if i == len(bins) - 1: html += '<div class="pillar"></div>'
    html += '</div>'
    return css + html

components.html(render_shelf_html(current_bins, levels_raw, bps, slot_h), height=650)