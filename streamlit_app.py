import streamlit as st
import pandas as pd
import requests
import time

# 1. Configurações da página
st.set_page_config(page_title="MDC Inventário 9.7", layout="centered")

# 2. Estilos Customizados (CSS) - 强化手机端窄屏适配
st.markdown("""
    <style>
    /* 强制列容器不折行 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
    }
    
    /* 调整按钮样式，缩小体积以适应单行显示 */
    .stButton > button {
        width: 100% !important;
        padding: 5px 0px !important;
        font-size: 20px !important;
        border-radius: 5px !important;
    }

    #MainMenu, header, footer {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    
    /* Layout das Estantes */
    .shelf-container { display: flex; justify-content: center; align-items: flex-start; padding: 10px 0; background: white; }
    .pillar { width: 10px; background: #3498db; margin: 0 4px; border-radius: 5px; align-self: stretch; min-height: 240px; }
    .bin-col { display: flex; flex-direction: column; width: 60px; }
    .slot { 
        height: 38px; border: 1px solid #eee; margin: 2px 1px; 
        display: flex; align-items: center; justify-content: center; 
        font-weight: bold; font-size: 12px; border-radius: 2px; position: relative;
    }
    .slot::after { content: ""; position: absolute; bottom: -3px; left: 0; width: 100%; height: 4px; background: #fb8c00; border-radius: 2px; }
    .stocked { background: #1976D2; color: #fff; }
    .empty { background: #fff; color: #ccc; }
    .disabled { background: #f5f5f5; color: #ff5252; }
    .bin-label { text-align: center; font-size: 11px; padding: 5px 0; color: #777; font-weight: bold; }
    
    /* Estilo do Seletor (Selectbox) - 修复高度 */
    div[data-baseweb="select"] { font-size: 24px !important; font-weight: bold !important; }
    div[data-baseweb="select"] > div:first-child { height: 65px !important; display: flex !important; align-items: center !important; }
    div[role="listbox"] div { font-size: 22px !important; padding: 12px !important; }
    
    .big-font { font-size: 20px !important; font-weight: bold; color: #ff4b4b; text-align: center; margin: 10px 0; }
    </style>
""", unsafe_allow_html=True)

# --- Processamento de Dados ---
@st.cache_data
def load_data():
    df = pd.read_csv('SGF.csv', dtype=str)
    if '状态' in df.columns:
        df['状态'] = df['状态'].fillna('').str.strip()
    stock_list = df[df['产品参考编码'].notna()]['位置/位置名称'].unique().tolist()
    return df, stock_list

df, has_stock_list = load_data()

# --- Memória de Estado ---
if 's_area' not in st.session_state: st.session_state.s_area = "A"
if 's_rack' not in st.session_state: st.session_state.s_rack = "0.0"
if 'offset' not in st.session_state: st.session_state.offset = 0

# =========================================================
# 🏗️ PARTE SUPERIOR: Visualização
# =========================================================
st.markdown("<h3 style='text-align: center; margin-bottom: 0;'>🏗️ Vista de Estante (MDC)</h3>", unsafe_allow_html=True)

# 库区和货架选择
c1, c2 = st.columns(2)
with c1:
    areas = sorted(df['仓库'].dropna().unique().tolist())
    st.session_state.s_area = st.selectbox("1. Zona", areas, index=areas.index(st.session_state.s_area))
with c2:
    racks = sorted(df[df['仓库'] == st.session_state.s_area]['货架'].dropna().unique().tolist(), key=lambda x: int(float(x)))
    r_labels = [f"{int(float(r)):02d}" for r in racks]
    try: d_idx = racks.index(st.session_state.s_rack)
    except: d_idx = 0
    sel_label = st.selectbox("2. Estante", r_labels, index=d_idx)
    st.session_state.s_rack = racks[r_labels.index(sel_label)]

rack_code = f"{st.session_state.s_area}{sel_label}"

# 导航控制：极致空间压缩，确保图标在同一行
# 使用 5 列布局，让图标居中且紧凑
_, n_left, n_right, _ = st.columns([2, 1, 1, 2])
with n_left:
    if st.button("⬅️"): 
        st.session_state.offset = max(0, st.session_state.offset - 6)
with n_right:
    if st.button("➡️"): 
        st.session_state.offset += 6

# 渲染货架
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
# 🏗️ PARTE CENTRAL: Seleção
# =========================================================
st.divider()
st.markdown('<p class="big-font">📍 Passo 2: Escolha a Posição</p>', unsafe_allow_html=True)

available_locs = []
for b in current_bins:
    for l in lvls:
        available_locs.append(f"{rack_code}{int(float(b)):02d}{int(float(l)):02d}")

target_loc = st.selectbox("Posição", ["-- Selecione --"] + available_locs, label_visibility="collapsed")

# =========================================================
# 🏗️ PARTE INFERIOR: Feedback
# =========================================================
if target_loc != "-- Selecione --":
    st.info(f"📍 Selecionado: **{target_loc}**")
    with st.form("feedback_form", clear_on_submit=True):
        u_name = st.text_input("Seu Nome (Quem está a contar?) *")
        u_issue = st.radio("O que encontrou?", [
            "Sistema diz que tem - Físico está VAZIO", 
            "Sistema diz que está vazio - Físico TEM CARGA", 
            "Posição bloqueada mas tem carga física"
        ], horizontal=False)
        u_note = st.text_area("Notas Adicionais")
        
        if st.form_submit_button("✅ CONFIRMAR INVENTÁRIO", use_container_width=True):
            if not u_name:
                st.error("Por favor, escreva o seu nome!")
            else:
                form_id = "1FAIpQLScdB2DC7CKJKly5vaaqTykfo5wrsdMSIgy3I01KvxAUY_emJQ"
                url = f"https://docs.google.com/forms/d/e/{form_id}/formResponse"
                payload = {
                    "entry.1669427102": u_name, 
                    "entry.738175923": target_loc, 
                    "entry.1676630815": u_issue, 
                    "entry.914821861": u_note
                }
                
                try:
                    response = requests.post(url, data=payload, timeout=10)
                    if response.status_code == 200 or response.status_code == 0:
                        st.toast(f"✅ Enviado: {target_loc}", icon='🚀')
                        st.success("Sincronizado com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Erro: {response.status_code}")
                except:
                    st.error("Erro de rede.")

st.markdown("<br><br><br><br>", unsafe_allow_html=True)