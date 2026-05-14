import streamlit as st
import pandas as pd
import requests

# 1. 页面基本配置
st.set_page_config(page_title="MDC 互动盘点 9.2", layout="centered")

# 2. 全局样式定制
st.markdown("""
    <style>
    /* 强制列布局在手机端不折行 */
    [data-testid="column"] { width: calc(50% - 0.5rem) !important; flex: 1 1 calc(50% - 0.5rem) !important; }
    #MainMenu, header, footer {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    
    /* 货架 UI 样式 */
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
    
    /* 中间部分字体加大 */
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

# 1. 仓库与货架选择
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

# 2. 强制翻页按钮在一行 (使用 4 列布局，中间两列放按钮)
n1, n2, n3, n4 = st.columns([1, 2, 2, 1])
with n2:
    if st.button("⬅️ 上页", use_container_width=True):
        st.session_state.offset = max(0, st.session_state.offset - 6)
with n3:
    if st.button("下页 ➡️", use_container_width=True):
        st.session_state.offset += 6

# 3. 渲染彩色货架
is_a = (st.session_state.s_area == "A")
lvls = ['50.0','40.0','30.0','20.0','10.0','0.0'] if is_a else ['40.0','30.0','20.0','10.0','0.0']
sec_size = 3 if is_a else 2
all_bins = sorted(df[(df['仓库'] == st.session_state.s_area) & (df['货架'] == st.session_state.s_rack)]['位置.1'].dropna().unique().tolist(), key=lambda x: int(float(x)), reverse=True)
current_bins = all_bins[st.session_state.offset : st.session_state.offset + 6]

# 构建 HTML 字符串
shelf_html = '<div class="shelf-container">'
for i, b_num in enumerate(current_bins):
    # 插入蓝色立柱
    if i % sec_size == 0:
        shelf_html += '<div class="pillar"></div>'
    
    bin_str = f"{int(float(b_num)):02d}"
    shelf_html += '<div class="bin-col">'
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
    
    if i == len(current_bins) - 1:
        shelf_html += '<div class="pillar"></div>'

shelf_html += '</div>'
st.markdown(shelf_html, unsafe_allow_html=True)

# =========================================================
# 🏗️ 中间部分：大字体库位选择
# =========================================================
st.divider()
st.markdown('<p class="big-font">📍 第二步：请选择要反馈的库位</p>', unsafe_allow_html=True)

# 自动生成当前视图内可选的库位列表
available_locs = []
for b in current_bins:
    for l in lvls:
        available_locs.append(f"{rack_code}{int(float(b)):02d}{int(float(l)):02d}")

target_loc = st.selectbox("⬇️ 点击下方展开列表选择库位号", ["-- 还没选库位 --"] + available_locs, label_visibility="collapsed")

# =========================================================
# 🏗️ 下半部分：反馈提交
# =========================================================
if target_loc != "-- 还没选库位 --":
    st.info(f"✅ 已选中库位：**{target_loc}**，请填写下方信息后提交。")
    with st.form("feedback_form", clear_on_submit=True):
        u_name = st.text_input("您的姓名 *")
        u_issue = st.radio("问题类型", ["系统有货-实物无", "系统无货-实物有", "库位停用-实物有货"], horizontal=True)
        u_note = st.text_area("备注说明")
        
        if st.form_submit_button("✅ 确认提交反馈", use_container_width=True):
            if not u_name:
                st.error("请填姓名！")
            else:
                # 提交逻辑
                form_id = "1FAIpQLScdB2DC7CKJKly5vaaqTykfo5wrsdMSIgy3I01KvxAUY_emJQ"
                url = f"https://docs.google.com/forms/d/e/{form_id}/formResponse"
                payload = {"entry.1669427102": u_name, "entry.738175923": target_loc, "entry.1676630815": u_issue, "entry.914821861": u_note}
                try:
                    requests.post(url, data=payload, timeout=5)
                    st.success(f"同步成功！{target_loc} 记录已更新。")
                except:
                    st.error("提交失败，请重试。")
                st.rerun()

st.markdown("<br><br><br><br>", unsafe_allow_html=True)