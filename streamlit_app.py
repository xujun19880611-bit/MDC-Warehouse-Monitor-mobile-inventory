import streamlit as st
import pandas as pd
import requests
import time

# 1. 页面配置
st.set_page_config(page_title="MDC 互动盘点 9.5", layout="centered")

# 2. 全局样式定制 - 彻底修复下拉框显示不全问题
st.markdown("""
    <style>
    [data-testid="column"] { width: calc(50% - 0.5rem) !important; flex: 1 1 calc(50% - 0.5rem) !important; }
    #MainMenu, header, footer {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    
    /* 货架 UI */
    .shelf-container { display: flex; justify-content: center; align-items: flex-start; padding: 10px 0; background: white; }
    .pillar { width: 12px; background: #3498db; margin: 0 4px; border-radius: 6px; align-self: stretch; min-height: 240px; }
    .bin-col { display: flex; flex-direction: column; width: 62px; }
    .slot { 
        height: 40px; border: 1px solid #eee; margin: 2px 1px; 
        display: flex; align-items: center; justify-content: center; 
        font-weight: bold; font-size: 13px; border-radius: 2px; position: relative;
    }
    .slot::after { content: ""; position: absolute; bottom: -3px; left: 0; width: 100%; height: 4px; background: #fb8c00; border-radius: 2px; }
    .stocked { background: #1976D2; color: #fff; }
    .empty { background: #fff; color: #ccc; }
    .disabled { background: #f5f5f5; color: #ff5252; }
    .bin-label { text-align: center; font-size: 11px; padding: 5px 0; color: #777; font-weight: bold; }
    
    /* 下拉框高度修复：不仅加大字体，还必须撑开容器高度和行高 */
    div[data-baseweb="select"] {
        font-size: 26px !important; /* 稍微再大一点 */
        font-weight: bold !important;
    }
    /* 核心修复：强制下拉框本体高度 */
    div[data-baseweb="select"] > div:first-child {
        height: 70px !important; 
        display: flex !important;
        align-items: center !important;
    }
    /* 下拉列表项 */
    div[role="listbox"] div {
        font-size: 22px !important;
        padding: 12px !important;
    }
    
    .big-font { font-size: 22px !important; font-weight: bold; color: #ff4b4b; text-align: center; margin: 15px 0; }
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
if 's_area' not in st.session_state: st.session_state.s_area = "A"
if 's_rack' not in st.session_state: st.session_state.s_rack = "0.0"
if 'offset' not in st.session_state: st.session_state.offset = 0

# =========================================================
# 🏗️ 上半部分：货架浏览
# =========================================================
st.markdown("<h3 style='text-align: center; margin-bottom: 0;'>🏗️ 实时货架视图</h3>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    areas = sorted(df['仓库'].dropna().unique().tolist())
    st.session_state.s_area = st.selectbox("1. 库区", areas, index=areas.index(st.session_state.s_area))
with c2:
    racks = sorted(df[df['仓库'] == st.session_state.s_area]['货架'].dropna().unique().tolist(), key=lambda x: int(float(x)))
    r_labels = [f"{int(float(r)):02d}" for r in racks]
    try: d_idx = racks.index(st.session_state.s_rack)
    except: d_idx = 0
    sel_label = st.selectbox("2. 货架", r_labels, index=d_idx)
    st.session_state.s_rack = racks[r_labels.index(sel_label)]

rack_code = f"{st.session_state.s_area}{sel_label}"

n1, n2, n3, n4 = st.columns([1, 2, 2, 1])
with n2:
    if st.button("⬅️ 上页", use_container_width=True): st.session_state.offset = max(0, st.session_state.offset - 6)
with n3:
    if st.button("下页 ➡️", use_container_width=True): st.session_state.offset += 6

is_a = (st.session_state.s_area == "A")
lvls = ['50.0','40.0','30.0','20.0','10.0','0.0'] if is_a else ['40.0','30.0','20.0','10.0','0.0']
sec_size = 3 if is_a else 2
all_bins = sorted(df[(df['仓库'] == st.session_state.s_area) & (df['货架'] == st.session_state.s_rack)]['位置.1'].dropna().unique().tolist(), key=lambda x: int(float(x)), reverse=True)
current_bins = all_bins[st.session_state.offset : st.session_state.offset + 6]

shelf_html = '<div class="shelf-container">'
for i, b_num in enumerate(current_bins):
    if i % sec_size == 0: shelf_html += '<div class="pillar"></div>'
    bin_str = f"{int(float(b_num)):02d}"
    shelf_html += '<div class="bin-col">'
    for l in lvls:
        l_str = f"{int(float(l)):02d}"
        fid = f"{rack_code}{bin_str}{l_str}"
        row = df[df['位置/位置名称'] == fid]
        status = row['状态'].values[0] if not row.empty else "可用"
        if status != "可用": shelf_html += '<div class="slot disabled">❌</div>'
        else:
            bg = "stocked" if fid in has_stock_list else "empty"
            shelf_html += f'<div class="slot {bg}">{l_str}</div>'
    shelf_html += f'<div class="bin-label">{bin_str}</div></div>'
    if i == len(current_bins) - 1: shelf_html += '<div class="pillar"></div>'
shelf_html += '</div>'
st.markdown(shelf_html, unsafe_allow_html=True)

# =========================================================
# 🏗️ 中间部分：选择库位
# =========================================================
st.divider()
st.markdown('<p class="big-font">📍 第二步：选择待反馈库位</p>', unsafe_allow_html=True)

available_locs = []
for b in current_bins:
    for l in lvls:
        available_locs.append(f"{rack_code}{int(float(b)):02d}{int(float(l)):02d}")

target_loc = st.selectbox("⬇️ 库位选择列表", ["-- 请选择 --"] + available_locs, label_visibility="collapsed")

# =========================================================
# 🏗️ 下半部分：反馈提交（修复提交链接与Radio布局）
# =========================================================
if target_loc != "-- 请选择 --":
    st.info(f"✅ 当前选中：**{target_loc}**")
    with st.form("feedback_form", clear_on_submit=True):
        u_name = st.text_input("您的姓名 *")
        # 变更为垂直排列
        u_issue = st.radio("问题类型", ["系统有货-实物无", "系统无货-实物有", "库位停用-实物有货"], horizontal=False)
        u_note = st.text_area("备注说明")
        
        if st.form_submit_button("✅ 确认提交", use_container_width=True):
            if not u_name:
                st.error("请输入姓名！")
            else:
                # ！！！核心修复：正确的 Google Form 提交地址 ！！！
                form_id = "1FAIpQLScdB2DC7CKJKly5vaaqTykfo5wrsdMSIgy3I01KvxAUY_emJQ"
                url = f"https://docs.google.com/forms/d/e/{form_id}/formResponse"
                
                payload = {
                    "entry.1669427102": u_name, 
                    "entry.738175923": target_loc, 
                    "entry.1676630815": u_issue, 
                    "entry.914821861": u_note
                }
                
                try:
                    # 使用 timeout 确保不会死循环，并获取准确状态
                    response = requests.post(url, data=payload, timeout=10)
                    
                    # 只要返回 200 或 0（某些网络下 Google Form 的特殊返回）即为成功
                    if response.status_code == 200 or response.status_code == 0:
                        st.toast(f"🎉 提交成功: {target_loc}", icon='✅')
                        st.success("数据同步完成！页面即将刷新...")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error(f"提交失败：服务器返回错误 {response.status_code}")
                except Exception as e:
                    st.error("网络异常，无法连接到提交服务器，请检查网络。")

st.markdown("<br><br><br><br>", unsafe_allow_html=True)