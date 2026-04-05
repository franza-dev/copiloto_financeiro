import os
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import extra_streamlit_components as stx

_FAVICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "guido_favicon.svg")
st.set_page_config(
    page_title="guido",
    page_icon=_FAVICON_PATH if os.path.exists(_FAVICON_PATH) else "🌱",
    layout="wide",
    initial_sidebar_state="expanded",  # sidebar do Guido nunca nasce colapsada
)

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

cookie_manager = stx.CookieManager()

# ==========================================
# IDENTIDADE VISUAL GUIDO
# Paleta verde-noite, Georgia serif, system-ui sans
# chamaoguido.com.br
# ==========================================
st.markdown("""
    <style>
        :root {
            --guido-green:         #1D9E75;
            --guido-green-deep:    #085041;
            --guido-green-mid:     #9FE1CB;
            --guido-green-light:   #E1F5EE;
            --guido-amber:         #F5A623;
            --guido-amber-light:   #FEF3DC;
            --guido-night:         #111827;
            --guido-night-surface: #1E293B;
            --guido-night-border:  #334155;
            --guido-off-white:     #F7F5F0;
            --guido-text-primary:  #F7F5F0;
            --guido-text-secondary:#94A3B8;
            --guido-text-muted:    #64748B;
            --guido-font-serif:    Georgia, 'Times New Roman', serif;
            --guido-font-sans:     system-ui, -apple-system, 'Segoe UI', sans-serif;
            --guido-radius-md:     10px;
            --guido-radius-lg:     16px;
        }

        html, body, [class*="css"], .stApp {
            font-family: var(--guido-font-sans) !important;
            background-color: var(--guido-night) !important;
            color: var(--guido-text-primary) !important;
        }
        /* Esconde elementos do chrome do Streamlit MAS mantém o header visível,
           porque é dentro dele que fica o botão de reabrir a sidebar colapsada. */
        #MainMenu { display: none !important; }
        footer { display: none !important; }
        [data-testid="stToolbar"] { display: none !important; }
        header[data-testid="stHeader"] {
            background: transparent !important;
        }
        /* Sidebar do Guido é fixa — esconde qualquer controle de colapsar
           (o botão X dentro da sidebar e o chevron no header que fecha ela).
           Com isso, combinado com initial_sidebar_state="expanded", a sidebar
           nasce expandida e não tem como ser colapsada. */
        [data-testid="stSidebarCollapseButton"],
        button[kind="headerNoPadding"][aria-label*="sidebar" i],
        button[kind="headerNoPadding"][aria-label*="Collapse" i],
        button[data-testid="baseButton-headerNoPadding"] {
            display: none !important;
        }
        /* Garantia extra: se por algum motivo a sidebar estiver colapsada
           (sessão antiga, cache), o botão de reabrir precisa estar visível. */
        [data-testid="stSidebarCollapsedControl"] {
            visibility: visible !important;
            display: flex !important;
        }

        /* Títulos em Georgia serif — DNA da marca */
        h1 {
            font-family: var(--guido-font-serif) !important;
            font-weight: 400 !important;
            font-size: 2.4rem !important;
            color: var(--guido-text-primary) !important;
            letter-spacing: -1px !important;
            margin-bottom: 0.25rem !important;
        }
        h2, h3, h4 {
            font-family: var(--guido-font-serif) !important;
            font-weight: 400 !important;
            color: var(--guido-text-primary) !important;
            letter-spacing: -0.3px !important;
        }

        /* Sidebar — tom mais escuro que o fundo principal */
        [data-testid="stSidebar"] {
            background-color: var(--guido-night-surface) !important;
            border-right: 1px solid var(--guido-night-border) !important;
        }
        [data-testid="stSidebar"] * {
            font-family: var(--guido-font-sans) !important;
            color: var(--guido-text-primary) !important;
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4 {
            font-family: var(--guido-font-serif) !important;
        }
        [data-testid="stSidebarNav"] { display: none; }

        /* Tabs — pílulas minimalistas */
        [data-baseweb="tab-list"] {
            background-color: var(--guido-night-surface) !important;
            border-radius: var(--guido-radius-lg) !important;
            padding: 4px !important;
            gap: 4px !important;
            border: 1px solid var(--guido-night-border) !important;
        }
        [data-baseweb="tab"] {
            font-family: var(--guido-font-sans) !important;
            font-weight: 500 !important;
            color: var(--guido-text-secondary) !important;
            background-color: transparent !important;
            border-radius: var(--guido-radius-md) !important;
            padding: 8px 18px !important;
            border: none !important;
            transition: all 0.2s !important;
        }
        [aria-selected="true"][data-baseweb="tab"] {
            background: var(--guido-green) !important;
            color: #ffffff !important;
        }
        [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none !important; }

        /* Botões — verde sólido, sem gradiente */
        .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
            font-family: var(--guido-font-sans) !important;
            font-weight: 500 !important;
            font-size: 0.95rem !important;
            border-radius: var(--guido-radius-md) !important;
            padding: 0.65em 1.8em !important;
            border: none !important;
            transition: all 0.15s ease !important;
            background: var(--guido-green) !important;
            color: #ffffff !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2) !important;
        }
        .stButton > button:hover, .stFormSubmitButton > button:hover {
            background: var(--guido-green-deep) !important;
            transform: translateY(-1px) !important;
        }
        .stButton > button[kind="secondary"] {
            background: transparent !important;
            color: var(--guido-green) !important;
            border: 1.5px solid var(--guido-green) !important;
            box-shadow: none !important;
        }
        .stButton > button[kind="secondary"]:hover {
            background: rgba(29,158,117,0.08) !important;
            color: var(--guido-green) !important;
        }

        /* Inputs — fundo escuro com borda sutil */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div,
        .stTextArea textarea {
            font-family: var(--guido-font-sans) !important;
            background-color: var(--guido-night-surface) !important;
            border: 1.5px solid var(--guido-night-border) !important;
            border-radius: var(--guido-radius-md) !important;
            color: var(--guido-text-primary) !important;
        }
        .stTextInput > div > div > input:focus,
        .stNumberInput > div > div > input:focus,
        .stTextArea textarea:focus {
            border-color: var(--guido-green) !important;
            box-shadow: 0 0 0 3px rgba(29,158,117,0.15) !important;
        }

        /* Labels — discretas, caixa baixa */
        label, .stSelectbox label, .stTextInput label, .stNumberInput label, .stRadio label {
            font-family: var(--guido-font-sans) !important;
            font-weight: 500 !important;
            color: var(--guido-text-secondary) !important;
            font-size: 0.82rem !important;
            letter-spacing: 0 !important;
            text-transform: none !important;
        }

        /* Containers — cards sóbrios */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: var(--guido-night-surface) !important;
            border: 1px solid var(--guido-night-border) !important;
            border-radius: var(--guido-radius-lg) !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
            padding: 1rem !important;
        }

        /* Metrics — KPIs */
        [data-testid="stMetric"] {
            background-color: var(--guido-night-surface) !important;
            border: 1px solid var(--guido-night-border) !important;
            border-radius: var(--guido-radius-lg) !important;
            padding: 1.1rem 1.4rem !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
        }
        [data-testid="stMetricLabel"] {
            font-family: var(--guido-font-sans) !important;
            font-size: 0.8rem !important;
            font-weight: 500 !important;
            color: var(--guido-text-secondary) !important;
            text-transform: none !important;
            letter-spacing: 0 !important;
        }
        [data-testid="stMetricValue"] {
            font-family: var(--guido-font-serif) !important;
            font-weight: 400 !important;
            font-size: 1.9rem !important;
            color: var(--guido-green-mid) !important;
        }

        /* Progress bar — verde */
        [data-testid="stProgressBar"] > div {
            background-color: var(--guido-night-border) !important;
            border-radius: 9999px !important;
        }
        [data-testid="stProgressBar"] > div > div {
            background: var(--guido-green) !important;
            border-radius: 9999px !important;
        }

        /* Dataframes, alerts, spinner, captions */
        [data-testid="stDataFrame"], .stDataEditor {
            border: 1px solid var(--guido-night-border) !important;
            border-radius: var(--guido-radius-md) !important;
            overflow: hidden !important;
        }
        hr { border-color: var(--guido-night-border) !important; margin: 1.5rem 0 !important; }
        [data-testid="stAlert"] {
            border-radius: var(--guido-radius-md) !important;
            border: none !important;
            font-family: var(--guido-font-sans) !important;
        }
        .stSpinner > div { border-top-color: var(--guido-green) !important; }
        .stCaption, caption {
            color: var(--guido-text-muted) !important;
            font-family: var(--guido-font-sans) !important;
        }

        /* Card de login — destaque central */
        .guido-login-card {
            background: var(--guido-night-surface);
            border: 1px solid var(--guido-night-border);
            border-radius: 20px;
            padding: 2.5rem 2rem;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }

        /* Header com logo Guido */
        .guido-header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 0.5rem;
        }
        .guido-header-text h1 {
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1 !important;
        }
        .guido-header-text p {
            margin: 4px 0 0 0;
            color: var(--guido-text-secondary);
            font-family: var(--guido-font-sans);
            font-size: 0.88rem;
            font-style: italic;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# LOGOTIPO GUIDO — v1.1 (logo oficial com óculos)
# Anatomia: óculos em cima + "G" verde + "uido" escuro, lado a lado
# viewBox canônico do logo completo: 210×145
# viewBox canônico do ícone solo dos óculos: 155×52
# ==========================================
def logo_guido_svg(width: int = 200, color_g: str = "#1D9E75", color_word: str = "#F7F5F0", color_glasses: str | None = None) -> str:
    """Logo oficial Guido (óculos + Guido horizontal).

    `width`: largura em px. Altura é calculada proporcionalmente (260:145).
    `color_word`: cor da parte "uido" — use #111827 em fundo claro, #F7F5F0 em escuro.
    `color_glasses`: cor dos óculos — default igual ao G.

    Nota: viewBox width é 260 (não 210 como no manual) porque o 'uido' em Georgia 86px
    com letter-spacing -2 estende até x≈241, então precisamos de folga à direita.
    """
    if color_glasses is None:
        color_glasses = color_g
    h = int(width * 145 / 260)
    return f'''<svg width="{width}" height="{h}" viewBox="0 0 260 145" xmlns="http://www.w3.org/2000/svg" overflow="visible">
        <line x1="26" y1="21" x2="4" y2="10" stroke="{color_glasses}" stroke-width="2.2" stroke-linecap="round"/>
        <rect x="26" y="14" width="36" height="25" rx="6" fill="none" stroke="{color_glasses}" stroke-width="2.2"/>
        <line x1="62" y1="26" x2="88" y2="26" stroke="{color_glasses}" stroke-width="2.2" stroke-linecap="round"/>
        <rect x="88" y="14" width="36" height="25" rx="6" fill="none" stroke="{color_glasses}" stroke-width="2.2"/>
        <line x1="124" y1="21" x2="148" y2="10" stroke="{color_glasses}" stroke-width="2.2" stroke-linecap="round"/>
        <text x="4" y="132" font-family="Georgia,'Times New Roman',serif" font-size="86" font-weight="400" fill="{color_g}" text-anchor="start" letter-spacing="-2">G</text>
        <text x="62" y="132" font-family="Georgia,'Times New Roman',serif" font-size="86" font-weight="400" fill="{color_word}" text-anchor="start" letter-spacing="-2">uido</text>
    </svg>'''

def icone_oculos_svg(width: int = 56, color: str = "#1D9E75") -> str:
    """Ícone autônomo dos óculos — sem wordmark.
    Usado em contextos de espaço limitado: header do painel, sidebar, avatar, favicon."""
    h = int(width * 52 / 155)
    return f'''<svg width="{width}" height="{h}" viewBox="0 0 155 52" xmlns="http://www.w3.org/2000/svg">
        <line x1="18" y1="17" x2="2" y2="5" stroke="{color}" stroke-width="5.5" stroke-linecap="round"/>
        <rect x="18" y="8" width="40" height="28" rx="7" fill="none" stroke="{color}" stroke-width="5.5"/>
        <line x1="58" y1="22" x2="97" y2="22" stroke="{color}" stroke-width="5.5" stroke-linecap="round"/>
        <rect x="97" y="8" width="40" height="28" rx="7" fill="none" stroke="{color}" stroke-width="5.5"/>
        <line x1="137" y1="17" x2="153" y2="5" stroke="{color}" stroke-width="5.5" stroke-linecap="round"/>
    </svg>'''

# ==========================================
# AUTENTICAÇÃO — restaura sessão do cookie
# ==========================================
if "usuario_id" not in st.session_state:
    cookie_id   = cookie_manager.get("usuario_id")
    cookie_nome = cookie_manager.get("usuario_nome")
    if cookie_id and cookie_nome:
        st.session_state.usuario_id   = int(cookie_id)
        st.session_state.usuario_nome = cookie_nome

if "usuario_id" not in st.session_state:
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown(f"""
            <div style="text-align:center; margin-bottom: 2rem;">
                <div style="display:inline-flex; margin-bottom: 0.75rem;">
                    {logo_guido_svg(width=280, color_word="#F7F5F0")}
                </div>
                <p style="color:#94A3B8; font-size:0.95rem; margin: 0.25rem 0 0 0; font-family: Georgia, serif; font-style: italic; line-height: 1.5;">
                    Seu braço direito pra separar<br>o dinheiro da casa do dinheiro do negócio.
                </p>
                <p style="color:#64748B; font-size:0.78rem; margin: 0.75rem 0 0 0;">chamaoguido.com.br</p>
            </div>
        """, unsafe_allow_html=True)

        if "auth_msg" in st.session_state:
            msg = st.session_state.pop("auth_msg")
            if msg["tipo"] == "erro":
                st.error(msg["texto"])
            else:
                st.warning(msg["texto"])

        aba_login, aba_registro = st.tabs(["Entrar", "Criar Conta"])

        with aba_login:
            with st.form("form_login"):
                email = st.text_input("E-mail", placeholder="seu@email.com")
                senha = st.text_input("Senha", type="password", placeholder="••••••••")
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                entrar = st.form_submit_button("Entrar", use_container_width=True, type="primary")

            if entrar:
                if email and senha:
                    try:
                        res = requests.post(f"{API_URL}/auth/login", json={"email": email, "senha": senha})
                        if res.status_code == 200:
                            u = res.json()
                            st.session_state.usuario_id   = u["id"]
                            st.session_state.usuario_nome = u["nome"]
                            cookie_manager.set("usuario_id",   str(u["id"]),  key="set_id_login")
                            cookie_manager.set("usuario_nome", u["nome"],     key="set_nome_login")
                            st.rerun()
                        elif res.status_code == 401:
                            st.session_state.auth_msg = {"tipo": "erro", "texto": "E-mail ou senha incorretos."}
                            st.rerun()
                        else:
                            st.session_state.auth_msg = {"tipo": "erro", "texto": f"Erro no servidor ({res.status_code})."}
                            st.rerun()
                    except Exception as e:
                        st.session_state.auth_msg = {"tipo": "erro", "texto": f"API offline. Detalhe: {e}"}
                        st.rerun()
                else:
                    st.session_state.auth_msg = {"tipo": "aviso", "texto": "Preencha e-mail e senha."}
                    st.rerun()

        with aba_registro:
            with st.form("form_registro"):
                nome_reg = st.text_input("Nome completo", placeholder="Seu nome")
                email_reg = st.text_input("E-mail", placeholder="seu@email.com", key="email_reg")
                senha_reg = st.text_input("Senha", type="password", placeholder="Mínimo 6 caracteres", key="senha_reg")
                senha_conf = st.text_input("Confirmar senha", type="password", placeholder="Repita a senha")
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                criar = st.form_submit_button("Criar Conta", use_container_width=True, type="primary")

            if criar:
                if nome_reg and email_reg and senha_reg and senha_conf:
                    if senha_reg != senha_conf:
                        st.session_state.auth_msg = {"tipo": "erro", "texto": "As senhas não coincidem."}
                        st.rerun()
                    elif len(senha_reg) < 6:
                        st.session_state.auth_msg = {"tipo": "aviso", "texto": "A senha deve ter pelo menos 6 caracteres."}
                        st.rerun()
                    else:
                        try:
                            res = requests.post(f"{API_URL}/auth/registrar", json={"nome": nome_reg, "email": email_reg, "senha": senha_reg})
                            if res.status_code == 200:
                                u = res.json()
                                st.session_state.usuario_id   = u["id"]
                                st.session_state.usuario_nome = u["nome"]
                                cookie_manager.set("usuario_id",   str(u["id"]), key="set_id_reg")
                                cookie_manager.set("usuario_nome", u["nome"],    key="set_nome_reg")
                                st.rerun()
                            elif res.status_code == 400:
                                st.session_state.auth_msg = {"tipo": "erro", "texto": "Este e-mail já está cadastrado."}
                                st.rerun()
                            else:
                                st.session_state.auth_msg = {"tipo": "erro", "texto": f"Erro no servidor ({res.status_code})."}
                                st.rerun()
                        except Exception as e:
                            st.session_state.auth_msg = {"tipo": "erro", "texto": f"API offline. Detalhe: {e}"}
                            st.rerun()
                else:
                    st.session_state.auth_msg = {"tipo": "aviso", "texto": "Preencha todos os campos."}
                    st.rerun()

    st.stop()

# ==========================================
# APP PRINCIPAL (usuário autenticado)
# ==========================================
USUARIO_ID = st.session_state.usuario_id

# --- HEADER — ícone oficial dos óculos + saudação ---
st.markdown(f"""
    <div class="guido-header">
        <div style="display:flex; align-items:center; justify-content:center; width:72px; height:72px; background: rgba(29,158,117,0.08); border: 1px solid rgba(29,158,117,0.25); border-radius: 16px;">
            {icone_oculos_svg(width=52)}
        </div>
        <div class="guido-header-text">
            <h1>Oi, {st.session_state.usuario_nome.split()[0]}.</h1>
            <p>Chama o Guido. Eu cuido do seu dinheiro.</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.markdown(
    f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:0.5rem;">{icone_oculos_svg(width=38)}'
    f'<span style="font-family:Georgia,serif;font-size:1.5rem;color:#F7F5F0;letter-spacing:-0.5px;">guido</span></div>',
    unsafe_allow_html=True,
)
st.sidebar.caption(f"Logado como **{st.session_state.usuario_nome.split()[0]}**")
if st.sidebar.button("Sair", use_container_width=True):
    cookie_manager.delete("usuario_id",   key="del_id")
    cookie_manager.delete("usuario_nome", key="del_nome")
    del st.session_state.usuario_id
    del st.session_state.usuario_nome
    st.rerun()

st.sidebar.divider()
st.sidebar.markdown("### 📅 Período")

from datetime import datetime as _dt
_ano_atual = _dt.now().year
_mes_atual = _dt.now().month
_MESES = [
    "Ano todo", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]
_anos_opcoes = list(range(_ano_atual, _ano_atual - 6, -1))

filtro_ano = st.sidebar.selectbox("Ano", _anos_opcoes, index=0, key="filtro_ano")
filtro_mes_label = st.sidebar.selectbox(
    "Mês", _MESES, index=_mes_atual, key="filtro_mes_label"
)
# índice 0 = "Ano todo" → mes = None; 1..12 → mês correspondente
filtro_mes = None if filtro_mes_label == "Ano todo" else _MESES.index(filtro_mes_label)

# Parâmetros de período usados em todas as chamadas
PARAMS_PERIODO = {"ano": filtro_ano}
if filtro_mes:
    PARAMS_PERIODO["mes"] = filtro_mes

if filtro_mes:
    st.sidebar.caption(f"Mostrando **{filtro_mes_label}/{filtro_ano}**")
else:
    st.sidebar.caption(f"Mostrando o **ano de {filtro_ano}**")

st.sidebar.divider()
st.sidebar.markdown("### 💼 Seu dinheiro agora")
st.sidebar.caption("Só o que já tá confirmado")

try:
    resumo_req = requests.get(
        f"{API_URL}/dashboard/resumo",
        params={"usuario_id": USUARIO_ID, **PARAMS_PERIODO},
    )
    if resumo_req.status_code == 200:
        resumo = resumo_req.json()
        st.sidebar.markdown("**🏢 Negócio**")
        st.sidebar.write(f"↗ Entrou: **{resumo['pj']['receitas']}**")
        st.sidebar.write(f"↙ Saiu: **{resumo['pj']['despesas']}**")
        st.sidebar.metric("Sobrou pro negócio", resumo['pj']['saldo'])
        st.sidebar.divider()
        st.sidebar.markdown("**🏠 Casa**")
        st.sidebar.write(f"↗ Entrou: **{resumo['pf']['receitas']}**")
        st.sidebar.write(f"↙ Saiu: **{resumo['pf']['despesas']}**")
        st.sidebar.metric("Sobrou pra casa", resumo['pf']['saldo'])
    if st.sidebar.button("🔄 Atualizar", use_container_width=True):
        st.rerun()
except:
    st.sidebar.error("API offline. Chama de novo daqui a pouco.")

# --- CONTAS DO USUÁRIO ---
contas = []
opcoes_contas = {}
nomes_contas = []
id_para_nome = {}
try:
    req_contas = requests.get(f"{API_URL}/contas/{USUARIO_ID}")
    if req_contas.status_code == 200:
        contas = req_contas.json()
        opcoes_contas = {f"{c['nome']} ({c['tipo']})": c['id'] for c in contas}
        nomes_contas = list(opcoes_contas.keys())
        id_para_nome = {v: k for k, v in opcoes_contas.items()}
except:
    pass

LISTA_BASE = [
    "Vendas / Receitas", "Prestação de Serviços", "Transferência Interna",
    "Alimentação", "Transporte e Combustível", "Impostos (DAS, etc)",
    "Ferramentas e Software", "Tarifas Bancárias", "Pró-Labore / Salário",
    "Equipamentos", "A Classificar"
]

# --- ABAS ---
aba_dashboard, aba_extrato, aba_contas, aba_categorias = st.tabs(["🌱 Painel", "🧾 Histórico", "🏦 Contas", "📂 Categorias & Metas"])

# ==========================================
# ABA 1: PAINEL
# ==========================================
with aba_dashboard:
    st.markdown("### 📝 O que saiu hoje?")
    texto_input = st.text_input("Conta pro Guido", placeholder="Ex: gastei 45 no Uber pra reunião do negócio", label_visibility="collapsed")
    audio_input = st.audio_input("🎙️ Ou grava um áudio")

    if st.button("Manda pro Guido", use_container_width=True):
        if texto_input:
            with st.spinner("O Guido tá ouvindo..."):
                res = requests.post(f"{API_URL}/transacoes/ia", params={"texto": texto_input, "usuario_id": USUARIO_ID})
                if res.status_code == 200:
                    st.success("Anotado. Dá uma olhada na revisão aí embaixo.")
                    st.rerun()
                else:
                    st.error("Deu ruim aqui. Tenta de novo?")
        elif audio_input:
            with st.spinner("O Guido tá ouvindo seu áudio..."):
                res_audio = requests.post(
                    f"{API_URL}/transacoes/ia/audio",
                    params={"usuario_id": USUARIO_ID},
                    files={"file": ("audio.wav", audio_input.getvalue(), "audio/wav")}
                )
                if res_audio.status_code == 200:
                    st.success("Anotado. Confere aí na revisão.")
                    st.rerun()
                else:
                    st.error("Deu ruim com o áudio. Tenta de novo?")
        else:
            st.warning("Escreve ou grava algo primeiro.")
    st.divider()

    st.markdown("### 📂 Subir extrato do banco (CSV)")
    with st.expander("Já tem um extrato baixado? Manda aqui."):
        if not nomes_contas:
            st.warning("Cadastra uma conta na aba 'Contas' primeiro.")
        else:
            conta_upload = st.selectbox("Esse extrato é de qual conta?", nomes_contas, key="upload_conta")
            id_conta_upload = opcoes_contas[conta_upload]
            arquivo = st.file_uploader("Selecione o arquivo .CSV", type=["csv"])
            st.caption("Baixe o extrato no formato CSV no app do seu banco.")

            if arquivo and st.button("Processar Arquivo 🚀", use_container_width=True):
                try:
                    arquivo.seek(0)
                    df_extrato = pd.read_csv(arquivo, sep=None, engine='python', header=None)
                    header_idx = 0
                    for i in range(min(15, len(df_extrato))):
                        linha_texto = df_extrato.iloc[i].astype(str).str.lower().tolist()
                        if any('valor' in c for c in linha_texto) and any('descri' in c or 'hist' in c for c in linha_texto):
                            header_idx = i
                            break
                    df_extrato.columns = df_extrato.iloc[header_idx].astype(str).str.lower()
                    df_extrato = df_extrato.iloc[header_idx+1:].reset_index(drop=True)
                    col_desc = next((c for c in df_extrato.columns if 'descri' in c or 'historico' in c), None)
                    col_val  = next((c for c in df_extrato.columns if 'valor' in c), None)
                    col_data = next((c for c in df_extrato.columns if 'data' in c or 'vencimento' in c or 'date' in c), None)
                    if col_desc and col_val:
                        transacoes_para_api = []
                        for _, row in df_extrato.iterrows():
                            val_str = str(row[col_val]).strip()
                            try:
                                if val_str and val_str.lower() not in ['nan', 'none']:
                                    valor_float = float(val_str.replace(',', '.'))
                                    data_extrato = str(row[col_data])[:10] if col_data and pd.notna(row[col_data]) else ""
                                    if valor_float != 0:
                                        transacoes_para_api.append({"data": data_extrato, "descricao": str(row[col_desc]), "valor": valor_float})
                            except ValueError:
                                pass
                        payload = {"conta_id": id_conta_upload, "usuario_id": USUARIO_ID, "transacoes": transacoes_para_api}
                        res_lote = requests.post(f"{API_URL}/transacoes/lote", json=payload)
                        if res_lote.status_code == 200:
                            st.success("As transações foram enviadas para a Quarentena.")
                            st.rerun()
                        else:
                            st.error("Erro ao enviar lote para a API.")
                    else:
                        st.error("Não consegui achar as colunas no seu arquivo.")
                except Exception as e:
                    st.error(f"Erro ao ler o CSV. Detalhe: {e}")

    st.divider()

    col_grafico, col_quarentena = st.columns([1, 1.5])

    with col_grafico:
        st.markdown("### 📈 Sua grana")
        try:
            if 'resumo' in locals():
                pj_val = float(resumo["pj"]["despesas"].replace("R$ ", "").replace(",", ""))
                pf_val = float(resumo["pf"]["despesas"].replace("R$ ", "").replace(",", ""))
                total_gasto = pj_val + pf_val
                if total_gasto > 0:
                    fig = go.Figure(data=[go.Pie(
                        labels=["🏢 Negócio", "🏠 Casa"],
                        values=[pj_val, pf_val],
                        hole=0.72,
                        marker=dict(
                            colors=["#1D9E75", "#9FE1CB"],
                            line=dict(color="#111827", width=4),
                        ),
                        textinfo="none",
                        hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>",
                        sort=False,
                    )])
                    fig.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="system-ui, sans-serif", color="#F7F5F0"),
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.15,
                            xanchor="center",
                            x=0.5,
                            font=dict(size=13),
                        ),
                        margin=dict(l=10, r=10, t=10, b=40),
                        height=320,
                        annotations=[
                            dict(
                                text=f"<span style='font-family:Georgia,serif;font-size:13px;color:#94A3B8'>saiu total</span><br>"
                                     f"<span style='font-family:Georgia,serif;font-size:26px;color:#9FE1CB'>R$ {total_gasto:,.0f}</span>",
                                x=0.5, y=0.5,
                                font_size=13,
                                showarrow=False,
                                align="center",
                            )
                        ],
                    )
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                else:
                    st.caption("Nada saiu ainda nesse período. Chama o Guido quando gastar algo.")

            req_hist_grafico = requests.get(f"{API_URL}/transacoes/historico", params={"usuario_id": USUARIO_ID, **PARAMS_PERIODO})
            if req_hist_grafico.status_code == 200:
                hist_grafico = req_hist_grafico.json()
                if hist_grafico:
                    df_hist_graf = pd.DataFrame(hist_grafico)
                    df_desp = df_hist_graf[(df_hist_graf['valor'] < 0) & (~df_hist_graf['categoria'].str.contains('Transferência Interna', case=False, na=False))].copy()
                    if not df_desp.empty:
                        df_desp['valor_abs'] = df_desp['valor'].abs()
                        df_agrupado = (df_desp.groupby(['categoria', 'tipo'])['valor_abs']
                                             .sum().reset_index()
                                             .sort_values('valor_abs', ascending=True))
                        # Renomeia PF/PJ para vocabulário Guido só na exibição
                        df_agrupado['origem'] = df_agrupado['tipo'].map({'PJ': '🏢 Negócio', 'PF': '🏠 Casa'})

                        st.markdown("#### 📊 Onde o dinheiro foi")
                        fig2 = go.Figure()
                        for origem, cor in [('🏢 Negócio', '#1D9E75'), ('🏠 Casa', '#9FE1CB')]:
                            sub = df_agrupado[df_agrupado['origem'] == origem]
                            if not sub.empty:
                                fig2.add_trace(go.Bar(
                                    y=sub['categoria'],
                                    x=sub['valor_abs'],
                                    name=origem,
                                    orientation='h',
                                    marker=dict(
                                        color=cor,
                                        line=dict(width=0),
                                    ),
                                    hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra>" + origem + "</extra>",
                                ))
                        fig2.update_layout(
                            template="plotly_dark",
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(family="system-ui, sans-serif", color="#F7F5F0", size=12),
                            barmode='stack',
                            bargap=0.35,
                            showlegend=True,
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=-0.18,
                                xanchor="center",
                                x=0.5,
                            ),
                            margin=dict(l=10, r=10, t=10, b=40),
                            height=max(260, 40 * df_agrupado['categoria'].nunique() + 80),
                            xaxis=dict(
                                showgrid=True,
                                gridcolor="rgba(148,163,184,0.1)",
                                zeroline=False,
                                tickprefix="R$ ",
                                tickformat=",.0f",
                            ),
                            yaxis=dict(
                                showgrid=False,
                                tickfont=dict(family="Georgia, serif", size=13),
                            ),
                        )
                        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        except Exception:
            st.info("Ainda não tem dados pra mostrar. Manda um gasto pro Guido!")

    with col_quarentena:
        st.markdown("### ⏳ Pra revisar")
        st.caption("O Guido anotou, mas quer sua confirmação antes de entrar na conta.")
        if st.button("🧹 Limpar tudo", use_container_width=True):
            res_limpar = requests.delete(f"{API_URL}/sistema/limpar-quarentena", params={"usuario_id": USUARIO_ID})
            if res_limpar.status_code == 200:
                st.success("Tudo limpo.")
                st.rerun()

        try:
            res_quarentena = requests.get(f"{API_URL}/transacoes/quarentena", params={"usuario_id": USUARIO_ID})
            if res_quarentena.status_code == 200:
                transacoes = res_quarentena.json().get("transacoes", [])
                if transacoes:
                    if not nomes_contas:
                        st.warning("Cadastra pelo menos uma conta na aba 'Contas' primeiro.")
                    else:
                        categorias_aprendidas = set()
                        try:
                            req_hist = requests.get(f"{API_URL}/transacoes/historico", params={"usuario_id": USUARIO_ID})
                            if req_hist.status_code == 200:
                                categorias_aprendidas = {x['categoria'] for x in req_hist.json()}
                        except: pass

                        lista_dinamica = sorted(list(set(LISTA_BASE) | categorias_aprendidas))
                        lista_dinamica.append("Outra...")

                        for t in transacoes:
                            titulo_expander = f"🛒 {t.get('data','')} | {t['descricao']} - R$ {t['valor']:.2f}"
                            with st.expander(titulo_expander, expanded=True):
                                col_d, col_de, col_v = st.columns([1,2,1])
                                ed_data = col_d.text_input("Data", value=t.get('data',''), key=f"d_{t['id']}")
                                ed_desc = col_de.text_input("Descrição", value=t['descricao'], key=f"de_{t['id']}")
                                ed_val  = col_v.number_input("Valor", value=float(t['valor']), step=0.01, key=f"v_{t['id']}")

                                c1, c2, c3 = st.columns(3)
                                cat_atual = t['categoria']
                                lista_local = lista_dinamica.copy()
                                if cat_atual not in lista_local:
                                    lista_local.insert(0, cat_atual)
                                escolha_cat = c1.selectbox("Categoria", lista_local, index=lista_local.index(cat_atual), key=f"sel_cat_{t['id']}")
                                nova_cat = c1.text_input("Qual nova categoria?", key=f"txt_cat_{t['id']}") if escolha_cat == "Outra..." else escolha_cat

                                # Mostra Casa/Negócio, salva PF/PJ (compat com banco)
                                opcoes_tipo_label = ["🏠 Casa", "🏢 Negócio"]
                                mapa_tipo = {"🏠 Casa": "PF", "🏢 Negócio": "PJ"}
                                mapa_tipo_inv = {"PF": "🏠 Casa", "PJ": "🏢 Negócio"}
                                idx_tipo = opcoes_tipo_label.index(mapa_tipo_inv.get(t['tipo'], "🏠 Casa"))
                                label_tipo = c2.selectbox("É de onde?", opcoes_tipo_label, index=idx_tipo, key=f"tipo_{t['id']}")
                                novo_tipo = mapa_tipo[label_tipo]

                                conta_id_salva = t.get('conta_id')
                                idx_conta = nomes_contas.index(id_para_nome[conta_id_salva]) if conta_id_salva in id_para_nome else 0
                                conta_selecionada = c3.selectbox("Pago com", nomes_contas, index=idx_conta, key=f"conta_{t['id']}")
                                id_conta_escolhida = opcoes_contas[conta_selecionada]

                                c_btn1, c_btn2 = st.columns(2)
                                if c_btn1.button("Confirmar ✅", key=f"btn_{t['id']}", use_container_width=True):
                                    payload = {"data": ed_data, "descricao": ed_desc, "valor": ed_val, "categoria": nova_cat, "tipo": novo_tipo, "conta_id": id_conta_escolhida}
                                    if requests.patch(f"{API_URL}/transacoes/{t['id']}/confirmar", json=payload).status_code == 200:
                                        st.rerun()
                                if c_btn2.button("Apagar 🗑️", key=f"del_{t['id']}", use_container_width=True):
                                    requests.delete(f"{API_URL}/transacoes/{t['id']}")
                                    st.rerun()
                else:
                    st.success("Tudo em dia. O Guido não tem nada pra te pedir agora. ✨")
            else:
                st.error("O backend tá offline.")
        except Exception:
            st.error("Aguardando a API...")

