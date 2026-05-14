import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests

# 1. 页面配置
st.set_page_config(page_title="MDC 互动盘点 8.0", layout="centered")

# 2. 基础 CSS (去间距、隐藏 header)
st.markdown("""
    <style>
    [data-testid="column"] { width: calc(50% - 0.5rem) !important; flex: 1 1 calc(50% - 0.5rem) !important; }
    #MainMenu, header, footer {visibility: hidden;}
    .block-container {padding-top: 1rem;}
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

@st.cache_data
def load_data():
    df = pd.read_csv('SGF.csv', dtype=str)
    if '状态' in df.columns:
        df['状态'] = df['状态'].fillna('').str.strip()
    stock_list = df[df['产品参考编码'].notna()]['位置/位置名称'].unique().tolist()
    return df, stock_list

df, has_stock_list = load_data()

# --- 状态记忆初始化 ---
if 'sel_area' not in st.session_state: st.session_state.sel_area = "A"
if 'sel_rack' not in st.session_state: st.session_state.sel_rack = "1"
if 'clicked_loc' not in st.session_state: st.session_state.clicked_loc = None

# =========================================================
# 🏗️ 顶部：货架与仓库选择
# =========================================================
st.markdown("<h3 style='text-align: center;'>🏗️ 货架布局展示</h3>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    areas = sorted(df['仓库'].dropna().unique().tolist())
    st.session_state.sel_area = st.selectbox("1. 库区", areas, index=areas.index(st.session_state.sel_area))
with c2:
    racks = sorted(df[df['仓库'] == st.session_state.sel_area]['货架'].dropna().unique().tolist(), key=lambda x: int(float(x)))
    rack_labels = [f"{int(float(r)):02d}" for r in racks]
    selected_label = st.selectbox("2. 货架", rack_labels)
    st.session_state.sel_rack = racks[rack_labels.index(selected_label)]

rack_code = f"{st.session_state.sel_area}{selected_label}"

# 业务规则
is_area_a = (st.session_state.sel_area == "A")
lvls = ['50.0','40.0','30.0','20.0','10.0','0.0'] if is_area_a else ['40.0','30.0','20.0','10.0','0.0']
bps, view_sections, h = (3, 2, "45px") if is_area_a else (2, 3, "55px")

all_bins = sorted(df[(df['仓库'] == st.session_state.sel_area) & (df['货架'] == st.session_state.sel_rack)]['位置.1'].dropna().unique().tolist(), key=lambda x: int(float(x)), reverse=True)
if 'offset' not in st.session_state: st.session_state.offset = 0
current_bins = all_bins[st.session_state.offset : st.session_state.offset + (bps * view_sections)]

# =========================================================
# 🎨 货架渲染 (使用透明按钮图层解决白屏)
# =========================================================
# 我们用 HTML 画漂亮的背景，用 st.columns 画透明点击层
st.markdown("""
    <style>
    .shelf-bg { display: flex; justify-content: center; position: relative; margin-bottom: 20px; }
    .pillar { width: 10px; background: #3498db; margin: 0 4px; border-radius: 5px; }
    .bin-col { display: flex; flex-direction: column; width: 62px; }
    .slot-ui { height: """+h+"""; border: 1px solid #eee; margin: 2px 1px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px; border-radius: 2px; position: relative; }
    .slot-ui::after { content: ""; position: absolute; bottom: -3px; left: 0; width: 100%; height: 4px; background: #fb8c00; border-radius: 2px; }
    .stocked { background: #1976D2; color: #fff; }
    .empty { background: #fff; color: #ccc; }
    .disabled { background: #f5f5f5; color: #ff5252; }
    .bin-label { text-align: center; font-size: 10px; padding: 8px 0; color: #777; }
    </style>
""", unsafe_allow_html=True)

# 渲染翻页按钮
n1, n2, n3, n4 = st.columns([1,2,2,1])
with n2: 
    if st.button("⬅️ 上页"): st.session_state.offset = max(0, st.session_state.offset - 6)
with n3:
    if st.button("下页 ➡️"): st.session_state.offset += 6

# 渲染货架
cols = st.columns(len(current_bins))
for i, b_num in enumerate(current_bins):
    bin_str = f"{int(float(b_num)):02d}"
    with cols[i]:
        for l in lvls:
            l_str = f"{int(float(l)):02d}"
            fid = f"{rack_code}{bin_str}{l_str}"
            
            # 获取状态
            row = df[df['位置/位置名称'] == fid]
            status = row['状态'].values[0] if not row.empty else "可用"
            
            # 视觉样式判断
            if status != "可用":
                st.markdown(f'<div class="slot-ui disabled">❌</div>', unsafe_allow_html=True)
            else:
                style = "stocked" if fid in has_stock_list else "empty"
                # 用原生按钮点击，解决白屏问题
                if st.button(l_str, key=fid, help=f"点击盘点 {fid}"):
                    st.session_state.clicked_loc = fid
        st.markdown(f'<div class="bin-label">{bin_str}</div>', unsafe_allow_html=True)

# =========================================================
# 🏗️ 底部：反馈记录
# =========================================================
st.divider()
if st.session_state.clicked_loc:
    st.error(f"📍 已选中库位：{st.session_state.clicked_loc}")
    with st.form("audit_form", clear_on_submit=True):
        u_name = st.text_input("姓名 *")
        u_issue = st.radio("情况", ["系统有货-实物无", "系统无货-实物有", "库位停用-实物有货"], horizontal=True)
        u_note = st.text_area("备注")
        if st.form_submit_button("✅ 确认提交", use_container_width=True):
            if u_name and send_to_google_form(u_name, st.session_state.clicked_loc, u_issue, u_note):
                st.success("提交成功！")
                st.session_state.clicked_loc = None
                st.rerun()
else:
    st.info("👆 请点击上方货架中的数字开始盘点")