import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. 页面配置 ---
st.set_page_config(page_title="MDC Mobile Pro", layout="wide")

# --- 2. Google Sheets 连接与数据处理 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def save_to_gsheets(loc, status, staff):
    """将盘点结果同步到 Google Sheets"""
    # 读取当前表格数据
    try:
        existing_data = conn.read(ttl=0)
    except:
        existing_data = pd.DataFrame(columns=["loc", "real_status", "staff", "update_time"])
    
    # 准备新数据
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_entry = pd.DataFrame([{
        "loc": loc,
        "real_status": status,
        "staff": staff,
        "update_time": now
    }])
    
    # 合并并去重（同一库位以最后一次盘点为准）
    if not existing_data.empty:
        updated_data = pd.concat([existing_data, new_entry], ignore_index=True)
        updated_data = updated_data.drop_duplicates(subset=['loc'], keep='last')
    else:
        updated_data = new_entry
        
    # 更新到云端
    conn.update(data=updated_data)
    st.cache_data.clear() # 清除缓存以刷新视图

def get_audited_dict():
    """获取已盘点库位的状态字典"""
    try:
        df = conn.read(ttl=5) # 5秒缓存平衡性能
        if df.empty: return {}
        return dict(zip(df['loc'], df['real_status']))
    except:
        return {}

# --- 3. 语言配置 ---
LANG_DICT = {
    "CN": {
        "title": "MDC 仓库联动盘点",
        "staff_name": "盘点人员",
        "wh_sel": "1. 选择仓库",
        "aisle_sel": "2. 选择货道",
        "bin_sel": "3. 选择具体库位",
        "audit_btn": "提交实盘记录",
        "status_empty": "空库位 (Vazio)",
        "status_used": "有货 (Ocupado)",
        "status_error": "不可用 (Bloqueado)",
        "submit_ok": "同步成功！",
        "total_usage": "总利用率",
        "history": "🕒 实时云端记录 (Google Sheets)"
    },
    "PT": {
        "title": "Inventário MDC Pro",
        "staff_name": "Funcionário",
        "wh_sel": "1. Selecionar Armazém",
        "aisle_sel": "2. Selecionar Corredor",
        "bin_sel": "3. Selecionar Local",
        "audit_btn": "Confirmar",
        "status_empty": "Vazio",
        "status_used": "Ocupado",
        "status_error": "Bloqueado",
        "submit_ok": "Sincronizado!",
        "total_usage": "Ocupação Total",
        "history": "🕒 Registro em Nuvem"
    }
}

