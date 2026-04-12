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
        /* ── SIDEBAR COLAPSÁVEL ──
           Esconde o texto 'keyboard_double_arrow_left' do botão nativo
           mas mantém o mecanismo interno do Streamlit funcional.
           Não usamos display:none — isso mata o click(). Usamos
           dimensão zero + overflow hidden pra esconder visualmente. */
        [data-testid="stSidebarCollapseButton"] {
            width: 0 !important;
            height: 0 !important;
            overflow: hidden !important;
            padding: 0 !important;
            margin: 0 !important;
            position: absolute !important;
        }
        [data-testid="stSidebarCollapsedControl"] {
            width: 0 !important;
            height: 0 !important;
            overflow: hidden !important;
            padding: 0 !important;
            margin: 0 !important;
            position: absolute !important;
        }
        [data-testid="stSidebar"] {
            z-index: 999998 !important;
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
            font-size: 1.1rem !important;
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

# Botões customizados de abrir/fechar sidebar — injetados via components.html()
# porque st.markdown(unsafe_allow_html=True) REMOVE tags <script>.
# Os botões nativos do Streamlit estão escondidos via CSS porque renderizam
# "keyboard_double_arrow_left" como texto em vez de ícone.
import streamlit.components.v1 as components
components.html("""
<script>
(function() {
    var doc = window.parent.document;
    var STYLE_BASE = 'position:fixed;top:14px;z-index:1000000;width:36px;height:36px;border-radius:10px;background:#1D9E75;color:#fff;border:none;cursor:pointer;font-size:16px;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(0,0,0,0.3);transition:all 0.15s;font-family:system-ui,sans-serif;';

    function fecharSidebar() {
        var sidebar = doc.querySelector('[data-testid="stSidebar"]');
        if (!sidebar) return;
        sidebar.setAttribute('aria-expanded', 'false');
        sidebar.style.transition = 'transform 0.3s ease';
        sidebar.style.transform = 'translateX(-100%)';
    }

    function abrirSidebar() {
        // Limpa o estado "collapsed" do localStorage do Streamlit.
        // O Streamlit 1.56+ guarda em "stSidebarCollapsed-{appId}" e
        // sobrescreve qualquer mudança DOM no próximo re-render se o
        // localStorage ainda disser "collapsed".
        var keys = Object.keys(window.parent.localStorage);
        for (var i = 0; i < keys.length; i++) {
            if (keys[i].indexOf('stSidebarCollapsed') === 0) {
                window.parent.localStorage.removeItem(keys[i]);
            }
        }
        // Força re-render do Streamlit via rerun
        var sidebar = doc.querySelector('[data-testid="stSidebar"]');
        if (sidebar) {
            sidebar.setAttribute('aria-expanded', 'true');
            sidebar.style.transform = 'none';
            sidebar.style.visibility = 'visible';
            sidebar.style.marginLeft = '0';
        }
        // Dispara um resize pra forçar o Streamlit a recalcular layout
        window.parent.dispatchEvent(new Event('resize'));
    }

    function criarBotoes() {
        // Botão FECHAR — dentro da sidebar, canto superior direito
        if (!doc.getElementById('guido-close-btn')) {
            var close = doc.createElement('button');
            close.id = 'guido-close-btn';
            close.title = 'Fechar menu';
            close.innerHTML = '&#10005;';  // ✕
            close.style.cssText = STYLE_BASE + 'display:none;right:12px;left:auto;';
            close.onmouseover = function(){ close.style.background='#085041'; };
            close.onmouseout = function(){ close.style.background='#1D9E75'; };
            close.onclick = fecharSidebar;
            // Insere no topo da sidebar pra ficar "dentro" visualmente
            var sidebar = doc.querySelector('[data-testid="stSidebar"]');
            if (sidebar) {
                close.style.position = 'absolute';
                close.style.top = '12px';
                close.style.right = '12px';
                close.style.left = 'auto';
                sidebar.style.position = 'relative';
                sidebar.insertBefore(close, sidebar.firstChild);
            } else {
                doc.body.appendChild(close);
            }
        }

        // Botão ABRIR — fixo na tela, logo à direita de onde a sidebar estaria
        if (!doc.getElementById('guido-open-btn')) {
            var open = doc.createElement('button');
            open.id = 'guido-open-btn';
            open.title = 'Abrir menu lateral';
            open.innerHTML = '&#9776;';  // ☰ hamburger
            open.style.cssText = STYLE_BASE + 'display:none;left:14px;';
            open.onmouseover = function(){ open.style.background='#085041'; };
            open.onmouseout = function(){ open.style.background='#1D9E75'; };
            open.onclick = abrirSidebar;
            doc.body.appendChild(open);
        }
    }

    function atualizar() {
        criarBotoes();
        var sidebar = doc.querySelector('[data-testid="stSidebar"]');
        var btnClose = doc.getElementById('guido-close-btn');
        var btnOpen = doc.getElementById('guido-open-btn');
        if (!btnClose || !btnOpen) return;

        var expandida = sidebar && sidebar.getAttribute('aria-expanded') !== 'false';
        btnClose.style.display = expandida ? 'flex' : 'none';
        btnOpen.style.display = expandida ? 'none' : 'flex';
    }

    setInterval(atualizar, 400);
})();
</script>
""", height=0)

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

# Logout: se o flag existe, limpa tudo antes de qualquer outra coisa.
# Esse mecanismo existe porque cookie_manager.delete() é instável —
# frequentemente não executa o JS de deleção se chamado junto com
# st.rerun(). Então o botão "Sair" seta o flag e faz rerun; na volta,
# esse bloco limpa a sessão e os cookies com segurança.
if st.session_state.get("_guido_logout"):
    st.session_state.pop("_guido_logout", None)
    st.session_state.pop("usuario_id", None)
    st.session_state.pop("usuario_nome", None)
    try:
        cookie_manager.delete("usuario_id",   key="logout_del_id")
        cookie_manager.delete("usuario_nome", key="logout_del_nome")
    except Exception:
        pass  # se falhar, tanto faz — a sessão já foi limpa

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
                tel_reg = st.text_input(
                    "WhatsApp (com DDD)",
                    placeholder="Ex: 11999999999",
                    key="tel_reg",
                    help="Pra usar o Guido pelo WhatsApp. Só números, sem +55.",
                )
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
                        # Formata telefone pro padrão internacional (55 + DDD + número)
                        telefone_fmt = None
                        if tel_reg and tel_reg.strip():
                            apenas_digitos = ''.join(c for c in tel_reg if c.isdigit())
                            if not apenas_digitos.startswith("55"):
                                apenas_digitos = "55" + apenas_digitos
                            telefone_fmt = apenas_digitos
                        try:
                            payload_reg = {"nome": nome_reg, "email": email_reg, "senha": senha_reg}
                            if telefone_fmt:
                                payload_reg["telefone"] = telefone_fmt
                            res = requests.post(f"{API_URL}/auth/registrar", json=payload_reg)
                            if res.status_code == 200:
                                u = res.json()
                                st.session_state.usuario_id   = u["id"]
                                st.session_state.usuario_nome = u["nome"]
                                cookie_manager.set("usuario_id",   str(u["id"]), key="set_id_reg")
                                cookie_manager.set("usuario_nome", u["nome"],    key="set_nome_reg")
                                st.rerun()
                            elif res.status_code == 400:
                                try:
                                    detail = res.json().get("detail", "")
                                except Exception:
                                    detail = ""
                                msg_erro = detail if detail else "E-mail ou telefone já cadastrado."
                                st.session_state.auth_msg = {"tipo": "erro", "texto": msg_erro}
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
    st.session_state["_guido_logout"] = True
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
        def _rotulo_conta(c):
            icone = "💳" if c.get("modalidade") == "cartao_credito" else "🏦"
            return f"{icone} {c['nome']} ({c['tipo']})"
        opcoes_contas = {_rotulo_conta(c): c['id'] for c in contas}
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
aba_dashboard, aba_graficos, aba_extrato, aba_contas, aba_categorias, aba_perfil = st.tabs(["🌱 Painel", "📊 Dashboards", "🧾 Histórico", "🏦 Contas", "📂 Categorias & Metas", "👤 Minha Conta"])

# ==========================================
# ABA 1: PAINEL
# ==========================================
with aba_dashboard:
    st.markdown("### 📝 O que saiu hoje?")

    # Form com Enter pra submeter + clear_on_submit pra limpar o campo
    with st.form("form_lancamento_ia", clear_on_submit=True):
        texto_input = st.text_input("Conta pro Guido", placeholder="Ex: gastei 45 no Uber pra reunião do negócio", label_visibility="collapsed")
        enviou = st.form_submit_button("Manda pro Guido", use_container_width=True, type="primary")

    if enviou:
        if texto_input:
            with st.spinner("O Guido tá ouvindo..."):
                res = requests.post(f"{API_URL}/transacoes/ia", params={"texto": texto_input, "usuario_id": USUARIO_ID})
                if res.status_code == 200:
                    st.success("Anotado. Dá uma olhada na revisão aí embaixo.")
                    st.rerun()
                else:
                    st.error("Deu ruim aqui. Tenta de novo?")
        else:
            st.warning("Escreve algo primeiro.")
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
                    df_extrato = pd.read_csv(arquivo, sep=None, engine='python', header=None, dtype=str)

                    # Helper: converte qualquer valor pra string segura (resolve
                    # floats, NaN, None que estouram o operador 'in')
                    def _safe_str(v):
                        if v is None or (isinstance(v, float) and pd.isna(v)):
                            return ""
                        return str(v).lower().strip()

                    # Detecta a linha de cabeçalho
                    header_idx = 0
                    for i in range(min(15, len(df_extrato))):
                        linha_texto = [_safe_str(v) for v in df_extrato.iloc[i]]
                        if any('valor' in c for c in linha_texto) and any('descri' in c or 'hist' in c for c in linha_texto):
                            header_idx = i
                            break

                    # Usa a linha detectada como cabeçalho
                    df_extrato.columns = [_safe_str(v) for v in df_extrato.iloc[header_idx]]
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

    # ==================================================
    # BARRAS DE PROGRESSO — METAS VS GASTOS REAIS
    # ==================================================
    # Teto é mensal. Se o filtro é "Ano todo", compara com o mês atual.
    # Se é um mês específico, usa aquele mês.
    try:
        req_lim_dash = requests.get(f"{API_URL}/limites/", params={"usuario_id": USUARIO_ID})
        if req_lim_dash.status_code == 200:
            limites_dash = req_lim_dash.json()
            if limites_dash:
                # Determina qual mês usar pra comparação
                if filtro_mes:
                    params_meta = {"usuario_id": USUARIO_ID, "ano": filtro_ano, "mes": filtro_mes}
                    label_periodo_meta = f"{filtro_mes_label}/{filtro_ano}"
                else:
                    params_meta = {"usuario_id": USUARIO_ID, "ano": filtro_ano, "mes": _mes_atual}
                    label_periodo_meta = f"{_MESES[_mes_atual]}/{filtro_ano}"

                req_hist_metas = requests.get(f"{API_URL}/transacoes/historico", params=params_meta)
                if req_hist_metas.status_code == 200:
                    hist_metas = req_hist_metas.json()
                    # Agrupa gastos (só saídas, exclui transferência interna) por categoria
                    gastos_por_cat = {}
                    for tx in hist_metas:
                        if tx.get("confirmado") and tx.get("valor", 0) < 0:
                            cat = tx.get("categoria", "")
                            if "transferência interna" not in cat.lower():
                                gastos_por_cat[cat] = gastos_por_cat.get(cat, 0) + abs(tx["valor"])

                    # Monta as barras de progresso
                    st.divider()
                    st.markdown(f"### 🎯 Suas metas · {label_periodo_meta}")

                    for lim in sorted(limites_dash, key=lambda x: x.get("categoria", "")):
                        cat_nome = lim["categoria"]
                        teto = lim["valor_teto"]
                        gasto = gastos_por_cat.get(cat_nome, 0)
                        pct = gasto / teto if teto > 0 else 0

                        # Cor conforme consumo
                        if pct > 1.0:
                            cor = "#EF4444"  # vermelho — estourou
                            emoji = "🔴"
                        elif pct >= 0.7:
                            cor = "#F5A623"  # âmbar — atenção
                            emoji = "🟡"
                        else:
                            cor = "#1D9E75"  # verde — tranquilo
                            emoji = "🟢"

                        col_nome_m, col_barra_m = st.columns([1.2, 2])
                        col_nome_m.markdown(f"{emoji} **{cat_nome}**")
                        col_nome_m.caption(f"R$ {gasto:,.2f} de R$ {teto:,.2f}")

                        # Progress bar (Streamlit clampeia em 0-1, então pra >100% mando 1.0)
                        col_barra_m.progress(min(pct, 1.0))
                        if pct > 1.0:
                            col_barra_m.caption(f"⚠️ Cuidado, você já atingiu {pct:.0%} do seu teto!")
    except Exception:
        pass  # sem limites ou sem conexão — não mostra a seção

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
# ABA: DASHBOARDS
# ==========================================
with aba_graficos:
    st.markdown("### 📊 Dashboards")

    # --- Controles globais ---
    ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 2])
    with ctrl1:
        dash_ano = st.selectbox("Ano", _anos_opcoes, index=0, key="dash_ano")
    with ctrl2:
        dash_mes_label = st.selectbox("Mês", _MESES, index=_mes_atual, key="dash_mes")
        dash_mes = None if dash_mes_label == "Ano todo" else _MESES.index(dash_mes_label)
    with ctrl3:
        dash_visao = st.radio("Visão", ["Todos", "🏢 Negócio", "🏠 Casa"], horizontal=True, key="dash_visao")

    try:
        # Busca transações do ano inteiro (pra gráfico de linha) e do período selecionado
        _params_ano = {"usuario_id": USUARIO_ID, "ano": dash_ano}
        _params_periodo_dash = {"usuario_id": USUARIO_ID, "ano": dash_ano}
        if dash_mes:
            _params_periodo_dash["mes"] = dash_mes

        req_dash_ano = requests.get(f"{API_URL}/transacoes/historico", params=_params_ano)
        req_dash = requests.get(f"{API_URL}/transacoes/historico", params=_params_periodo_dash)

        # Período anterior (mês anterior ou ano anterior)
        if dash_mes and dash_mes > 1:
            _params_ant = {"usuario_id": USUARIO_ID, "ano": dash_ano, "mes": dash_mes - 1}
        elif dash_mes and dash_mes == 1:
            _params_ant = {"usuario_id": USUARIO_ID, "ano": dash_ano - 1, "mes": 12}
        else:
            _params_ant = {"usuario_id": USUARIO_ID, "ano": dash_ano - 1}
        req_dash_ant = requests.get(f"{API_URL}/transacoes/historico", params=_params_ant)

        # Limites/tetos
        req_lim_dash2 = requests.get(f"{API_URL}/limites/", params={"usuario_id": USUARIO_ID})

        if req_dash.status_code == 200 and req_dash_ano.status_code == 200:
            import numpy as np

            hist_dash = req_dash.json()
            hist_ano = req_dash_ano.json()
            hist_ant = req_dash_ant.json() if req_dash_ant.status_code == 200 else []
            tetos_dash = {l["categoria"]: l["valor_teto"] for l in (req_lim_dash2.json() if req_lim_dash2.status_code == 200 else [])}

            df = pd.DataFrame(hist_dash) if hist_dash else pd.DataFrame()
            df_ano = pd.DataFrame(hist_ano) if hist_ano else pd.DataFrame()
            df_ant = pd.DataFrame(hist_ant) if hist_ant else pd.DataFrame()

            # Filtra transferências internas
            for _d in [df, df_ano, df_ant]:
                if not _d.empty and 'categoria' in _d.columns:
                    _d.drop(_d[_d['categoria'].str.contains('Transferência Interna', case=False, na=False)].index, inplace=True)

            # Aplica filtro de visão (Casa/Negócio)
            if dash_visao == "🏢 Negócio" and not df.empty:
                df = df[df['tipo'] == 'PJ']
                df_ano = df_ano[df_ano['tipo'] == 'PJ']
            elif dash_visao == "🏠 Casa" and not df.empty:
                df = df[df['tipo'] == 'PF']
                df_ano = df_ano[df_ano['tipo'] == 'PF']

            if not df.empty:
                receitas = df[df['valor'] > 0]['valor'].sum()
                despesas = abs(df[df['valor'] < 0]['valor'].sum())
                saldo = receitas - despesas

                # Período anterior
                receitas_ant = df_ant[df_ant['valor'] > 0]['valor'].sum() if not df_ant.empty and 'valor' in df_ant.columns else 0
                despesas_ant = abs(df_ant[df_ant['valor'] < 0]['valor'].sum()) if not df_ant.empty and 'valor' in df_ant.columns else 0

                # Faturamento MEI (receitas PJ do ano, independente do filtro de mês)
                faturamento_mei = df_ano[(df_ano['valor'] > 0) & (df_ano['tipo'] == 'PJ')]['valor'].sum() if not df_ano.empty else 0
                limite_mei = 81000
                pct_mei = faturamento_mei / limite_mei * 100

                # Maior categoria de despesa
                gastos_cat = df[df['valor'] < 0].groupby('categoria')['valor'].apply(lambda x: abs(x.sum()))
                maior_cat = gastos_cat.idxmax() if not gastos_cat.empty else "—"
                maior_cat_val = gastos_cat.max() if not gastos_cat.empty else 0

                # % Negócio vs Casa
                desp_pj = abs(df[(df['valor'] < 0) & (df['tipo'] == 'PJ')]['valor'].sum())
                desp_pf = abs(df[(df['valor'] < 0) & (df['tipo'] == 'PF')]['valor'].sum())
                total_desp = desp_pj + desp_pf
                pct_neg = (desp_pj / total_desp * 100) if total_desp > 0 else 0

                # ── KPIs (6 cards) ──────────────────────────────
                st.divider()
                k1, k2, k3, k4, k5, k6 = st.columns(6)
                delta_saldo = saldo - (receitas_ant - despesas_ant) if receitas_ant > 0 else None
                k1.metric("Saldo líquido", f"R$ {saldo:,.0f}", delta=f"R$ {delta_saldo:,.0f}" if delta_saldo else None)
                delta_rec = f"{(receitas - receitas_ant) / receitas_ant * 100:+.0f}%" if receitas_ant > 0 else None
                k2.metric("Receitas", f"R$ {receitas:,.0f}", delta=delta_rec)
                delta_desp = f"{(despesas - despesas_ant) / despesas_ant * 100:+.0f}%" if despesas_ant > 0 else None
                k3.metric("Despesas", f"R$ {despesas:,.0f}", delta=delta_desp, delta_color="inverse")
                k4.metric("Maior gasto", f"{maior_cat[:18]}", delta=f"R$ {maior_cat_val:,.0f}")
                k5.metric("Negócio vs Casa", f"{pct_neg:.0f}% / {100-pct_neg:.0f}%")
                cor_mei = "normal" if pct_mei < 60 else "off" if pct_mei < 85 else "inverse"
                k6.metric("Limite MEI", f"{pct_mei:.0f}%", delta=f"R$ {max(0, limite_mei - faturamento_mei):,.0f} restante")

                st.divider()

                # ── GRÁFICO 1: Linha do tempo mensal ─────────────
                if not df_ano.empty:
                    df_ano['_data'] = pd.to_datetime(df_ano['data'], errors='coerce')
                    df_ano['_mes'] = df_ano['_data'].dt.month

                    meses_label = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
                    rec_mensal = df_ano[df_ano['valor'] > 0].groupby('_mes')['valor'].sum()
                    desp_mensal = df_ano[df_ano['valor'] < 0].groupby('_mes')['valor'].apply(lambda x: abs(x.sum()))

                    fig_linha = go.Figure()
                    fig_linha.add_trace(go.Scatter(
                        x=meses_label, y=[rec_mensal.get(m, 0) for m in range(1, 13)],
                        name='Receitas', mode='lines+markers',
                        line=dict(color='#1D9E75', width=3),
                        marker=dict(size=8, color='#1D9E75'),
                        fill='tonexty', fillcolor='rgba(29,158,117,0.08)',
                        hovertemplate='<b>%{x}</b><br>Receitas: R$ %{y:,.2f}<extra></extra>',
                    ))
                    fig_linha.add_trace(go.Scatter(
                        x=meses_label, y=[desp_mensal.get(m, 0) for m in range(1, 13)],
                        name='Despesas', mode='lines+markers',
                        line=dict(color='#E24B4A', width=3),
                        marker=dict(size=8, color='#E24B4A'),
                        hovertemplate='<b>%{x}</b><br>Despesas: R$ %{y:,.2f}<extra></extra>',
                    ))
                    if not desp_mensal.empty:
                        media_desp = desp_mensal.mean()
                        fig_linha.add_hline(y=media_desp, line_dash='dash', line_color='#475569',
                                           annotation_text=f'Média: R$ {media_desp:,.0f}', annotation_position='right')

                    fig_linha.update_layout(
                        title=dict(text='Evolução mensal — Receitas vs Despesas', font=dict(color='#F1F5F9')),
                        paper_bgcolor='#111827', plot_bgcolor='#1E293B',
                        font=dict(color='#94A3B8'),
                        legend=dict(bgcolor='#1E293B', bordercolor='#334155'),
                        hovermode='x unified',
                        xaxis=dict(gridcolor='#1E293B', showgrid=True),
                        yaxis=dict(gridcolor='#1E293B', showgrid=True, tickprefix='R$ '),
                        height=380, margin=dict(l=60, r=20, t=50, b=40),
                    )
                    st.plotly_chart(fig_linha, use_container_width=True, config={"displayModeBar": False})

                # ── GRÁFICO 2+3: Barras por categoria + Donut ────
                col_barras, col_donut = st.columns([2, 1])

                with col_barras:
                    if not gastos_cat.empty:
                        df_cat = df[df['valor'] < 0].copy()
                        df_cat['valor_abs'] = df_cat['valor'].abs()
                        df_cat['origem'] = df_cat['tipo'].map({'PJ': '🏢 Negócio', 'PF': '🏠 Casa'})
                        df_agrup = df_cat.groupby(['categoria', 'origem'])['valor_abs'].sum().reset_index()
                        df_agrup = df_agrup.sort_values('valor_abs', ascending=True)

                        fig_barras = go.Figure()
                        for origem, cor in [('🏢 Negócio', '#1D9E75'), ('🏠 Casa', '#9FE1CB')]:
                            sub = df_agrup[df_agrup['origem'] == origem]
                            if not sub.empty:
                                fig_barras.add_trace(go.Bar(
                                    y=sub['categoria'], x=sub['valor_abs'],
                                    name=origem, orientation='h', marker_color=cor,
                                    hovertemplate='%{y}<br>R$ %{x:,.2f}<extra>' + origem + '</extra>',
                                ))
                        # Linhas de teto
                        for cat, teto in tetos_dash.items():
                            if cat in gastos_cat.index:
                                fig_barras.add_vline(x=teto, line_dash='dot', line_color='#F5A623',
                                                     annotation_text=f'Teto: R$ {teto:,.0f}',
                                                     annotation_font_color='#F5A623')
                        fig_barras.update_layout(
                            barmode='stack',
                            title=dict(text='Despesas por categoria', font=dict(color='#F1F5F9')),
                            paper_bgcolor='#111827', plot_bgcolor='#1E293B',
                            font=dict(color='#94A3B8'),
                            xaxis=dict(tickprefix='R$ ', gridcolor='#1E293B'),
                            yaxis=dict(gridcolor='#1E293B'),
                            legend=dict(bgcolor='#1E293B'),
                            height=max(300, gastos_cat.nunique() * 40 + 80),
                            margin=dict(l=140, r=60, t=50, b=40),
                        )
                        st.plotly_chart(fig_barras, use_container_width=True, config={"displayModeBar": False})

                with col_donut:
                    if total_desp > 0:
                        fig_donut = go.Figure(go.Pie(
                            labels=['🏢 Negócio', '🏠 Casa'],
                            values=[desp_pj, desp_pf],
                            hole=0.65,
                            marker=dict(colors=['#1D9E75', '#9FE1CB'], line=dict(color='#111827', width=3)),
                            textinfo='label+percent',
                            hovertemplate='%{label}<br>R$ %{value:,.2f}<br>%{percent}<extra></extra>',
                        ))
                        fig_donut.update_layout(
                            annotations=[dict(text=f'R$ {total_desp:,.0f}', x=0.5, y=0.5,
                                              font_size=16, font=dict(color='#F1F5F9'), showarrow=False)],
                            paper_bgcolor='#111827', plot_bgcolor='#111827',
                            font=dict(color='#94A3B8'), showlegend=True,
                            legend=dict(bgcolor='#1E293B'),
                            height=300, margin=dict(l=20, r=20, t=40, b=20),
                        )
                        st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

                # ── GRÁFICO 4: Progresso de tetos ────────────────
                if tetos_dash:
                    st.divider()
                    st.markdown("#### 🎯 Teto de gastos por categoria")
                    for cat, teto in sorted(tetos_dash.items()):
                        gasto = gastos_cat.get(cat, 0)
                        pct = (gasto / teto * 100) if teto > 0 else 0
                        cor = "#1D9E75" if pct < 70 else "#F5A623" if pct < 90 else "#E24B4A"
                        alerta = "🔔 " if pct >= 80 else ""
                        tc1, tc2 = st.columns([3, 1])
                        with tc1:
                            st.markdown(f"**{alerta}{cat}**")
                            st.markdown(
                                f'<div style="background:#1E293B;border-radius:6px;height:12px;overflow:hidden;">'
                                f'<div style="background:{cor};width:{min(pct, 100)}%;height:100%;border-radius:6px;'
                                f'transition:width 0.3s;"></div></div>',
                                unsafe_allow_html=True,
                            )
                        with tc2:
                            st.markdown(
                                f"<div style='text-align:right;color:{cor};font-size:13px;'>"
                                f"R$ {gasto:,.0f} / R$ {teto:,.0f}<br>"
                                f"<span style='font-size:11px;'>{pct:.0f}%</span></div>",
                                unsafe_allow_html=True,
                            )
                        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

                # ── GRÁFICO 5+6: Heatmap + Gauge MEI ────────────
                col_heat, col_gauge = st.columns([2, 1])

                with col_heat:
                    if dash_mes and not df.empty:
                        import calendar as _cal
                        df['_data'] = pd.to_datetime(df['data'], errors='coerce')
                        gastos_dia = df[df['valor'] < 0].groupby(df['_data'].dt.day)['valor'].apply(lambda x: abs(x.sum()))
                        _, dias_no_mes = _cal.monthrange(dash_ano, dash_mes)
                        primeiro_dia = _cal.weekday(dash_ano, dash_mes, 1)
                        matriz = np.zeros(35)
                        for dia in range(1, dias_no_mes + 1):
                            idx = primeiro_dia + dia - 1
                            if idx < 35:
                                matriz[idx] = gastos_dia.get(dia, 0)
                        matriz = matriz.reshape(5, 7)
                        dias_semana = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
                        semanas = ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4', 'Sem 5']
                        fig_heat = go.Figure(go.Heatmap(
                            z=matriz, x=dias_semana, y=semanas,
                            colorscale=[[0, '#1E293B'], [0.3, '#085041'], [0.7, '#1D9E75'], [1, '#9FE1CB']],
                            hovertemplate='%{x} · %{y}<br>R$ %{z:,.2f}<extra></extra>',
                            showscale=True,
                        ))
                        fig_heat.update_layout(
                            title=dict(text='Intensidade de gastos por dia', font=dict(color='#F1F5F9')),
                            paper_bgcolor='#111827', plot_bgcolor='#1E293B',
                            font=dict(color='#94A3B8'),
                            height=280, margin=dict(l=60, r=20, t=50, b=40),
                        )
                        st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})
                    else:
                        st.caption("Selecione um mês específico pra ver o heatmap de gastos por dia.")

                with col_gauge:
                    fig_gauge = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=pct_mei,
                        number=dict(suffix="%", font=dict(color="#F1F5F9", size=32)),
                        gauge=dict(
                            axis=dict(range=[0, 100], tickcolor="#94A3B8"),
                            bar=dict(color="#1D9E75" if pct_mei < 60 else "#F5A623" if pct_mei < 85 else "#E24B4A"),
                            bgcolor="#1E293B", borderwidth=0,
                            steps=[
                                dict(range=[0, 60], color="#0F2A1F"),
                                dict(range=[60, 85], color="#1A1400"),
                                dict(range=[85, 100], color="#1A0505"),
                            ],
                            threshold=dict(line=dict(color="#E24B4A", width=4), thickness=0.8, value=85),
                        ),
                        title=dict(text="Limite MEI utilizado", font=dict(color="#94A3B8", size=14)),
                    ))
                    faltam_mei = max(0, limite_mei - faturamento_mei)
                    fig_gauge.update_layout(
                        paper_bgcolor='#111827', font=dict(color='#94A3B8'),
                        height=280, margin=dict(l=20, r=20, t=60, b=20),
                        annotations=[dict(
                            text=f"R$ {faturamento_mei:,.0f} de R$ {limite_mei:,.0f}<br>"
                                 f"<span style='color:#94A3B8'>Faltam R$ {faltam_mei:,.0f}</span>",
                            x=0.5, y=-0.1, showarrow=False,
                            font=dict(color='#F1F5F9', size=12), align='center',
                        )],
                    )
                    st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})

                # ── GRÁFICO 7: Comparativo mensal ────────────────
                if not df_ant.empty and not df.empty:
                    st.divider()
                    cats_atual = df[df['valor'] < 0].groupby('categoria')['valor'].apply(lambda x: abs(x.sum()))
                    cats_anterior = df_ant[df_ant['valor'] < 0].groupby('categoria')['valor'].apply(lambda x: abs(x.sum()))
                    todas_cats = sorted(set(cats_atual.index) | set(cats_anterior.index))

                    fig_comp = go.Figure()
                    fig_comp.add_trace(go.Bar(
                        name='Período anterior', x=todas_cats,
                        y=[cats_anterior.get(c, 0) for c in todas_cats],
                        marker_color='#334155',
                        hovertemplate='%{x}<br>Anterior: R$ %{y:,.2f}<extra></extra>',
                    ))
                    fig_comp.add_trace(go.Bar(
                        name='Período atual', x=todas_cats,
                        y=[cats_atual.get(c, 0) for c in todas_cats],
                        marker_color='#1D9E75',
                        hovertemplate='%{x}<br>Atual: R$ %{y:,.2f}<extra></extra>',
                    ))
                    fig_comp.update_layout(
                        barmode='group',
                        title=dict(text='Comparativo de despesas — período atual vs anterior', font=dict(color='#F1F5F9')),
                        paper_bgcolor='#111827', plot_bgcolor='#1E293B',
                        font=dict(color='#94A3B8'),
                        xaxis=dict(gridcolor='#1E293B', tickangle=-30),
                        yaxis=dict(tickprefix='R$ ', gridcolor='#1E293B'),
                        legend=dict(bgcolor='#1E293B'),
                        height=360, margin=dict(l=60, r=20, t=50, b=80),
                    )
                    st.plotly_chart(fig_comp, use_container_width=True, config={"displayModeBar": False})

                # ── INSIGHTS ─────────────────────────────────────
                st.divider()
                from insights_engine import gerar_insights, Insight
                lista_insights = gerar_insights(df, df_ant, tetos_dash, faturamento_mei, limite_mei)

                st.markdown("#### 🧠 Análises e Insights")
                st.caption("Gerado automaticamente com base nos seus dados do período selecionado.")

                if not lista_insights:
                    st.success("✅ Tudo em ordem! Nenhuma observação importante para este período.")
                else:
                    CORES_INSIGHT = {
                        "critico": ("#FCEBEB", "#E24B4A", "#791F1F"),
                        "atencao": ("#FAEEDA", "#F5A623", "#633806"),
                        "info": ("#E6F1FB", "#378ADD", "#0C447C"),
                        "ok": ("#E1F5EE", "#1D9E75", "#085041"),
                    }
                    cols_ins = st.columns(2)
                    for idx, ins in enumerate(lista_insights):
                        bg, border, text_cor = CORES_INSIGHT.get(ins.tipo, ("#1E293B", "#94A3B8", "#F1F5F9"))
                        with cols_ins[idx % 2]:
                            st.markdown(
                                f'<div style="background:{bg};border-left:4px solid {border};'
                                f'border-radius:0 10px 10px 0;padding:14px 16px;margin-bottom:12px;">'
                                f'<div style="font-size:15px;font-weight:500;color:{text_cor};margin-bottom:6px;">'
                                f'{ins.emoji} {ins.titulo}</div>'
                                f'<div style="font-size:13px;color:{text_cor};opacity:0.85;line-height:1.6;">'
                                f'{ins.mensagem}</div></div>',
                                unsafe_allow_html=True,
                            )

            else:
                st.info("Ainda não tem dados pra mostrar nos dashboards. Manda um gasto pro Guido!")
    except Exception as e:
        st.error(f"Erro ao carregar dashboards: {e}")