# ==========================================
# ABA 2: EXTRATO
# ==========================================
with aba_extrato:
    st.markdown("### 🧾 Tudo que já passou pelo Guido")
    try:
        req_historico = requests.get(f"{API_URL}/transacoes/historico", params={"usuario_id": USUARIO_ID, **PARAMS_PERIODO})
        if req_historico.status_code == 200:
            historico = req_historico.json()
            if historico:
                df_historico = pd.DataFrame(historico)
                c_filtro1, _ = st.columns(2)
                filtro_label = c_filtro1.selectbox("Mostrar", ["Tudo", "🏠 Casa", "🏢 Negócio"])
                mapa_filtro = {"🏠 Casa": "PF", "🏢 Negócio": "PJ"}
                if filtro_label in mapa_filtro:
                    df_historico = df_historico[df_historico['tipo'] == mapa_filtro[filtro_label]]

                colunas_exibir = ['id', 'data', 'descricao', 'valor', 'categoria', 'tipo', 'conta_id']
                colunas_disponiveis = [col for col in colunas_exibir if col in df_historico.columns]
                st.dataframe(df_historico[colunas_disponiveis], use_container_width=True, hide_index=True)

                st.download_button(
                    label="📥 Baixar planilha pro contador (.csv)",
                    data=df_historico[colunas_disponiveis].to_csv(index=False).encode('utf-8'),
                    file_name="guido_extrato.csv",
                    mime="text/csv",
                    type="primary"
                )

                st.divider()
                st.markdown("#### ✏️ Corrigir lançamento")
                with st.expander("Errou algo? Clica aqui pra corrigir."):
                    opcoes_edicao = {f"#{x['id']} · {x.get('data','')} · {x['descricao']} (R$ {x['valor']})": x for x in historico}
                    if opcoes_edicao:
                        escolha_edicao = st.selectbox("Qual lançamento?", list(opcoes_edicao.keys()))
                        tx_edit = opcoes_edicao[escolha_edicao]
                        with st.form("form_edicao"):
                            ce1, ce2, ce3 = st.columns([1,2,1])
                            m_data = ce1.text_input("Data", value=tx_edit.get('data', ''))
                            m_desc = ce2.text_input("Descrição", value=tx_edit['descricao'])
                            m_val  = ce3.number_input("Valor", value=float(tx_edit['valor']), step=0.01)
                            ce4, ce5, ce6 = st.columns(3)
                            lista_cats_ed = LISTA_BASE.copy()
                            if tx_edit['categoria'] not in lista_cats_ed:
                                lista_cats_ed.insert(0, tx_edit['categoria'])
                            m_cat  = ce4.selectbox("Categoria", lista_cats_ed, index=lista_cats_ed.index(tx_edit['categoria']))
                            if m_cat == "Outra...":
                                m_cat = ce4.text_input("Qual nova categoria?")
                            mapa_ed = {"🏠 Casa": "PF", "🏢 Negócio": "PJ"}
                            m_tipo_label = ce5.selectbox("É de onde?", ["🏠 Casa", "🏢 Negócio"], index=0 if tx_edit['tipo']=="PF" else 1)
                            m_tipo = mapa_ed[m_tipo_label]
                            idx_c_ed = nomes_contas.index(id_para_nome[tx_edit['conta_id']]) if tx_edit['conta_id'] in id_para_nome else 0
                            m_conta = ce6.selectbox("Conta", nomes_contas, index=idx_c_ed)
                            if st.form_submit_button("Salvar correção ✅", type="primary"):
                                payload_edicao = {"data": m_data, "descricao": m_desc, "valor": m_val, "categoria": m_cat, "tipo": m_tipo, "conta_id": opcoes_contas[m_conta]}
                                res_put = requests.put(f"{API_URL}/transacoes/{tx_edit['id']}", json=payload_edicao)
                                if res_put.status_code == 200:
                                    st.success("Corrigido.")
                                    st.rerun()
                                else:
                                    st.error("Deu ruim na edição.")
            else:
                st.info("Ainda não tem nada confirmado. Manda um gasto pro Guido!")
        else:
            st.warning("Não consegui carregar o histórico.")
    except:
        st.error("A API tá offline?")

