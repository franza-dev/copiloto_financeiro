import os
import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Copiloto Financeiro IA", page_icon="💰", layout="wide")
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&display=swap');

        /* ── BASE ── */
        html, body, [class*="css"], .stApp {
            font-family: 'Sora', sans-serif !important;
            background-color: #140c1c !important;
            color: #dddddd !important;
        }

        #MainMenu, footer, header { visibility: hidden; }

        /* ── TÍTULO PRINCIPAL ── */
        h1 {
            font-family: 'Sora', sans-serif !important;
            font-weight: 700 !important;
            font-size: 2rem !important;
            background: linear-gradient(90deg, #8750f7, #fd701c);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.25rem !important;
        }

        /* ── TÍTULOS h2, h3, h4 ── */
        h2, h3, h4 {
            font-family: 'Sora', sans-serif !important;
            font-weight: 600 !important;
            color: #dddddd !important;
        }

        /* ── SIDEBAR ── */
        [data-testid="stSidebar"] {
            background-color: #1e1030 !important;
            border-right: 1px solid #2a1454 !important;
        }
        [data-testid="stSidebar"] * {
            font-family: 'Sora', sans-serif !important;
            color: #dddddd !important;
        }
        [data-testid="stSidebarNav"] { display: none; }

        /* ── ABAS ── */
        [data-baseweb="tab-list"] {
            background-color: #1e1030 !important;
            border-radius: 12px !important;
            padding: 4px !important;
            gap: 4px !important;
            border: 1px solid #2a1454 !important;
        }
        [data-baseweb="tab"] {
            font-family: 'Sora', sans-serif !important;
            font-weight: 600 !important;
            color: #9d9d9d !important;
            background-color: transparent !important;
            border-radius: 8px !important;
            padding: 8px 18px !important;
            border: none !important;
            transition: all 0.2s !important;
        }
        [aria-selected="true"][data-baseweb="tab"] {
            background: linear-gradient(135deg, #8750f7, #6230d4) !important;
            color: #ffffff !important;
        }
        [data-baseweb="tab-highlight"] { display: none !important; }
        [data-baseweb="tab-border"] { display: none !important; }

        /* ── BOTÕES ── */
        .stButton > button,
        .stFormSubmitButton > button,
        .stDownloadButton > button {
            font-family: 'Sora', sans-serif !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            border-radius: 9999px !important;
            padding: 0.55em 1.6em !important;
            border: none !important;
            transition: all 0.25s ease !important;
            background: linear-gradient(135deg, #8750f7, #6230d4) !important;
            color: #ffffff !important;
            box-shadow: 6px 6px 18px rgba(135, 80, 247, 0.25) !important;
        }
        .stButton > button:hover,
        .stFormSubmitButton > button:hover,
        .stDownloadButton > button:hover {
            transform: translateY(-2px) scale(1.02) !important;
            box-shadow: 6px 8px 24px rgba(135, 80, 247, 0.4) !important;
        }
        /* Botão "secondary" → laranja */
        .stButton > button[kind="secondary"] {
            background: linear-gradient(135deg, #fd701c, #e05a10) !important;
            box-shadow: 6px 6px 18px rgba(253, 112, 28, 0.25) !important;
        }
        .stButton > button[kind="secondary"]:hover {
            box-shadow: 6px 8px 24px rgba(253, 112, 28, 0.4) !important;
        }

        /* ── INPUTS ── */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div,
        .stTextArea textarea {
            font-family: 'Sora', sans-serif !important;
            background-color: #1e1030 !important;
            border: 1px solid #2a1454 !important;
            border-radius: 10px !important;
            color: #dddddd !important;
            transition: border-color 0.2s !important;
        }
        .stTextInput > div > div > input:focus,
        .stNumberInput > div > div > input:focus,
        .stTextArea textarea:focus {
            border-color: #8750f7 !important;
            box-shadow: 0 0 0 2px rgba(135, 80, 247, 0.2) !important;
        }

        /* ── LABELS DOS INPUTS ── */
        label, .stSelectbox label, .stTextInput label,
        .stNumberInput label, .stRadio label {
            font-family: 'Sora', sans-serif !important;
            font-weight: 600 !important;
            color: #b0a0c8 !important;
            font-size: 0.82rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
        }

        /* ── CARDS / CONTAINERS ── */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #1e1030 !important;
            border: 1px solid #2a1454 !important;
            border-radius: 16px !important;
            box-shadow: 12px 12px 50px rgba(0, 0, 0, 0.4) !important;
            padding: 1rem !important;
        }

        /* ── EXPANDERS ── */
        .streamlit-expanderHeader {
            font-family: 'Sora', sans-serif !important;
            font-weight: 600 !important;
            background-color: #1e1030 !important;
            border: 1px solid #2a1454 !important;
            border-radius: 10px !important;
            color: #dddddd !important;
        }
        .streamlit-expanderContent {
            background-color: #19082e !important;
            border: 1px solid #2a1454 !important;
            border-top: none !important;
            border-radius: 0 0 10px 10px !important;
        }

        /* ── MÉTRICAS ── */
        [data-testid="stMetric"] {
            background-color: #1e1030 !important;
            border: 1px solid #2a1454 !important;
            border-radius: 16px !important;
            padding: 1.1rem 1.4rem !important;
            box-shadow: 6px 6px 18px rgba(0, 0, 0, 0.3) !important;
        }
        [data-testid="stMetricLabel"] {
            font-family: 'Sora', sans-serif !important;
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            color: #b0a0c8 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
        }
        [data-testid="stMetricValue"] {
            font-family: 'Sora', sans-serif !important;
            font-weight: 700 !important;
            font-size: 1.6rem !important;
            color: #ffffff !important;
        }
        [data-testid="stMetricDelta"] {
            color: #8750f7 !important;
        }

        /* ── BARRA DE PROGRESSO ── */
        [data-testid="stProgressBar"] > div {
            background-color: #2a1454 !important;
            border-radius: 9999px !important;
        }
        [data-testid="stProgressBar"] > div > div {
            background: linear-gradient(90deg, #8750f7, #fd701c) !important;
            border-radius: 9999px !important;
        }

        /* ── TABELA / DATA EDITOR ── */
        [data-testid="stDataFrame"], .stDataEditor {
            border: 1px solid #2a1454 !important;
            border-radius: 12px !important;
            overflow: hidden !important;
        }

        /* ── DIVIDER ── */
        hr {
            border-color: #2a1454 !important;
            margin: 1.5rem 0 !important;
        }

        /* ── ALERTAS / MENSAGENS ── */
        [data-testid="stAlert"] {
            border-radius: 12px !important;
            border: none !important;
            font-family: 'Sora', sans-serif !important;
        }

        /* ── RADIO ── */
        [data-testid="stRadio"] > div {
            background-color: #1e1030 !important;
            border-radius: 9999px !important;
            padding: 4px !important;
            border: 1px solid #2a1454 !important;
        }

        /* ── SPINNER ── */
        .stSpinner > div {
            border-top-color: #8750f7 !important;
        }

        /* ── CAPTIONS ── */
        .stCaption, caption {
            color: #7a6a90 !important;
            font-family: 'Sora', sans-serif !important;
        }
    </style>
""", unsafe_allow_html=True)

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.markdown("""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:0.5rem;">
        <div style="
            background: linear-gradient(135deg, #8750f7, #fd701c);
            border-radius: 14px;
            width: 48px; height: 48px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.6rem; box-shadow: 6px 6px 18px rgba(135,80,247,0.35);
        ">💰</div>
        <div>
            <h1 style="margin:0;padding:0;">Copiloto Financeiro IA</h1>
            <p style="margin:0;color:#7a6a90;font-size:0.82rem;font-family:Sora,sans-serif;">
                Gestão inteligente das suas finanças
            </p>
        </div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# TELA DE AUTENTICAÇÃO
# ==========================================
if 'usuario_id' not in st.session_state:
    _, col_center, _ = st.columns([1, 1.2, 1])

    with col_center:
        # Exibe mensagem persistente (erro ou aviso da tentativa anterior)
        if 'auth_msg' in st.session_state:
            msg = st.session_state.pop('auth_msg')
            if msg['tipo'] == 'erro':
                st.error(msg['texto'])
            else:
                st.warning(msg['texto'])

        modo = st.radio("", ["🔑 Entrar", "📝 Criar Conta"], horizontal=True, label_visibility="collapsed")
        st.divider()

        if modo == "🔑 Entrar":
            with st.form("form_login"):
                email_login = st.text_input("E-mail")
                senha_login = st.text_input("Senha", type="password")

                if st.form_submit_button("Entrar", type="primary", use_container_width=True):
                    if email_login and senha_login:
                        try:
                            res = requests.post(
                                f"{API_URL}/auth/login",
                                json={"email": email_login, "senha": senha_login}
                            )
                            if res.status_code == 200:
                                user = res.json()
                                st.session_state.usuario_id   = user['id']
                                st.session_state.usuario_nome = user['nome']
                                st.rerun()
                            elif res.status_code == 401:
                                st.session_state.auth_msg = {'tipo': 'erro', 'texto': 'E-mail ou senha incorretos.'}
                                st.rerun()
                            else:
                                st.session_state.auth_msg = {'tipo': 'erro', 'texto': f'Erro no servidor (status {res.status_code}).'}
                                st.rerun()
                        except Exception as e:
                            st.session_state.auth_msg = {'tipo': 'erro', 'texto': f'API offline. Detalhe: {e}'}
                            st.rerun()
                    else:
                        st.session_state.auth_msg = {'tipo': 'aviso', 'texto': 'Preencha e-mail e senha.'}
                        st.rerun()

        else:
            with st.form("form_registro"):
                nome_reg   = st.text_input("Seu nome")
                email_reg  = st.text_input("E-mail")
                senha_reg  = st.text_input("Senha", type="password")
                senha_conf = st.text_input("Confirmar senha", type="password")

                if st.form_submit_button("Criar Conta", type="primary", use_container_width=True):
                    if nome_reg and email_reg and senha_reg and senha_conf:
                        if senha_reg != senha_conf:
                            st.session_state.auth_msg = {'tipo': 'erro', 'texto': 'As senhas não coincidem.'}
                            st.rerun()
                        else:
                            try:
                                res = requests.post(
                                    f"{API_URL}/auth/registrar",
                                    json={"nome": nome_reg, "email": email_reg, "senha": senha_reg}
                                )
                                if res.status_code == 200:
                                    user = res.json()
                                    st.session_state.usuario_id   = user['id']
                                    st.session_state.usuario_nome = user['nome']
                                    st.rerun()
                                elif res.status_code == 400:
                                    st.session_state.auth_msg = {'tipo': 'erro', 'texto': 'Este e-mail já está cadastrado.'}
                                    st.rerun()
                                else:
                                    st.session_state.auth_msg = {'tipo': 'erro', 'texto': f'Erro no servidor (status {res.status_code}): {res.text}'}
                                    st.rerun()
                            except Exception as e:
                                st.session_state.auth_msg = {'tipo': 'erro', 'texto': f'API offline. Detalhe: {e}'}
                                st.rerun()
                    else:
                        st.session_state.auth_msg = {'tipo': 'aviso', 'texto': 'Preencha todos os campos.'}
                        st.rerun()

    st.stop()

# A partir daqui o usuário está autenticado
USUARIO_ID = st.session_state.usuario_id

# --- SIDEBAR ---
st.sidebar.write(f"👤 Olá, **{st.session_state.usuario_nome}**!")
if st.sidebar.button("🚪 Sair"):
    del st.session_state.usuario_id
    del st.session_state.usuario_nome
    st.rerun()

st.sidebar.divider()
st.sidebar.header("📊 Resumo Consolidado")
st.sidebar.write("Apenas dados confirmados")

resumo = None
try:
    resumo_req = requests.get(f"{API_URL}/dashboard/resumo")
    if resumo_req.status_code == 200:
        resumo = resumo_req.json()

        st.sidebar.subheader("🏢 Empresa (PJ)")
        st.sidebar.write(f"🟢 Receitas: **{resumo['pj']['receitas']}**")
        st.sidebar.write(f"🔴 Despesas: **{resumo['pj']['despesas']}**")
        st.sidebar.metric("Saldo PJ", resumo['pj']['saldo'])

        st.sidebar.divider()

        st.sidebar.subheader("👤 Pessoal (PF)")
        st.sidebar.write(f"🟢 Receitas: **{resumo['pf']['receitas']}**")
        st.sidebar.write(f"🔴 Despesas: **{resumo['pf']['despesas']}**")
        st.sidebar.metric("Saldo PF", resumo['pf']['saldo'])

    if st.sidebar.button("🔄 Atualizar Dashboard"):
        st.rerun()
except:
    st.sidebar.error("Erro: Servidor API Offline ou Banco Desatualizado.")

# --- DADOS GLOBAIS DE CONTAS ---
contas = []
opcoes_contas = {}
nomes_contas = []
id_para_nome = {}
try:
    req_contas = requests.get(f"{API_URL}/contas/{USUARIO_ID}")
    if req_contas.status_code == 200:
        contas = req_contas.json()
        opcoes_contas = {f"{c['nome']} ({c['tipo']})": c['id'] for c in contas}
        nomes_contas  = list(opcoes_contas.keys())
        id_para_nome  = {v: k for k, v in opcoes_contas.items()}
except:
    pass

# --- DADOS GLOBAIS DE CATEGORIAS ---
LISTA_BASE = [
    "Vendas / Receitas", "Prestação de Serviços", "Transferência Interna",
    "Alimentação", "Transporte e Combustível", "Impostos (DAS, etc)",
    "Ferramentas e Software", "Tarifas Bancárias", "Pró-Labore / Salário",
    "Equipamentos", "A Classificar"
]

categorias_db = []
try:
    req_cats = requests.get(f"{API_URL}/categorias")
    if req_cats.status_code == 200:
        categorias_db = [c['nome'] for c in req_cats.json()]
except:
    pass

historico_global = []
categorias_aprendidas = set()
try:
    req_hist_global = requests.get(f"{API_URL}/transacoes/historico")
    if req_hist_global.status_code == 200:
        historico_global      = req_hist_global.json()
        categorias_aprendidas = {x['categoria'] for x in historico_global}
except:
    pass

lista_categorias = sorted(list(set(LISTA_BASE) | set(categorias_db) | categorias_aprendidas))
lista_categorias.append("Outra...")

# --- ESTRUTURA DE ABAS ---
aba_dashboard, aba_extrato, aba_contas, aba_categorias = st.tabs([
    "🏠 Painel de Controle", "🧾 Extrato", "🏦 Minhas Contas", "📂 Categorias"
])

# ==========================================
# ABA 1: PAINEL DE CONTROLE E DASHBOARD
# ==========================================
with aba_dashboard:

    # --- 1. LANÇAMENTO COM IA (TEXTO OU ÁUDIO) ---
    st.write("### 📝 O que aconteceu hoje?")
    
    # Sistema de feedback visual (Raiozinho ou Ampulheta)
    if 'msg_ia' in st.session_state:
        msg = st.session_state.pop('msg_ia')
        if msg['confirmado']:
            st.success(f"⚡ {msg['texto']}")
        else:
            st.warning(f"⏳ {msg['texto']}")

    aba_texto, aba_audio = st.tabs(["✍️ Digitar Frase ou Meta", "🎙️ Gravar Áudio"])
    
    with aba_texto:
        with st.form("form_ia", clear_on_submit=True):
            texto_input = st.text_input("Gasto ou Meta", placeholder="Ex: 'Gastei 50 no Uber' ou 'Limite de 500 para Uber'")
            btn_enviar_ia = st.form_submit_button("Analisar com IA 🚀", use_container_width=True)
            
            if btn_enviar_ia and texto_input:
                with st.spinner("Analisando..."):
                    res = requests.post(f"{API_URL}/transacoes/ia", params={"texto": texto_input, "usuario_id": USUARIO_ID})
                    if res.status_code == 200:
                        resposta = res.json()
                        st.session_state.msg_ia = {
                            'texto': resposta.get('status', 'Processado!'),
                            'confirmado': resposta.get('confirmado_automaticamente', False)
                        }
                        st.rerun()

    with aba_audio:
        st.write("Diga o gasto ou defina uma meta (ex: 'Definir limite de 200 para lazer').")
        audio_gravado = st.audio_input("Grave seu comando:")
        
        if audio_gravado:
            if st.button("🚀 Enviar Áudio para a IA", type="primary", use_container_width=True):
                arquivos = {"file": ("audio_app.wav", audio_gravado, "audio/wav")}
                with st.spinner("Ouvindo..."):
                    res_audio = requests.post(f"{API_URL}/transacoes/ia/audio", files=arquivos)
                    if res_audio.status_code == 200:
                        dados_aud = res_audio.json()
                        st.session_state.msg_ia = {
                            'texto': f"{dados_aud['status']}",
                            'confirmado': dados_aud.get('confirmado_automaticamente', False)
                        }
                        st.rerun()

    st.divider()

    # --- 5. UPLOAD CSV (RESTAURADO) ---
    st.write("### 📂 Importar Extrato (CSV)")
    with st.expander("Faça upload do extrato do seu banco"):
        if not nomes_contas:
            st.warning("Cadastre uma conta na aba 'Minhas Contas' primeiro.")
        else:
            conta_upload    = st.selectbox("Esse extrato é de qual conta?", nomes_contas, key="upload_conta")
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
                    df_extrato = df_extrato.iloc[header_idx + 1:].reset_index(drop=True)

                    col_desc = next((c for c in df_extrato.columns if 'descri' in c or 'historico' in c), None)
                    col_val  = next((c for c in df_extrato.columns if 'valor' in c), None)
                    col_data = next((c for c in df_extrato.columns if 'data' in c or 'vencimento' in c or 'date' in c), None)

                    if col_desc and col_val:
                        transacoes_para_api = []
                        for _, row in df_extrato.iterrows():
                            val_str = str(row[col_val]).strip()
                            try:
                                if val_str and val_str.lower() not in ['nan', 'none']:
                                    valor_float  = float(val_str.replace(',', '.'))
                                    data_extrato = str(row[col_data])[:10] if col_data and pd.notna(row[col_data]) else ""
                                    if valor_float != 0:
                                        transacoes_para_api.append({
                                            "data": data_extrato,
                                            "descricao": str(row[col_desc]),
                                            "valor": valor_float
                                        })
                            except ValueError:
                                pass

                        payload    = {"conta_id": id_conta_upload, "usuario_id": USUARIO_ID, "transacoes": transacoes_para_api}
                        res_lote   = requests.post(f"{API_URL}/transacoes/lote", json=payload)
                        if res_lote.status_code == 200:
                            st.success("Bingo! As transações foram enviadas para a Quarentena.")
                            st.rerun()
                        else:
                            st.error("Erro ao enviar lote para a API.")
                    else:
                        st.error("Ops! Não consegui achar as colunas no seu arquivo.")
                except Exception as e:
                    st.error(f"Erro ao ler o CSV. Detalhe: {e}")

    st.divider()

    # --- 6. QUARENTENA E BOTÃO DE LIMPEZA (RESTAURADOS) ---
    st.write("### ⏳ Quarentena (Revisão)")
    
    # Botão de Salvação de Erros
    if st.button("🚨 Epa, importei errado! Limpar Quarentena", use_container_width=True):
        if requests.delete(f"{API_URL}/sistema/limpar-quarentena").status_code == 200:
            st.success("Quarentena limpa! Agora você pode importar o arquivo correto.")
            st.rerun()

    try:
        res_q = requests.get(f"{API_URL}/transacoes/quarentena").json().get("transacoes", [])
        if res_q:
            for t in res_q:
                with st.expander(f"📦 {t['descricao']} - R$ {t['valor']:.2f}"):
                    c1, c2, c3 = st.columns(3)
                    e_dat = c1.text_input("Data", t.get('data',''), key=f"qdat{t['id']}")
                    e_des = c1.text_input("Descrição", t['descricao'], key=f"qdes{t['id']}")
                    e_val = c2.number_input("Valor", float(t['valor']), key=f"qval{t['id']}")
                    e_cat = c2.text_input("Categoria", t['categoria'], key=f"qcat{t['id']}")
                    idx_c = nomes_contas.index(id_para_nome[t['conta_id']]) if t.get('conta_id') in id_para_nome else 0
                    e_con = c3.selectbox("Conta", nomes_contas, index=idx_c, key=f"qcon{t['id']}")
                    e_tip = c3.selectbox("Tipo", ["PF", "PJ"], index=0 if t['tipo']=="PF" else 1, key=f"qtip{t['id']}")
                    
                    if st.button("Confirmar ✅", key=f"qok{t['id']}", use_container_width=True):
                        pay = {
                            "data": e_dat, "descricao": e_des, "valor": float(e_val), 
                            "categoria": e_cat, "tipo": e_tip, "conta_id": opcoes_contas[e_con]
                        }
                        if requests.patch(f"{API_URL}/transacoes/{t['id']}/confirmar", json=pay).status_code == 200:
                            st.rerun()
        else:
            st.success("Tudo conferido! Não há pendências na Quarentena. ✅")
    except:
        st.caption("🔄 Sincronizando...")

    # --- 2. ACOMPANHAMENTO DE METAS E LIMITES 🎯 ---
    st.write("### 🎯 Metas e Orçamentos")
    try:
        # Busca limites cadastrados
        res_limites = requests.get(f"{API_URL}/limites/").json()
        
        # Calcula gastos REAIS por categoria (apenas transações confirmadas)
        if historico_global:
            df_total = pd.DataFrame(historico_global)
            # Filtra apenas despesas (valor negativo)
            gastos_por_cat = df_total[df_total['valor'] < 0].groupby('categoria')['valor'].sum().abs().to_dict()
        else:
            gastos_por_cat = {}

        if res_limites:
            m_cols = st.columns(2)
            for i, meta in enumerate(res_limites):
                cat = meta['categoria']
                teto = meta['valor_teto']
                real = gastos_por_cat.get(cat, 0)
                
                # Cálculo de porcentagem
                progresso = min(real / teto, 1.0) if teto > 0 else 0
                
                with m_cols[i % 2]:
                    with st.container(border=True):
                        st.write(f"**{cat.upper()}**")
                        # Cor da barra: Verde (OK), Laranja (>80%), Vermelha (>100%)
                        cor = "green" if real <= teto else "red"
                        if real > teto * 0.8 and real <= teto: cor = "orange"
                        
                        st.progress(progresso)
                        st.caption(f"Gasto: R$ {real:,.2f} / Teto: R$ {teto:,.2f}")
                        
                        if real > teto:
                            st.error(f"⚠️ Limite ultrapassado em R$ {real-teto:,.2f}")
        else:
            st.info("Nenhuma meta definida. Tente: 'Definir limite de 500 para Alimentação'")
    except:
        st.caption("Aguardando configuração de metas...")

    st.divider()

    # --- 3. RESUMO FINANCEIRO (MÉTRICAS) ---
    if resumo:
        st.write("### 💰 Saldo Geral")
        def parse_val(s): return float(s.replace("R$ ", "").replace(",", ""))

        saldo_pj = parse_val(resumo['pj']['saldo'])
        saldo_pf = parse_val(resumo['pf']['saldo'])
        total = saldo_pj + saldo_pf

        c1, c2, c3 = st.columns(3)
        c1.metric("Empresa (PJ)", f"R$ {saldo_pj:,.2f}")
        c2.metric("Pessoal (PF)", f"R$ {saldo_pf:,.2f}")
        c3.metric("Saldo Líquido", f"R$ {total:,.2f}", delta=f"{total:,.2f}")

    st.divider()

    # --- 4. DASHBOARD GRÁFICO ---
    st.write("### 📊 Análise de Gastos")
    if historico_global:
        df_dash = pd.DataFrame(historico_global)
        df_desp = df_dash[df_dash['valor'] < 0].copy()
        df_desp['valor_abs'] = df_desp['valor'].abs()

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.write("#### Por Categoria")
            fig_cat = px.pie(df_desp, values='valor_abs', names='categoria', hole=0.4)
            st.plotly_chart(fig_cat, use_container_width=True)

        with col_g2:
            st.write("#### PF vs PJ")
            fig_tipo = px.bar(df_dash, x='tipo', y='valor', color='tipo', barmode='group')
            st.plotly_chart(fig_tipo, use_container_width=True)
    else:
        st.info("Lance alguns gastos para gerar os gráficos.")

    st.divider()

# ==========================================
# ABA 2: EXTRATO E EDIÇÃO MANUAL
# ==========================================
with aba_extrato:
    st.write("### 🧾 Histórico de Lançamentos")

    try:
        req_historico = requests.get(f"{API_URL}/transacoes/historico")
        if req_historico.status_code == 200:
            historico = req_historico.json()

            if historico:
                df_historico = pd.DataFrame(historico)

                col_f1, col_f2 = st.columns(2)
                filtro_tipo = col_f1.selectbox("Filtrar por Tipo:", ["Todos", "PF", "PJ"])
                filtro_cat  = col_f2.selectbox(
                    "Filtrar por Categoria:",
                    ["Todas"] + sorted(df_historico['categoria'].unique().tolist())
                )

                df_view = df_historico.copy()
                if filtro_tipo != "Todos":
                    df_view = df_view[df_view['tipo'] == filtro_tipo]
                if filtro_cat != "Todas":
                    df_view = df_view[df_view['categoria'] == filtro_cat]

                colunas_exibir      = ['id', 'data', 'descricao', 'valor', 'categoria', 'tipo', 'conta_id']
                colunas_disponiveis = [col for col in colunas_exibir if col in df_view.columns]

                # --- A MÁGICA DA TABELA INTERATIVA (COM CAIXINHAS) ---
                df_interativo = df_view[colunas_disponiveis].copy()
                df_interativo.insert(0, "Selecionar 🗑️", False) 

                st.write("Selecione a caixinha na tabela para apagar lançamentos em lote:")
                
                df_editado = st.data_editor(
                    df_interativo,
                    hide_index=True,
                    use_container_width=True,
                    disabled=colunas_disponiveis # Trava as colunas de texto para não editar sem querer
                )

                itens_marcados = df_editado[df_editado["Selecionar 🗑️"] == True]
                
                if not itens_marcados.empty:
                    if st.button(f"🚨 Confirmar exclusão de {len(itens_marcados)} lançamento(s)", type="primary"):
                        for id_apagar in itens_marcados['id']:
                            requests.delete(f"{API_URL}/transacoes/{id_apagar}")
                        st.success("Limpeza concluída! 🌪️")
                        st.rerun()
                # -----------------------------------------------------

                st.write("")
                st.download_button(
                    label="📥 Baixar Planilha para o Contador (.csv)",
                    data=df_view[colunas_disponiveis].to_csv(index=False).encode('utf-8'),
                    file_name="meu_extrato_financeiro.csv",
                    mime="text/csv",
                    type="primary"
                )

                # --- EDIÇÃO MANUAL ---
                st.divider()
                st.write("#### ✏️ Editar Lançamento Confirmado")
                st.caption("Use para corrigir conta, categoria ou qualquer dado já confirmado.")

                opcoes_edicao = {
                    f"ID {x['id']} | {x.get('data','')} | {x['descricao']} (R$ {x['valor']})": x
                    for x in historico
                }

                escolha_edicao = st.selectbox("Selecione o lançamento que deseja editar:", list(opcoes_edicao.keys()))
                tx_edit = opcoes_edicao[escolha_edicao]

                with st.form("form_edicao"):
                    ce1, ce2, ce3 = st.columns([1, 2, 1])
                    m_data = ce1.text_input("Data",      value=tx_edit.get('data', ''))
                    m_desc = ce2.text_input("Descrição", value=tx_edit['descricao'])
                    m_val  = ce3.number_input("Valor",   value=float(tx_edit['valor']), step=0.01)

                    ce4, ce5, ce6 = st.columns(3)

                    lista_cats_ed = lista_categorias.copy()
                    if tx_edit['categoria'] not in lista_cats_ed:
                        lista_cats_ed.insert(0, tx_edit['categoria'])
                    m_cat = ce4.selectbox("Categoria", lista_cats_ed, index=lista_cats_ed.index(tx_edit['categoria']))
                    if m_cat == "Outra...":
                        m_cat = ce4.text_input("Qual nova categoria?")

                    m_tipo  = ce5.selectbox("Tipo", ["PF", "PJ"], index=0 if tx_edit['tipo'] == "PF" else 1)
                    idx_c   = nomes_contas.index(id_para_nome[tx_edit['conta_id']]) if tx_edit.get('conta_id') in id_para_nome else 0
                    m_conta = ce6.selectbox("Conta", nomes_contas, index=idx_c)

                    if st.form_submit_button("Salvar Alterações ✅", type="primary"):
                        payload_edicao = {
                            "data": m_data, "descricao": m_desc, "valor": m_val,
                            "categoria": m_cat, "tipo": m_tipo,
                            "conta_id": opcoes_contas[m_conta]
                        }
                        res_put = requests.put(f"{API_URL}/transacoes/{tx_edit['id']}", json=payload_edicao)
                        if res_put.status_code == 200:
                            st.success("Lançamento corrigido com sucesso!")
                            st.rerun()
                        else:
                            st.error("Erro ao editar o lançamento.")
                            
                # --- BOTÃO DE EXCLUSÃO INDIVIDUAL ---
                st.write("") 
                if st.button("🗑️ Excluir este Lançamento Definitivamente", use_container_width=True):
                    res_del = requests.delete(f"{API_URL}/transacoes/{tx_edit['id']}")
                    if res_del.status_code == 200:
                        st.success("Lançamento apagado para sempre! 🌪️")
                        st.rerun()
                    else:
                        st.error("Erro ao tentar apagar.")

            else:
                st.info("Seu extrato está vazio. Confirme alguns gastos na quarentena!")
        else:
            st.warning("Não foi possível carregar o histórico. Você precisa formatar o banco?")
    except:
        st.error("Erro ao carregar o extrato. A API está rodando?")

# ==========================================
# ABA 3: MINHAS CONTAS E CARTEIRAS
# ==========================================
with aba_contas:
    st.write("### 🏦 Gerenciamento de Contas e Carteiras")
    st.write("Cadastre suas contas bancárias para vincular aos lançamentos.")

    with st.container(border=True):
        st.write("#### ➕ Adicionar Nova Conta")
        with st.form("form_nova_conta", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            nome_conta  = c1.text_input("Nome (Ex: Nubank PJ)")
            banco_conta = c2.text_input("Banco (Ex: Nubank)")
            tipo_conta  = c3.selectbox("Finalidade", ["PJ", "PF"])

            if st.form_submit_button("Salvar Conta", type="primary"):
                if nome_conta and banco_conta:
                    payload = {"nome": nome_conta, "banco": banco_conta, "tipo": tipo_conta, "usuario_id": USUARIO_ID}
                    if requests.post(f"{API_URL}/contas/", json=payload).status_code == 200:
                        st.success("Conta cadastrada com sucesso!")
                        st.rerun()
                else:
                    st.warning("Preencha o nome e o banco.")

    st.divider()
    st.write("#### Suas Contas Atuais:")
    if contas:
        st.dataframe(pd.DataFrame(contas)[['id', 'nome', 'banco', 'tipo']], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma conta cadastrada ou servidor offline.")

    st.divider()
    st.write("#### ⚠️ Zona de Perigo")
    st.warning("Atenção: Ações abaixo são irreversíveis!")

    c_perigo1, c_perigo2 = st.columns(2)

    if c_perigo1.button("🗑️ Zerar Transações (Mantém Contas)", type="secondary"):
        if requests.delete(f"{API_URL}/sistema/resetar-transacoes").status_code == 200:
            st.success("Transações zeradas!")
            st.rerun()

    if c_perigo2.button("🚨 FORMATAR BANCO DE DADOS (APAGA TUDO)", type="primary"):
        if requests.delete(f"{API_URL}/sistema/recriar-banco").status_code == 200:
            st.success("Banco formatado! Recadastre sua conta de usuário.")
            del st.session_state.usuario_id
            del st.session_state.usuario_nome
            st.rerun()


# ==========================================
# ABA 4: GERENCIAMENTO DE CATEGORIAS E METAS
# ==========================================
with aba_categorias:
    st.write("### 📂 Gerenciamento de Categorias e Metas")
    st.caption("Crie categorias personalizadas e defina tetos de gastos para o seu acompanhamento.")

    col_esq, col_dir = st.columns(2)

    with col_esq:
        st.write("#### ➕ Nova Categoria")
        with st.form("form_nova_categoria", clear_on_submit=True):
            nome_cat_new = st.text_input("Nome", placeholder="Ex: Saúde e Bem-Estar")
            tipo_cat_new = st.selectbox("Aplica-se a", ["Ambos", "PJ", "PF"])

            if st.form_submit_button("Salvar Categoria", type="primary"):
                if nome_cat_new.strip():
                    res_cat = requests.post(
                        f"{API_URL}/categorias",
                        json={"nome": nome_cat_new.strip(), "tipo": tipo_cat_new}
                    )
                    if res_cat.status_code == 200:
                        st.success(f"Categoria '{nome_cat_new}' criada!")
                        st.rerun()
                    elif res_cat.status_code == 400:
                        st.warning("Essa categoria já existe.")
                    else:
                        st.error("Erro ao salvar categoria.")
                else:
                    st.warning("Digite um nome para a categoria.")

        st.divider()
        
        st.write("#### 🗂️ Suas Categorias Personalizadas")
        try:
            req_cats_page = requests.get(f"{API_URL}/categorias")
            if req_cats_page.status_code == 200:
                cats_lista = req_cats_page.json()
                if cats_lista:
                    for cat in cats_lista:
                        c_nome, c_tipo, c_del = st.columns([3, 1, 1])
                        c_nome.write(f"**{cat['nome']}**")
                        c_tipo.caption(cat['tipo'])
                        if c_del.button("🗑️", key=f"del_cat_{cat['id']}", help="Remover categoria"):
                            if requests.delete(f"{API_URL}/categorias/{cat['id']}").status_code == 200:
                                st.success("Categoria removida.")
                                st.rerun()
                else:
                    st.info("Nenhuma categoria personalizada cadastrada ainda.")
        except:
            st.error("Erro ao carregar categorias. A API está rodando?")

        st.write("")
        with st.expander("Ver Categorias Padrão do Sistema"):
            for cat in sorted(LISTA_BASE):
                st.write(f"• {cat}")

    with col_dir:
        st.write("#### 🎯 Definir Teto de Gastos")
        st.caption("Selecione a categoria e defina um limite mensal para acompanhar no Dashboard.")
        with st.form("n_meta"):
            cat_escolhida = st.selectbox("Categoria", lista_categorias)
            teto_valor = st.number_input("Valor Máximo (R$)", min_value=0.0, step=50.0)

            if st.form_submit_button("Salvar Meta 🎯", type="primary", use_container_width=True):
                if teto_valor > 0:
                    payload_meta = {
                        "categoria": cat_escolhida,
                        "valor_teto": float(teto_valor),
                        "usuario_id": USUARIO_ID
                    }
                    res_meta = requests.post(f"{API_URL}/limites/", json=payload_meta)
                    if res_meta.status_code == 200:
                        st.success(f"Teto de R$ {teto_valor:,.2f} definido para {cat_escolhida}!")
                        st.rerun()
                    else:
                        st.error("Erro ao salvar a meta.")
                else:
                    st.warning("Defina um valor maior que zero para o teto.")
        
        st.divider()
        st.write("#### 📊 Seus Limites Atuais")
        try:
            req_limites = requests.get(f"{API_URL}/limites/")
            if req_limites.status_code == 200:
                limites_lista = req_limites.json()
                if limites_lista:
                    for limite in limites_lista:
                        l_nome, l_valor = st.columns([3, 2])
                        l_nome.write(f"**{limite['categoria']}**")
                        l_valor.write(f"R$ {limite['valor_teto']:,.2f}")
                else:
                    st.info("Nenhum teto de gastos definido ainda.")
        except:
            st.caption("Aguardando comunicação com a API...")