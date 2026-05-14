import streamlit as st
import pandas as pd
import requests

# 1. 页面配置
st.set_page_config(page_title="MDC 互动盘点 6.0", layout="centered")

# 2. CSS：保留横梁视觉，隐藏多余组件
st.markdown("""
    <style>
    [data-testid="column"] { width: calc(50% - 0.5rem) !important; flex: 1 1 calc(50% - 0.5rem) !important; }
    #MainMenu, header, footer {visibility: hidden;}
    /* 优化原生按钮样式，使其看起来更像库位选择 */
    div.stButton > button {
        border-radius: 5px;
        border: 1px solid #1976D2;
        color: #1976D2;
        font-weight: bold;
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
if 'selected_area' not in st.session_state: st.session_state.selected_area = "A"
if 'selected_rack' not in st.session_state: st.session_state.selected_rack = "0.0"
if 'target_loc' not in st.session_state: st.session_state.target_loc = None

# =========================================================
# 🏗️ 第一部分：货架选择
# =========================================================
st.markdown("<h3 style='text-align: center;'>🏗️ 货架布局展示</h3>", unsafe_allow_html=True)

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

# 业务逻辑
is_area_a = (selected_area == "A")
levels_raw = ['50.0','40.0','30.0','20.0','10.0','0.0'] if is_area_a else ['40.0','30.0','20.0','10.0','0.0']
raw_bins = df[(df['仓库'] == selected_area) & (df['货架'] == st.session_state.selected_rack)]['位置.1'].dropna().unique().tolist()
all_bins = sorted(raw_bins, key=lambda x: int(float(x)), reverse=True)

# ---------------------------------------------------------
# 💡 核心改变：用原生按钮选择库位 (解决嵌套问题)
# ---------------------------------------------------------
st.write("📍 **请点击下方按钮选择要反馈的库位：**")

# 为了手机端好看，我们把按钮按列排布
current_bins_to_show = all_bins[:6] # 演示前6个，你可以继续用offset逻辑
cols = st.columns(len(current_bins_to_show))

for idx, b_num in enumerate(current_bins_to_show):
    bin_str = f"{int(float(b_num)):02d}"
    with cols[idx]:
        st.caption(f"列{bin_str}")
        for lvl in levels_raw:
            lvl_str = f"{int(float(lvl)):02d}"
            loc_id = f"{rack_code}{bin_str}{lvl_str}"
            
            # 用原生按钮，点击后直接修改 session_state
            if st.button(lvl_str, key=loc_id, use_container_width=True):
                st.session_state.target_loc = loc_id

st.divider()

# =========================================================
# 🏗️ 第二部分：反馈记录区 (永远在下方)
# =========================================================
if st.session_state.target_loc:
    st.markdown(f"<h3 style='text-align: center; color: #ff4b4b;'>🚨 异常反馈: {st.session_state.target_loc}</h3>", unsafe_allow_html=True)
    
    with st.form("inventory_form", clear_on_submit=True):
        name = st.text_input("盘点人姓名 *")
        issue = st.radio("问题类型", ["系统有货-实物无", "系统无货-实物有", "库位停用-实物有货"], horizontal=True)
        note = st.text_area("备注说明")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.form_submit_button("✅ 确认提交", use_container_width=True):
                if not name: st.error("请填姓名")
                elif send_to_google_form(name, st.session_state.target_loc, issue, note):
                    st.success("提交成功！")
                    st.session_state.target_loc = None # 提交后清除选择
                    st.rerun()
        with c2:
            if st.form_submit_button("❌ 取消重置", use_container_width=True):
                st.session_state.target_loc = None
                st.rerun()
else:
    st.info("💡 请点击上方蓝色数字选择故障库位")