# --- 4. 样式配置 ---
st.markdown("""
    <style>
    .bin-box { width: 34px; height: 30px; display: flex; align-items: center; justify-content: center; border-radius: 2px; font-size: 10px; font-weight: bold; border: 1px solid #f0f0f0; background-color: white; }
    .status-used { background-color: #3498db !important; color: white; border: none; }
    .status-empty { background-color: #2ecc71 !important; color: white; border: none; }
    .status-disabled { background-color: #95a5a6 !important; color: white; border: none; }
    .status-selected { border: 3px solid #FF4B4B !important; transform: scale(1.15); z-index: 100; box-shadow: 0 0 12px rgba(255, 75, 75, 0.9); }
    .status-audited { position: relative; }
    .status-audited::after { content: '✅'; position: absolute; top: -6px; right: -6px; font-size: 10px; }
    .total-card { background: linear-gradient(135deg, #1e3c72, #2a5298); padding: 15px; border-radius: 10px; color: white; text-align: center; margin-bottom: 20px; }
    .shelf-container { display: flex; flex-wrap: nowrap; overflow-x: auto; padding: 15px; background: #fff; border: 1px solid #eee; }
    .orange-beam { width: 100%; height: 3px; background-color: #ff9800; margin: 1px 0; }
    .pillar { width: 0; height: 180px; border-left: 3px dotted #3498db; margin: 0 10px; opacity: 0.6; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. SGF 数据加载 ---
@st.cache_data(ttl=60)
def load_sgf_data():
    if not os.path.exists("SGF.csv"): return None, None
    try:
        raw_df = pd.read_csv("SGF.csv", low_memory=False)
        df = raw_df.iloc[:, [0, 6, 9, 11, 12, 13, 14]].copy()
        df.columns = ['SKU', 'Loc', 'Qty', 'L', 'W', 'H', 'Status']
        df['Loc'] = df['Loc'].astype(str).str.strip()
        df['Status'] = df['Status'].astype(str).str.strip()
        df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0)
        for c in ['L','W','H']: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        df['Vol'] = (df['L'] * df['W'] * df['H']) / 1000000
        
        master = df[(~df['Loc'].str.contains('-', na=False)) & (df['Loc'].str.startswith(('A','B','C','D','E'))) & (df['L']>0)].drop_duplicates('Loc')
        l_map, wh_stats = {}, {wh: {'t_v':0.0, 'u_v':0.0, 'total_bins':0, 'used_bins':0} for wh in 'ABCDE'}
        for _, r in master.iterrows():
            wh = r['Loc'][0].upper()
            l_map[r['Loc']] = {'Items':[], 'Status':r['Status'], 'Vol':r['Vol'], 'WH':wh, 'Aisle':r['Loc'][0:3], 'Col':r['Loc'][3:5], 'Lvl':r['Loc'][5:7]}
            if r['Status'] == "可用": 
                wh_stats[wh]['t_v'] += r['Vol']
                wh_stats[wh]['total_bins'] += 1
        
        inv = df[df['Qty'] > 0]
        for _, r in inv.iterrows():
            if r['Loc'] in l_map: l_map[r['Loc']]['Items'].append(f"{r['SKU']}:{int(r['Qty'])}")
        
        for k, v in l_map.items():
            if len(v['Items']) > 0 and v['Status'] == "可用": 
                wh_stats[v['WH']]['u_v'] += v['Vol']; wh_stats[v['WH']]['used_bins'] += 1
        return l_map, wh_stats
    except: return None, None

l_map, wh_stats = load_sgf_data()
audited_data = get_audited_dict()

# --- 6. 侧边栏联动 ---
if l_map:
    lang_choice = st.sidebar.radio("Língua / 语言", ["中文", "Português"])
    L = LANG_DICT["CN"] if lang_choice == "中文" else LANG_DICT["PT"]
    
    st.sidebar.header("👤 " + L["staff_name"])
    staff = st.sidebar.text_input("Name", value="Staff_01")
    
    st.sidebar.divider()
    st.sidebar.subheader("🎯 " + L["audit_btn"])
    
    # 三级联动
    selected_wh = st.sidebar.selectbox(L["wh_sel"], sorted(list(wh_stats.keys())))
    aisle_options = sorted(list(set(v['Aisle'] for v in l_map.values() if v['WH'] == selected_wh)))
    selected_aisle = st.sidebar.selectbox(L["aisle_sel"], aisle_options)
    bin_options = sorted([loc for loc in l_map.keys() if loc.startswith(selected_aisle)])
    loc_input = st.sidebar.selectbox(L["bin_sel"], [""] + bin_options)

    if loc_input:
        has_cargo = len(l_map[loc_input]['Items']) > 0
        st.sidebar.info(f"系统记录: {'有货' if has_cargo else '空闲'}")
        new_status = st.sidebar.radio("实盘结果:", [L["status_empty"], L["status_used"], L["status_error"]])
        if st.sidebar.button(L["audit_btn"]):
            with st.spinner("正在同步..."):
                save_to_gsheets(loc_input, new_status, staff)
                st.sidebar.success(L["submit_ok"])
                st.rerun()

    # --- 7. 主界面渲染 ---
    st.markdown(f'<h3 style="text-align:center;">{L["title"]}</h3>', unsafe_allow_html=True)
    t_all = sum(s['t_v'] for s in wh_stats.values())
    u_all = sum(s['u_v'] for s in wh_stats.values())
    st.markdown(f'<div class="total-card">{L["total_usage"]}: {(u_all/t_all*100 if t_all>0 else 0):.1f}% ({u_all:.1f}/{t_all:.1f} m³)</div>', unsafe_allow_html=True)

    levels = ["50","40","30","20","10","00"] if selected_wh=='A' else ["40","30","20","10","00"]
    split = 3 if selected_wh=='A' else 2
    all_cols = sorted(list(set(v['Col'] for v in l_map.values() if v['Aisle']==selected_aisle)), reverse=True)
    
    h_str = '<div class="shelf-container"><div class="pillar"></div>'
    for i in range(0, len(all_cols), split):
        bay_cols = all_cols[i : i + split]
        h_str += '<div style="display:flex; flex-direction:row;">'
        col_htmls = ["" for _ in bay_cols]
        for l_idx, lvl in enumerate(levels):
            for c_idx, cid in enumerate(bay_cols):
                f_id = f"{selected_aisle}{cid}{lvl}"
                d = l_map.get(f_id)
                cls, sym = "status-unknown", lvl
                if d:
                    if len(d['Items']) > 0: cls = "status-used"
                    elif d['Status'] == "可用": cls = "status-empty"
                    elif d['Status'] == "不可用": cls, sym = "status-disabled", "❌"
                if f_id in audited_data: cls += " status-audited"
                if loc_input and f_id == loc_input: cls += " status-selected"
                col_htmls[c_idx] += f'<div class="bin-box {cls}">{sym}</div>'
            if l_idx < len(levels) - 1:
                for c_idx in range(len(bay_cols)): col_htmls[c_idx] += '<div class="orange-beam"></div>'
        for idx, c_html in enumerate(col_htmls):
            h_str += f'<div style="display:flex; flex-direction:column; align-items:center; width:40px;">{c_html}<div style="font-size:9px; color:#999;">{bay_cols[idx]}</div></div>'
        h_str += '</div><div class="pillar"></div>'
    st.markdown(h_str + '</div>', unsafe_allow_html=True)

    # 显示云端历史记录
    with st.expander(L["history"]):
        try:
            df_view = conn.read(ttl=0)
            st.dataframe(df_view.sort_values("update_time", ascending=False).head(10), use_container_width=True)
        except: st.write("暂无记录")

else:
    st.error("无法加载 SGF.csv。")