import streamlit as st
import pandas as pd
import os
from datetime import datetime
from supabase import create_client, Client

# --- 1. 初始化配置 ---
st.set_page_config(page_title="MDC Cloud Inventory", layout="wide")

# Supabase 安全连接
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Secrets 配置错误，请检查 Streamlit 后台设置。")

# --- 2. 数据库操作函数 ---
def save_to_supabase(loc, status, staff):
    """使用 upsert 方式同步实盘结果"""
    data = {
        "loc": loc,
        "real_status": status,
        "staff": staff,
        "update_time": datetime.now().isoformat()
    }
    try:
        supabase.table("inventory_audit").upsert(data).execute()
        st.cache_data.clear() 
    except Exception as e:
        st.error(f"数据库写入失败: {e}")

def get_audited_dict():
    """获取已盘点数据用于前端 ✅ 标记"""
    try:
        res = supabase.table("inventory_audit").select("loc, real_status").execute()
        return {item['loc']: item['real_status'] for item in res.data} if res.data else {}
    except:
        return {}

# --- 3. UI 样式 (沿用你 Total WH-Mobile.py 的高性能风格) ---
st.markdown("""
    <style>
    .total-card { background-color: #1e3c72; padding: 12px; border-radius: 8px; color: white; text-align: center; margin-bottom: 15px; }
    .shelf-container { display: flex; flex-wrap: nowrap; overflow-x: auto; padding: 10px; background: white; border: 1px solid #eee; }
    .bin-box { width: 32px; height: 28px; display: flex; align-items: center; justify-content: center; font-size: 9px; font-weight: bold; border: 1px solid #f0f0f0; }
    .status-used { background-color: #3498db !important; color: white; border: none; }
    .status-empty { background-color: #2ecc71 !important; color: white; border: none; }
    .status-disabled { background-color: #95a5a6 !important; color: white; border: none; }
    .status-selected { border: 2px solid #FF4B4B !important; transform: scale(1.1); }
    .status-audited { position: relative; }
    .status-audited::after { content: '✅'; position: absolute; top: -5px; right: -5px; font-size: 9px; }
    .orange-beam { width: 100%; height: 3px; background-color: #ff9800; margin: 1px 0; }
    .pillar { width: 0; height: 180px; border-left: 3px dotted #3498db; margin: 0 8px; opacity: 0.8; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. 数据处理逻辑 ---
@st.cache_data(ttl=60)
def load_data():
    if not os.path.exists("SGF.csv"): return None, None
    try:
        raw_df = pd.read_csv("SGF.csv", low_memory=False)
        df = raw_df.iloc[:, [0, 6, 9, 11, 12, 13, 14]].copy()
        df.columns = ['SKU', 'Loc', 'Qty', 'L', 'W', 'H', 'Status']
        df['Loc'] = df['Loc'].astype(str).str.strip()
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
    except Exception as e:
        st.error(f"SGF数据解析失败: {e}")
        return None, None

l_map, wh_stats = load_data()
audited_data = get_audited_dict()

# --- 5. 侧边栏与交互 ---
if l_map:
    with st.sidebar:
        staff = st.text_input("盘点人/Staff", value="Staff_01")
        st.divider()
        swh = st.selectbox("仓库", sorted(list(wh_stats.keys())))
        aisles = sorted(list(set(v['Aisle'] for v in l_map.values() if v['WH']==swh)))
        saisle = st.selectbox("货道", aisles)
        bins = sorted([loc for loc in l_map.keys() if loc.startswith(saisle)])
        sloc = st.selectbox("选中库位", [""] + bins)

        if sloc:
            st.info(f"系统记录: {'有货' if len(l_map[sloc]['Items'])>0 else '空闲'}")
            res = st.radio("实盘结果:", ["空闲 (Vazio)", "有货 (Ocupado)", "损坏 (Bloqueado)"])
            if st.button("确认提交/Confirm"):
                save_to_supabase(sloc, res, staff)
                st.rerun()

    # --- 6. 主图渲染 ---
    levels = ["50","40","30","20","10","00"] if swh=='A' else ["40","30","20","10","00"]
    split = 3 if swh=='A' else 2
    all_cols = sorted(list(set(v['Col'] for v in l_map.values() if v['Aisle']==saisle)), reverse=True)
    
    h_str = '<div class="shelf-container"><div class="pillar"></div>'
    for i in range(0, len(all_cols), split):
        bay_cols = all_cols[i : i + split]
        h_str += '<div style="display:flex;">'
        col_htmls = ["" for _ in bay_cols]
        for l_idx, lvl in enumerate(levels):
            for c_idx, cid in enumerate(bay_cols):
                fid = f"{saisle}{cid}{lvl}"
                d = l_map.get(fid)
                cls, sym = "status-unknown", lvl
                if d:
                    if len(d['Items']) > 0: cls = "status-used"
                    elif d['Status'] == "可用": cls = "status-empty"
                    elif d['Status'] == "不可用": cls, sym = "status-disabled", "❌"
                
                # 叠加状态
                if fid in audited_data: cls += " status-audited"
                if sloc and fid == sloc: cls += " status-selected"
                
                col_htmls[c_idx] += f'<div class="bin-box {cls}">{sym}</div>'
            if l_idx < len(levels) - 1:
                for c_idx in range(len(bay_cols)): col_htmls[c_idx] += '<div class="orange-beam"></div>'
        
        for idx, c_html in enumerate(col_htmls):
            h_str += f'<div style="display:flex; flex-direction:column; align-items:center; width:38px;">{c_html}<div style="font-size:9px;color:#999;">{bay_cols[idx]}</div></div>'
        h_str += '</div><div class="pillar"></div>'
    
    st.markdown(h_str + '</div>', unsafe_allow_html=True)

    # 底部历史记录查询
    with st.expander("🕒 最近记录 (Latest 15)"):
        try:
            history = supabase.table("inventory_audit").select("*").order("update_time", desc=True).limit(15).execute()
            if history.data:
                st.dataframe(pd.DataFrame(history.data), use_container_width=True)
        except Exception as e:
            st.warning(f"无法读取历史记录: {e}")