# ==========================================
# ABA: EXTRATO
# ==========================================
with aba_extrato:
    @st.fragment
    def _tab_extrato():
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

                    # ── Tabela editável com excluir/editar inline ──
                    colunas_exibir = ['id', 'data', 'descricao', 'valor', 'categoria', 'tipo', 'conta_id']
                    colunas_disponiveis = [col for col in colunas_exibir if col in df_historico.columns]

                    csv_data = df_historico[colunas_disponiveis].to_csv(index=False).encode('utf-8')

                    df_edit = df_historico[colunas_disponiveis].copy()
                    _tipo_display = {"PF": "Casa", "PJ": "Negócio"}
                    _tipo_reverse = {"Casa": "PF", "Negócio": "PJ"}
                    df_edit["tipo"] = df_edit["tipo"].map(_tipo_display).fillna(df_edit["tipo"])
                    df_edit["conta"] = df_edit["conta_id"].map(id_para_nome).fillna("—")
                    df_edit.drop(columns=["conta_id"], inplace=True)
                    df_edit.insert(0, "🗑️", False)

                    _todas_cats = sorted(set(LISTA_BASE) | set(df_edit["categoria"].dropna().unique()))
                    _original = df_edit.copy()

                    edited = st.data_editor(
                        df_edit,
                        use_container_width=True,
                        hide_index=True,
                        disabled=["id"],
                        column_config={
                            "🗑️": st.column_config.CheckboxColumn("🗑️", default=False, width="small"),
                            "id": st.column_config.NumberColumn("ID", width="small"),
                            "data": st.column_config.TextColumn("Data"),
                            "descricao": st.column_config.TextColumn("Descrição", width="medium"),
                            "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                            "categoria": st.column_config.SelectboxColumn("Categoria", options=_todas_cats, width="medium"),
                            "tipo": st.column_config.SelectboxColumn("Tipo", options=["Casa", "Negócio"], width="small"),
                            "conta": st.column_config.SelectboxColumn("Conta", options=nomes_contas if nomes_contas else ["—"], width="medium"),
                        },
                        key="editor_historico",
                    )

                    col_salvar, col_excluir, col_csv = st.columns(3)

                    with col_salvar:
                        if st.button("💾 Salvar alterações", type="primary"):
                            alterados = 0
                            for idx in edited.index:
                                if edited.at[idx, "🗑️"]:
                                    continue
                                mudou = False
                                for col in ["data", "descricao", "valor", "categoria", "tipo", "conta"]:
                                    if str(edited.at[idx, col]) != str(_original.at[idx, col]):
                                        mudou = True
                                        break
                                if mudou:
                                    payload_ed = {
                                        "data": str(edited.at[idx, "data"]),
                                        "descricao": str(edited.at[idx, "descricao"]),
                                        "valor": float(edited.at[idx, "valor"]),
                                        "categoria": str(edited.at[idx, "categoria"]),
                                        "tipo": _tipo_reverse.get(str(edited.at[idx, "tipo"]), "PF"),
                                        "conta_id": opcoes_contas.get(str(edited.at[idx, "conta"]), None),
                                    }
                                    res_ed = requests.put(f"{API_URL}/transacoes/{int(edited.at[idx, 'id'])}", json=payload_ed)
                                    if res_ed.status_code == 200:
                                        alterados += 1
                            if alterados > 0:
                                st.success(f"{alterados} lançamento(s) atualizado(s).")
                                st.rerun()
                            else:
                                st.info("Nenhuma alteração detectada.")

                    with col_excluir:
                        selecionados = edited[edited["🗑️"] == True]
                        if not selecionados.empty:
                            if st.button(f"🗑️ Excluir {len(selecionados)} lançamento(s)"):
                                for _, row in selecionados.iterrows():
                                    requests.delete(f"{API_URL}/transacoes/{int(row['id'])}")
                                st.success(f"{len(selecionados)} lançamento(s) excluído(s).")
                                st.rerun()

                    with col_csv:
                        st.download_button(
                            label="📥 Baixar CSV",
                            data=csv_data,
                            file_name="guido_extrato.csv",
                            mime="text/csv",
                        )
                else:
                    st.info("Ainda não tem nada confirmado. Manda um gasto pro Guido!")
            else:
                st.warning("Não consegui carregar o histórico.")
        except:
            st.error("A API tá offline?")
    _tab_extrato()

