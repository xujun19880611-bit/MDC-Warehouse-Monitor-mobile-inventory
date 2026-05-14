import streamlit as st
import pandas as pd
import requests

# 1. 页面配置
st.set_page_config(page_title="MDC 稳定版 9.1", layout="centered")

# 2. 样式：保留货架美感
st.markdown("""
    <style>
    [data-testid="column"] { width: calc(50% - 0.5rem) !important; flex: 1 1 calc(50% - 0.5rem) !important; }
    #MainMenu, header, footer {visibility: hidden;}
    .slot { 
        height: 40px; border: 1px solid #eee; margin: 2px 1px; 
        display: flex; align-items: center; justify-content: center; 
        font-weight: bold; font-size: 12px; border-radius: 2px; position: relative;
    }
    .slot::after { content: ""; position: absolute; bottom: -3px; left: 0; width: 100%; height: 4px; background: #fb8c00; border-radius: 2px; }
    .stocked { background: #1976D2; color: #fff; }
    .empty { background: #fff; color: #ccc; }
    .disabled { background: #f5f5f5; color: #ff5252; }
    .bin-label { text-align: center; font-size: 10px; color: #777; font-weight: bold; }
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

# --- 状态存储 ---
if 's_area' not in st.session_state: st.session_state.s_area = "A"
if 's_rack' not in st.session_state: st.session_state.s_rack = "0.0"

# =========================================================
# 🏗️ 上部分：视觉浏览（仅供观看，不可点击）
# =========================================================
st.markdown("<h3 style='text-align: center;'>🏗️ 实时货架视图</h3>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    areas = sorted(df['仓库'].dropna().unique().tolist())
    st.session_state.s_area = st.selectbox("1. 库区", areas, index=areas.index(st.session_state.s_area))
with c2:
    racks = sorted(df[df['仓库'] == st.session_state.s_area]['货架'].dropna().unique().tolist(), key=lambda x: int(float(x)))
    r_labels = [f"{int(float(r)):02d}" for r in racks]
    sel_label = st.selectbox("2. 货架", r_labels)
    st.session_state.s_rack = racks[r_labels.index(sel_label)]

rack_code = f"{st.session_state.s_area}{sel_label}"

# 渲染翻页
if 'offset' not in st.session_state: st.session_state.offset = 0
all_bins = sorted(df[(df['仓库'] == st.session_state.s_area) & (df['货架'] == st.session_state.s_rack)]['位置.1'].dropna().unique().tolist(), key=lambda x: int(float(x)), reverse=True)
current_bins = all_bins[st.session_state.offset : st.session_state.offset + 6]

n1, n2, n3, n4 = st.columns([1,2,2,1])
with n2: 
    if st.button("⬅️ 上页"): st.session_state.offset = max(0, st.session_state.offset - 6)
with n3:
    if st.button("下页 ➡️"): st.session_state.offset += 6

# 动态生成视觉货架（纯 HTML，无 <a> 标签）
is_a = (st.session_state.s_area == "A")
lvls = ['50.0','40.0','30.0','20.0','10.0','0.0'] if is_a else ['40.0','30.0','20.0','10.0','0.0']

shelf_html = '<div style="display: flex; justify-content: center; background: white; padding: 10px;">'
for b_num in current_bins:
    bin_str = f"{int(float(b_num)):02d}"
    shelf_html += '<div class="bin-col" style="display: flex; flex-direction: column; width: 60px; margin: 0 2px;">'
    for l in lvls:
        l_str = f"{int(float(l)):02d}"
        fid = f"{rack_code}{bin_str}{l_str}"
        row = df[df['位置/位置名称'] == fid]
        status = row['状态'].values[0] if not row.empty else "可用"
        if status != "可用":
            shelf_html += '<div class="slot disabled">❌</div>'
        else:
            bg = "stocked" if fid in has_stock_list else "empty"
            shelf_html += f'<div class="slot {bg}">{l_str}</div>'
    shelf_html += f'<div class="bin-label">{bin_str}</div></div>'
shelf_html += '</div>'
st.markdown(shelf_html, unsafe_allow_html=True)

# =========================================================
# 🏗️ 下部分：手动选择与反馈（这是唯一产生逻辑的地方）
# =========================================================
st.markdown("<br><br>---<br>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #ff4b4b;'>🚨 异常反馈录入</h3>", unsafe_allow_html=True)

# 1. 员工手动选刚才看到的库位
# 获取当前货架所有库位列表供选择
available_locs = []
for b in current_bins:
    for l in lvls:
        available_locs.append(f"{rack_code}{int(float(b)):02d}{int(float(l)):02d}")

target_loc = st.selectbox("📍 第一步：请选择刚才看中的库位号", ["-- 请选择 --"] + available_locs)

# 2. 填写表单
with st.form("manual_entry", clear_on_submit=True):
    u_name = st.text_input("您的姓名 *")
    u_issue = st.radio("问题类型", ["系统有货-实物无", "系统无货-实物有", "库位停用-实物有货"], horizontal=True)
    u_note = st.text_area("备注说明")
    
    if st.form_submit_button("✅ 确认提交反馈", use_container_width=True):
        if target_loc == "-- 请选择 --" or not u_name:
            st.error("请选择库位并填写姓名")
        elif send_to_google_form(u_name, target_loc, u_issue, u_note):
            st.success(f"库位 {target_loc} 反馈已同步！")
            st.rerun()

st.markdown("<br><br><br><br>", unsafe_allow_html=True)