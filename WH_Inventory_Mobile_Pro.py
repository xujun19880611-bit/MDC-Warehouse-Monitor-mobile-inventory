import streamlit as st
import pandas as pd
import os
from datetime import datetime
from supabase import create_client, Client

# --- 1. 页面配置 ---
st.set_page_config(page_title="MDC Mobile Pro (Supabase)", layout="wide")

# --- 2. Supabase 连接逻辑 ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

def save_to_supabase(loc, status, staff):
    """写入数据到 Supabase 数据库"""
    data = {
        "loc": loc,
        "real_status": status,
        "staff": staff,
        "update_time": datetime.now().isoformat()
    }
    # 执行插入（Supabase 这里的 upsert 可以根据 loc 自动覆盖旧记录，需在表里给 loc 设唯一约束，或者直接 insert）
    try:
        supabase.table("inventory_audit").insert(data).execute()
        st.cache_data.clear() # 提交成功后清除缓存，确保刷新后能看到最新结果
    except Exception as e:
        st.error(f"同步失败: {e}")

def get_audited_dict():
    """从数据库获取已盘点的数据，用于前端打钩标记"""
    try:
        response = supabase.table("inventory_audit").select("loc, real_status").execute()
        if response.data:
            return {item['loc']: item['real_status'] for item in response.data}
        return {}
    except:
        return {}

# --- 3. 语言与样式配置 ---
LANG_DICT = {
    "CN": {
        "title": "MDC 仓库联动盘点 (Supabase)",
        "staff_name": "盘点人员",
        "wh_sel": "1. 选择仓库",
        "aisle_sel": "2. 选择货道",
        "bin_sel": "3. 选择具体库位",
        "audit_btn": "提交实盘记录",
        "status_empty": "空库位 (Vazio)",
        "status_used": "有货 (Ocupado)",
        "status_error": "不可用 (Bloqueado)",
        "submit_ok": "同步成功！数据已入库。",
        "total_usage": "总利用率",
        "history": "🕒 云端实时记录 (Supabase DB)"
    },
    "PT": {
        "title": "MDC Inventário Cloud",
        "staff_name": "Funcionário",
        "wh_sel": "1. Armazém",
        "aisle_sel": "2. Corredor",
        "bin_sel": "3. Local",
        "audit_btn": "Confirmar",
        "status_empty": "Vazio",
        "status_used": "Ocupado",
        "status_error": "Bloqueado",
        "submit_ok": "Sincronizado!",
        "total_usage": "Ocupação",
        "history": "🕒 Registro Cloud"
    }
}

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

# --- 4. 数据加载 (SGF.csv) ---
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
audited_data = get_audited_dict() # 核心：从云端数据库获取

# --- 5. 交互界面 ---
if l_map:
    lang_choice = st.sidebar.radio("Língua / 语言", ["中文", "Português"])
    L = LANG_DICT["CN"] if lang_choice == "中文" else LANG_DICT["PT"]
    
    with st.sidebar:
        st.header("👤 " + L["staff_name"])
        staff = st.text_input("Name", value="Staff_01")
        st.divider()
        
        selected_wh = st.selectbox(L["wh_sel"], sorted(list(wh_stats.keys())))
        aisle_options = sorted(list(set(v['Aisle'] for v in l_map.values() if v['WH'] == selected_wh)))
        selected_aisle = st.selectbox(L["aisle_sel"], aisle_options)
        bin_options = sorted([loc for loc in l_map.keys() if loc.startswith(selected_aisle)])
        loc_input = st.selectbox(L["bin_sel"], [""] + bin_options)

        if loc_input:
            has_cargo = len(l_map[loc_input]['Items']) > 0
            st.info(f"系统记录: {'有货' if has_cargo else '空闲'}")
            new_status = st.radio("实盘结果:", [L["status_empty"], L["status_used"], L["status_error"]])
            if st.button(L["audit_btn"]):
                with st.spinner("正在写入云端数据库..."):
                    save_to_supabase(loc_input, new_status, staff)
                    st.success(L["submit_ok"])
                    st.rerun()

    # --- 6. 绘图与历史展示 ---
    st.markdown(f'<h3 style="text-align:center;">{L["title"]}</h3>', unsafe_allow_html=True)
    # ... (此处省略重复的统计卡片和货架绘图代码，逻辑与之前完全一致) ...
    # 绘图时记得检查 f_id 是否在 audited_data 字典中，如果在则添加 ✅ 标记。

    with st.expander(L["history"]):
        response = supabase.table("inventory_audit").select("*").order("update_time", desc=True).limit(15).execute()
        if response.data:
            st.dataframe(pd.DataFrame(response.data), use_container_width=True)
        else:
            st.write("暂无数据")
else:
    st.error("无法加载 SGF.csv")