# ==========================================
# ABA 3: MINHAS CONTAS
# ==========================================
with aba_contas:
    st.markdown("### 🏦 Suas contas")
    st.caption("Onde você guarda o dinheiro — da casa e do negócio. Inclui cartões de crédito.")

    with st.container(border=True):
        st.markdown("#### ➕ Adicionar conta")

        # Seletor de modalidade FORA do form — precisa ser reativo
        # (o form só renderiza campos de cartão quando o select muda)
        modalidade_label = st.radio(
            "Que tipo de conta?",
            ["🏦 Conta corrente / débito / Pix", "💳 Cartão de crédito"],
            horizontal=True,
            key="nova_conta_modalidade",
        )
        eh_cartao = modalidade_label.startswith("💳")

        with st.form("form_nova_conta", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            nome_conta = c1.text_input(
                "Apelido",
                placeholder="Ex: Nubank Black" if eh_cartao else "Ex: Nubank do negócio",
            )
            banco_conta = c2.text_input("Banco", placeholder="Ex: Nubank")
            mapa_fin = {"🏢 Negócio": "PJ", "🏠 Casa": "PF"}
            tipo_conta_label = c3.selectbox("Pra quê?", ["🏢 Negócio", "🏠 Casa"])
            tipo_conta = mapa_fin[tipo_conta_label]

            # Campos condicionais de cartão
            dia_fech = None
            dia_venc = None
            limite_cartao = None
            if eh_cartao:
                st.caption("Informações do cartão — olha no app do banco, na tela da fatura.")
                cc1, cc2, cc3 = st.columns(3)
                dia_fech = cc1.number_input(
                    "Fecha no dia", min_value=1, max_value=31, value=25, step=1,
                    help="Dia em que o cartão fecha a fatura (fim do ciclo de compras).",
                )
                dia_venc = cc2.number_input(
                    "Vence no dia", min_value=1, max_value=31, value=5, step=1,
                    help="Dia em que a fatura precisa ser paga.",
                )
                limite_cartao = cc3.number_input(
                    "Limite (opcional)", min_value=0.0, step=100.0, value=0.0,
                    help="Só pra referência — não é usado em cálculos ainda.",
                )

            if st.form_submit_button("Salvar conta", type="primary"):
                if not (nome_conta and banco_conta):
                    st.warning("Preenche apelido e banco.")
                else:
                    payload = {
                        "nome": nome_conta,
                        "banco": banco_conta,
                        "tipo": tipo_conta,
                        "usuario_id": USUARIO_ID,
                        "modalidade": "cartao_credito" if eh_cartao else "corrente",
                    }
                    if eh_cartao:
                        payload["dia_fechamento"] = int(dia_fech)
                        payload["dia_vencimento"] = int(dia_venc)
                        if limite_cartao and limite_cartao > 0:
                            payload["limite"] = float(limite_cartao)

                    res = requests.post(f"{API_URL}/contas/", json=payload)
                    if res.status_code == 200:
                        st.success("Pronto, cadastrada.")
                        st.rerun()
                    else:
                        try:
                            detail = res.json().get("detail", "erro desconhecido")
                        except Exception:
                            detail = f"erro {res.status_code}"
                        st.error(f"Não consegui salvar: {detail}")

    st.divider()
    st.markdown("#### Contas que o Guido conhece")
    if contas:
        df_contas = pd.DataFrame(contas).copy()
        # Campos novos podem não existir em contas antigas — preenche defaults
        for col, default in [("modalidade", "corrente"), ("dia_fechamento", None), ("dia_vencimento", None)]:
            if col not in df_contas.columns:
                df_contas[col] = default

        def _render_modalidade(row):
            if row.get("modalidade") == "cartao_credito":
                f, v = row.get("dia_fechamento"), row.get("dia_vencimento")
                if f and v:
                    return f"💳 Cartão (fecha {int(f)}, vence {int(v)})"
                return "💳 Cartão"
            return "🏦 Corrente"

        df_contas["como"] = df_contas.apply(_render_modalidade, axis=1)
        df_contas["tipo"] = df_contas["tipo"].map({"PJ": "🏢 Negócio", "PF": "🏠 Casa"}).fillna(df_contas["tipo"])
        df_contas = df_contas.rename(columns={"nome": "apelido", "tipo": "pra quê"})
        st.dataframe(
            df_contas[["id", "apelido", "banco", "pra quê", "como"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Nenhuma conta cadastrada ainda.")

    # ==================================================
    # SEÇÃO DE FATURAS DE CARTÃO (fase 2)
    # ==================================================
    cartoes = [c for c in contas if c.get("modalidade") == "cartao_credito"]
    contas_correntes = [c for c in contas if c.get("modalidade") != "cartao_credito"]

    if cartoes:
        st.divider()
        st.markdown("#### 💳 Suas faturas")
        st.caption("Todo cartão tem sua fatura. Quando paga, o Guido lança como transferência (não duplica no gráfico).")

        for cartao in cartoes:
            try:
                req_fatura = requests.get(
                    f"{API_URL}/cartoes/{cartao['id']}/faturas-abertas",
                    params={"usuario_id": USUARIO_ID},
                )
                if req_fatura.status_code != 200:
                    st.caption(f"💳 {cartao['nome']} — não foi possível carregar a fatura.")
                    continue

                info_fatura = req_fatura.json()
                faturas = info_fatura.get("faturas", [])
                proxima = info_fatura.get("proxima")

                tipo_label = "🏢 Negócio" if cartao.get("tipo") == "PJ" else "🏠 Casa"

                with st.container(border=True):
                    col_info, col_botao = st.columns([3, 1])

                    with col_info:
                        st.markdown(f"**💳 {cartao['nome']}** · {tipo_label}")
                        if proxima:
                            st.markdown(
                                f"Fatura aberta: **R$ {proxima['valor']:.2f}** · vence {proxima['vencimento']}"
                            )
                            if len(faturas) > 1:
                                outras = sum(f["valor"] for f in faturas[1:])
                                st.caption(f"+ {len(faturas) - 1} fatura(s) futura(s) somando R$ {outras:.2f}")
                        else:
                            st.caption("✨ Nenhuma fatura em aberto.")

                    with col_botao:
                        if proxima and contas_correntes:
                            if st.button("Pagar fatura", key=f"abrir_pgto_{cartao['id']}", use_container_width=True):
                                # Toggle: se já está aberto, fecha. Se não, abre.
                                key_aberto = f"pgto_aberto_{cartao['id']}"
                                st.session_state[key_aberto] = not st.session_state.get(key_aberto, False)
                                st.rerun()
                        elif proxima and not contas_correntes:
                            st.caption("Cadastre uma conta corrente pra pagar")

                    # Form inline de pagamento (toggleável)
                    if proxima and contas_correntes and st.session_state.get(f"pgto_aberto_{cartao['id']}", False):
                        st.divider()
                        st.markdown("##### Registrar pagamento")
                        with st.form(f"form_pgto_{cartao['id']}"):
                            pc1, pc2, pc3 = st.columns(3)
                            valor_pgto = pc1.number_input(
                                "Valor (R$)",
                                min_value=0.01,
                                value=float(proxima["valor"]),
                                step=10.0,
                                key=f"pgto_valor_{cartao['id']}",
                                help="Pode editar se for pagar diferente do total (pagamento parcial, estorno, etc.)",
                            )
                            # Monta lista de contas correntes do mesmo tipo (PF paga PF, PJ paga PJ)
                            # Fallback: se não tiver corrente do mesmo tipo, aceita qualquer uma
                            correntes_mesmo_tipo = [c for c in contas_correntes if c.get("tipo") == cartao.get("tipo")]
                            correntes_escolha = correntes_mesmo_tipo if correntes_mesmo_tipo else contas_correntes
                            mapa_origem = {f"🏦 {c['nome']} ({c['banco']})": c["id"] for c in correntes_escolha}
                            origem_label = pc2.selectbox(
                                "Sai de onde?",
                                list(mapa_origem.keys()),
                                key=f"pgto_origem_{cartao['id']}",
                            )
                            data_pgto = pc3.text_input(
                                "Data",
                                value=_dt.now().date().isoformat(),
                                key=f"pgto_data_{cartao['id']}",
                                help="Quando o dinheiro sai da sua conta (ISO: AAAA-MM-DD)",
                            )

                            col_cancel, col_confirmar = st.columns(2)
                            cancelou = col_cancel.form_submit_button("Cancelar", use_container_width=True)
                            confirmou = col_confirmar.form_submit_button(
                                "Confirmar pagamento ✅",
                                type="primary",
                                use_container_width=True,
                            )

                            if cancelou:
                                st.session_state[f"pgto_aberto_{cartao['id']}"] = False
                                st.rerun()

                            if confirmou:
                                payload_pgto = {
                                    "cartao_id": cartao["id"],
                                    "conta_origem_id": mapa_origem[origem_label],
                                    "valor": float(valor_pgto),
                                    "data": data_pgto,
                                    "usuario_id": USUARIO_ID,
                                }
                                res_pgto = requests.post(
                                    f"{API_URL}/transacoes/pagar-fatura",
                                    json=payload_pgto,
                                )
                                if res_pgto.status_code == 200:
                                    st.success(f"✅ Fatura paga. R$ {valor_pgto:.2f} saíram da sua conta corrente.")
                                    st.session_state[f"pgto_aberto_{cartao['id']}"] = False
                                    st.rerun()
                                else:
                                    try:
                                        detail = res_pgto.json().get("detail", "erro desconhecido")
                                    except Exception:
                                        detail = f"erro {res_pgto.status_code}"
                                    st.error(f"Não consegui registrar o pagamento: {detail}")

            except Exception as exc:
                st.caption(f"💳 {cartao['nome']} — erro: {exc}")

    # Zona de perigo — só admin vê (evita que beta testers formatem o banco)
    if USUARIO_ID == 1:
        st.divider()
        st.markdown("#### ⚠️ Zona de perigo")
        st.warning("Cuidado: essas ações não dá pra desfazer.")
        c_perigo1, c_perigo2 = st.columns(2)

        if c_perigo1.button("🗑️ Apagar minhas transações", type="secondary"):
            st.session_state["_confirmar_apagar_tx"] = True

        if c_perigo2.button("🚨 Formatar banco (apaga TUDO)", type="primary"):
            st.session_state["_confirmar_formatar"] = True

        # Confirmação: apagar transações
        if st.session_state.get("_confirmar_apagar_tx"):
            st.markdown("##### 🔐 Confirme com sua senha pra apagar todas as transações")
            with st.form("form_confirmar_apagar_tx"):
                senha_conf_tx = st.text_input("Senha", type="password", placeholder="Digite sua senha")
                col_ok, col_cancel = st.columns(2)
                confirmar = col_ok.form_submit_button("Confirmar exclusão", type="primary")
                cancelar = col_cancel.form_submit_button("Cancelar")
                if confirmar:
                    res_login = requests.post(
                        f"{API_URL}/auth/login",
                        json={"email": st.session_state.get("usuario_email", ""), "senha": senha_conf_tx},
                    )
                    # Fallback: tenta buscar o email se não tiver no session_state
                    if res_login.status_code == 401:
                        try:
                            perfil_r = requests.get(f"{API_URL}/auth/minha-conta", params={"usuario_id": USUARIO_ID})
                            if perfil_r.status_code == 200:
                                email_real = perfil_r.json().get("email", "")
                                res_login = requests.post(
                                    f"{API_URL}/auth/login",
                                    json={"email": email_real, "senha": senha_conf_tx},
                                )
                        except Exception:
                            pass
                    if res_login.status_code == 200:
                        requests.delete(f"{API_URL}/sistema/resetar-transacoes", params={"usuario_id": USUARIO_ID})
                        st.session_state.pop("_confirmar_apagar_tx", None)
                        st.success("Transações apagadas.")
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
                if cancelar:
                    st.session_state.pop("_confirmar_apagar_tx", None)
                    st.rerun()

        # Confirmação: formatar banco
        if st.session_state.get("_confirmar_formatar"):
            st.markdown("##### 🔐 Confirme com sua senha pra FORMATAR O BANCO INTEIRO")
            with st.form("form_confirmar_formatar"):
                senha_conf_fmt = st.text_input("Senha", type="password", placeholder="Digite sua senha")
                col_ok2, col_cancel2 = st.columns(2)
                confirmar2 = col_ok2.form_submit_button("Confirmar formatação", type="primary")
                cancelar2 = col_cancel2.form_submit_button("Cancelar")
                if confirmar2:
                    res_login2 = requests.post(
                        f"{API_URL}/auth/login",
                        json={"email": st.session_state.get("usuario_email", ""), "senha": senha_conf_fmt},
                    )
                    if res_login2.status_code == 401:
                        try:
                            perfil_r2 = requests.get(f"{API_URL}/auth/minha-conta", params={"usuario_id": USUARIO_ID})
                            if perfil_r2.status_code == 200:
                                email_real2 = perfil_r2.json().get("email", "")
                                res_login2 = requests.post(
                                    f"{API_URL}/auth/login",
                                    json={"email": email_real2, "senha": senha_conf_fmt},
                                )
                        except Exception:
                            pass
                    if res_login2.status_code == 200:
                        requests.delete(f"{API_URL}/sistema/recriar-banco", params={"admin_id": USUARIO_ID})
                        st.session_state.pop("_confirmar_formatar", None)
                        st.success("Banco formatado. Entra de novo.")
                        del st.session_state.usuario_id
                        del st.session_state.usuario_nome
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
                if cancelar2:
                    st.session_state.pop("_confirmar_formatar", None)
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

        # Busca gastos do período pra mostrar ao lado de cada teto
        _gastos_cat_metas = {}
        try:
            _params_metas_tab = {"usuario_id": USUARIO_ID, "ano": filtro_ano, "mes": filtro_mes or _mes_atual}
            _req_h_metas = requests.get(f"{API_URL}/transacoes/historico", params=_params_metas_tab)
            if _req_h_metas.status_code == 200:
                for _tx in _req_h_metas.json():
                    if _tx.get("confirmado") and _tx.get("valor", 0) < 0:
                        _c = _tx.get("categoria", "")
                        if "transferência interna" not in _c.lower():
                            _gastos_cat_metas[_c] = _gastos_cat_metas.get(_c, 0) + abs(_tx["valor"])
        except Exception:
            pass

        try:
            req_limites = requests.get(f"{API_URL}/limites/", params={"usuario_id": USUARIO_ID})
            if req_limites.status_code == 200:
                limites_lista = req_limites.json()
                if limites_lista:
                    for limite in limites_lista:
                        l_nome, l_valor, l_edit, l_del = st.columns([3, 2, 1, 1])
                        _gasto_cat = _gastos_cat_metas.get(limite['categoria'], 0)
                        _pct = _gasto_cat / limite['valor_teto'] if limite['valor_teto'] > 0 else 0
                        _emoji = "🔴" if _pct > 1 else ("🟡" if _pct >= 0.7 else "🟢")
                        l_nome.write(f"{_emoji} **{limite['categoria']}**")
                        l_valor.write(f"R$ {_gasto_cat:,.2f} / R$ {limite['valor_teto']:,.2f}")
                        if l_edit.button("✏️", key=f"edit_lim_{limite['id']}", help="Alterar valor"):
                            st.session_state[f"_editando_limite_{limite['id']}"] = True
                        if l_del.button("🗑️", key=f"del_lim_{limite['id']}", help="Excluir teto"):
                            res_del = requests.delete(f"{API_URL}/limites/{limite['id']}")
                            if res_del.status_code == 200:
                                st.rerun()

                        # Form inline de edição (aparece ao clicar no ✏️)
                        if st.session_state.get(f"_editando_limite_{limite['id']}", False):
                            with st.form(f"form_edit_lim_{limite['id']}"):
                                novo_valor = st.number_input(
                                    f"Novo teto pra {limite['categoria']}",
                                    min_value=0.0,
                                    value=float(limite['valor_teto']),
                                    step=50.0,
                                )
                                col_salvar, col_cancelar = st.columns(2)
                                salvar = col_salvar.form_submit_button("Salvar", type="primary")
                                cancelar = col_cancelar.form_submit_button("Cancelar")
                                if salvar and novo_valor > 0:
                                    payload_edit = {
                                        "categoria": limite['categoria'],
                                        "valor_teto": float(novo_valor),
                                        "usuario_id": USUARIO_ID,
                                    }
                                    requests.post(f"{API_URL}/limites/", json=payload_edit)
                                    st.session_state.pop(f"_editando_limite_{limite['id']}", None)
                                    st.rerun()
                                if cancelar:
                                    st.session_state.pop(f"_editando_limite_{limite['id']}", None)
                                    st.rerun()
                else:
                    st.info("Ainda não tem teto definido.")
        except:
            st.caption("Aguardando a API...")

# ==========================================
# ABA 5: MINHA CONTA
# ==========================================
with aba_perfil:
    st.markdown("### 👤 Minha Conta")

    try:
        req_perfil = requests.get(f"{API_URL}/auth/minha-conta", params={"usuario_id": USUARIO_ID})
        if req_perfil.status_code == 200:
            perfil = req_perfil.json()

            # --- Status da assinatura ---
            with st.container(border=True):
                st.markdown("#### 📋 Sua assinatura")
                status_ass = perfil.get("assinatura_status", "sem_assinatura")
                data_ate = perfil.get("assinatura_ativa_ate")

                if status_ass == "ativa":
                    st.success(f"✅ Assinatura ativa até **{data_ate}**")
                elif status_ass == "inativa":
                    st.warning(f"⚠️ Assinatura expirou em {data_ate}. Renove pra continuar usando.")
                    st.markdown(
                        '[Renovar assinatura](https://www.asaas.com/c/vmfmrar60lf95ayr)',
                        unsafe_allow_html=True,
                    )
                else:
                    st.info("Você ainda não tem assinatura ativa.")
                    st.markdown(
                        '[Assinar o Guido — R$ 19/mês](https://www.asaas.com/c/vmfmrar60lf95ayr)',
                        unsafe_allow_html=True,
                    )

                if status_ass == "ativa" and perfil.get("assinatura_ativa_ate"):
                    st.divider()
                    if st.button("Cancelar assinatura", type="secondary"):
                        st.session_state["_confirmar_cancelamento"] = True

                    if st.session_state.get("_confirmar_cancelamento"):
                        st.warning(
                            "Tem certeza? Seu acesso continua ativo até o fim do período pago "
                            f"(**{data_ate}**). Depois disso, você perde acesso ao painel e ao WhatsApp."
                        )
                        col_sim, col_nao = st.columns(2)
                        if col_sim.button("Sim, cancelar", type="primary"):
                            res_cancel = requests.post(
                                f"{API_URL}/auth/cancelar-assinatura",
                                params={"usuario_id": USUARIO_ID},
                            )
                            if res_cancel.status_code == 200:
                                msg_cancel = res_cancel.json().get("mensagem", "Cancelado")
                                st.success(msg_cancel)
                                st.session_state.pop("_confirmar_cancelamento", None)
                                st.rerun()
                            else:
                                st.error("Erro ao cancelar. Tenta de novo ou entre em contato.")
                        if col_nao.button("Não, manter"):
                            st.session_state.pop("_confirmar_cancelamento", None)
                            st.rerun()

            st.divider()

            # --- Dados pessoais ---
            with st.container(border=True):
                st.markdown("#### ✏️ Seus dados")
                with st.form("form_perfil"):
                    pf_nome = st.text_input("Nome", value=perfil.get("nome", ""))
                    pf_email = st.text_input("Email", value=perfil.get("email", ""))
                    pf_tel_raw = perfil.get("telefone", "") or ""
                    # Remove prefixo 55 pra exibir mais limpo
                    pf_tel_display = pf_tel_raw[2:] if pf_tel_raw.startswith("55") else pf_tel_raw
                    pf_tel = st.text_input(
                        "WhatsApp (com DDD)",
                        value=pf_tel_display,
                        help="Só números, sem +55",
                    )

                    if st.form_submit_button("Salvar alterações", type="primary"):
                        payload_perfil = {}
                        if pf_nome != perfil.get("nome"):
                            payload_perfil["nome"] = pf_nome
                        if pf_email != perfil.get("email"):
                            payload_perfil["email"] = pf_email
                        if pf_tel != pf_tel_display:
                            payload_perfil["telefone"] = pf_tel

                        if payload_perfil:
                            res_perfil = requests.put(
                                f"{API_URL}/auth/perfil",
                                params={"usuario_id": USUARIO_ID},
                                json=payload_perfil,
                            )
                            if res_perfil.status_code == 200:
                                st.success("Dados atualizados.")
                                # Atualiza o nome no cookie/session se mudou
                                if "nome" in payload_perfil:
                                    st.session_state.usuario_nome = payload_perfil["nome"]
                                    cookie_manager.set("usuario_nome", payload_perfil["nome"], key="set_nome_perfil")
                                st.rerun()
                            else:
                                try:
                                    detail = res_perfil.json().get("detail", "")
                                except Exception:
                                    detail = ""
                                st.error(detail or "Erro ao salvar.")
                        else:
                            st.info("Nenhuma alteração detectada.")

            # --- Trocar senha ---
            with st.container(border=True):
                st.markdown("#### 🔑 Trocar senha")
                with st.form("form_trocar_senha"):
                    senha_atual = st.text_input("Senha atual", type="password")
                    senha_nova = st.text_input("Nova senha", type="password", placeholder="Mínimo 6 caracteres")
                    senha_conf = st.text_input("Confirmar nova senha", type="password")

                    if st.form_submit_button("Trocar senha", type="primary"):
                        if not senha_atual or not senha_nova:
                            st.warning("Preenche os dois campos.")
                        elif senha_nova != senha_conf:
                            st.error("As senhas não coincidem.")
                        elif len(senha_nova) < 6:
                            st.warning("A nova senha precisa ter pelo menos 6 caracteres.")
                        else:
                            res_senha = requests.put(
                                f"{API_URL}/auth/perfil",
                                params={"usuario_id": USUARIO_ID},
                                json={"senha_atual": senha_atual, "senha_nova": senha_nova},
                            )
                            if res_senha.status_code == 200:
                                st.success("Senha trocada.")
                            else:
                                try:
                                    detail = res_senha.json().get("detail", "")
                                except Exception:
                                    detail = ""
                                st.error(detail or "Erro ao trocar senha.")
    except Exception:
        st.error("Erro ao carregar dados da conta.")

    # ==========================================
    # ADMIN — só aparece pra user ID 1
    # ==========================================
    if USUARIO_ID == 1:
        st.divider()
        st.markdown("### 🔧 Admin")

        # --- Criar usuário free ---
        with st.container(border=True):
            st.markdown("#### ➕ Criar usuário gratuito (beta tester)")
            with st.form("form_admin_criar_user", clear_on_submit=True):
                adm_nome = st.text_input("Nome completo")
                adm_email = st.text_input("Email")
                adm_tel = st.text_input("WhatsApp (com DDD)", help="Recebe a senha por WhatsApp. Só números.")

                if st.form_submit_button("Criar conta free", type="primary"):
                    if adm_nome and adm_email:
                        res_admin = requests.post(
                            f"{API_URL}/admin/criar-usuario-free",
                            params={
                                "nome": adm_nome,
                                "email": adm_email,
                                "telefone": adm_tel,
                                "admin_id": USUARIO_ID,
                            },
                        )
                        if res_admin.status_code == 200:
                            dados_criado = res_admin.json()
                            st.success(
                                f"Conta criada! Email: **{dados_criado['email']}** · "
                                f"Senha: **{dados_criado['senha']}** · "
                                f"WhatsApp: {'enviado' if dados_criado.get('whatsapp_enviado') else 'não enviado'}"
                            )
                        else:
                            try:
                                detail = res_admin.json().get("detail", "")
                            except Exception:
                                detail = ""
                            st.error(detail or "Erro ao criar conta.")
                    else:
                        st.warning("Preenche nome e email.")

        # --- Lista de usuários ---
        with st.container(border=True):
            st.markdown("#### 👥 Usuários cadastrados")
            try:
                req_users = requests.get(
                    f"{API_URL}/admin/usuarios",
                    params={"admin_id": USUARIO_ID},
                )
                if req_users.status_code == 200:
                    users_list = req_users.json()
                    if users_list:
                        for u in users_list:
                            status_label = {
                                "free": "🟢 Free",
                                "ativa": "🟢 Ativa",
                                "inativa": "🔴 Expirada",
                                "sem_assinatura": "⚪ Sem plano",
                            }.get(u["assinatura_status"], u["assinatura_status"])

                            st.markdown(
                                f"**{u['nome']}** · {u['email']} · "
                                f"{u.get('telefone') or 'sem tel'} · "
                                f"{status_label}"
                            )
                    else:
                        st.info("Nenhum usuário cadastrado.")
            except Exception:
                st.caption("Erro ao carregar lista.")