# ==========================================
# ABA 3: MINHAS CONTAS
# ==========================================
with aba_contas:
    st.markdown("### 🏦 Suas contas")
    st.caption("Onde você guarda o dinheiro — da casa e do negócio.")

    with st.container(border=True):
        st.markdown("#### ➕ Adicionar conta")
        with st.form("form_nova_conta", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            nome_conta  = c1.text_input("Apelido", placeholder="Ex: Nubank do negócio")
            banco_conta = c2.text_input("Banco", placeholder="Ex: Nubank")
            mapa_fin = {"🏢 Negócio": "PJ", "🏠 Casa": "PF"}
            tipo_conta_label = c3.selectbox("Pra quê?", ["🏢 Negócio", "🏠 Casa"])
            tipo_conta = mapa_fin[tipo_conta_label]
            if st.form_submit_button("Salvar conta", type="primary"):
                if nome_conta and banco_conta:
                    payload = {"nome": nome_conta, "banco": banco_conta, "tipo": tipo_conta, "usuario_id": USUARIO_ID}
                    res = requests.post(f"{API_URL}/contas/", json=payload)
                    if res.status_code == 200:
                        st.success("Pronto, cadastrada.")
                        st.rerun()
                else:
                    st.warning("Preenche apelido e banco.")

    st.divider()
    st.markdown("#### Contas que o Guido conhece")
    if contas:
        df_contas = pd.DataFrame(contas)[['id', 'nome', 'banco', 'tipo']].copy()
        df_contas['tipo'] = df_contas['tipo'].map({'PJ': '🏢 Negócio', 'PF': '🏠 Casa'}).fillna(df_contas['tipo'])
        df_contas = df_contas.rename(columns={'nome': 'apelido', 'tipo': 'pra quê'})
        st.dataframe(df_contas, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma conta cadastrada ainda.")

    st.divider()
    st.markdown("#### ⚠️ Zona de perigo")
    st.warning("Cuidado: essas ações não dá pra desfazer.")
    c_perigo1, c_perigo2 = st.columns(2)

    if c_perigo1.button("🗑️ Apagar todas as transações", type="secondary"):
        if requests.delete(f"{API_URL}/sistema/resetar-transacoes", params={"usuario_id": USUARIO_ID}).status_code == 200:
            st.success("Tudo zerado.")
            st.rerun()

    if c_perigo2.button("🚨 Formatar banco (apaga TUDO)", type="primary"):
        if requests.delete(f"{API_URL}/sistema/recriar-banco").status_code == 200:
            st.success("Banco formatado. Entra de novo.")
            del st.session_state.usuario_id
            del st.session_state.usuario_nome
            st.rerun()

# ==========================================
# ABA 4: CATEGORIAS E METAS
# ==========================================
with aba_categorias:
    st.markdown("### 📂 Categorias & metas")
    st.caption("Organiza seus gastos e define quanto dá pra gastar em cada coisa.")

    col_esq, col_dir = st.columns(2)

    with col_esq:
        st.markdown("#### ➕ Nova categoria")
        with st.form("form_nova_categoria", clear_on_submit=True):
            nome_cat_new = st.text_input("Nome", placeholder="Ex: Saúde e bem-estar")
            mapa_cat = {"Serve pros dois": "Ambos", "🏢 Só negócio": "PJ", "🏠 Só casa": "PF"}
            label_cat_new = st.selectbox("Vale pra quê?", list(mapa_cat.keys()))
            tipo_cat_new = mapa_cat[label_cat_new]
            if st.form_submit_button("Salvar categoria", type="primary"):
                if nome_cat_new.strip():
                    res_cat = requests.post(f"{API_URL}/categorias", json={"nome": nome_cat_new.strip(), "tipo": tipo_cat_new})
                    if res_cat.status_code == 200:
                        st.success(f"Categoria '{nome_cat_new}' criada.")
                        st.rerun()
                    elif res_cat.status_code == 400:
                        st.warning("Essa categoria já existe.")
                    else:
                        st.error("Deu ruim ao salvar.")
                else:
                    st.warning("Digita um nome pra categoria.")

        st.divider()
        st.markdown("#### 🗂️ Categorias personalizadas")
        try:
            req_cats_page = requests.get(f"{API_URL}/categorias")
            if req_cats_page.status_code == 200:
                cats_lista = req_cats_page.json()
                if cats_lista:
                    mapa_cat_inv = {"Ambos": "🏠🏢", "PJ": "🏢", "PF": "🏠"}
                    for cat in cats_lista:
                        c_nome, c_tipo, c_del = st.columns([3, 1, 1])
                        c_nome.write(f"**{cat['nome']}**")
                        c_tipo.caption(mapa_cat_inv.get(cat['tipo'], cat['tipo']))
                        if c_del.button("🗑️", key=f"del_cat_{cat['id']}", help="Remover"):
                            if requests.delete(f"{API_URL}/categorias/{cat['id']}").status_code == 200:
                                st.rerun()
                else:
                    st.info("Ainda não tem categoria personalizada.")
        except:
            st.error("Erro ao carregar categorias.")

        with st.expander("Ver categorias padrão"):
            for cat in sorted(LISTA_BASE):
                st.write(f"• {cat}")

    with col_dir:
        st.markdown("#### 🎯 Teto de gastos")
        st.caption("Até onde dá pra ir em cada categoria antes do Guido te avisar.")

        # Monta lista com padrão + personalizadas
        lista_categorias = LISTA_BASE.copy()
        try:
            req_cats = requests.get(f"{API_URL}/categorias")
            if req_cats.status_code == 200:
                for c in req_cats.json():
                    if c['nome'] not in lista_categorias:
                        lista_categorias.append(c['nome'])
            lista_categorias = sorted(lista_categorias)
        except:
            pass

        with st.form("form_meta"):
            cat_escolhida = st.selectbox("Categoria", lista_categorias)
            teto_valor = st.number_input("Valor máximo (R$)", min_value=0.0, step=50.0)
            if st.form_submit_button("Salvar teto 🎯", type="primary", use_container_width=True):
                if teto_valor > 0:
                    payload_meta = {"categoria": cat_escolhida, "valor_teto": float(teto_valor), "usuario_id": USUARIO_ID}
                    res_meta = requests.post(f"{API_URL}/limites/", json=payload_meta)
                    if res_meta.status_code == 200:
                        st.success(f"Teto de R$ {teto_valor:,.2f} em {cat_escolhida}.")
                        st.rerun()
                    else:
                        st.error("Deu ruim ao salvar.")
                else:
                    st.warning("Põe um valor maior que zero.")

        st.divider()
        st.markdown("#### 📊 Seus tetos")
        try:
            req_limites = requests.get(f"{API_URL}/limites/", params={"usuario_id": USUARIO_ID})
            if req_limites.status_code == 200:
                limites_lista = req_limites.json()
                if limites_lista:
                    for limite in limites_lista:
                        l_nome, l_valor = st.columns([3, 2])
                        l_nome.write(f"**{limite['categoria']}**")
                        l_valor.write(f"R$ {limite['valor_teto']:,.2f}")
                else:
                    st.info("Ainda não tem teto definido.")
        except:
            st.caption("Aguardando a API...")
