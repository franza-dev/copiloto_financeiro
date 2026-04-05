import os
import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Copiloto Financeiro IA", page_icon="💰", layout="wide")

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&display=swap');

        html, body, [class*="css"], .stApp {
            font-family: 'Sora', sans-serif !important;
            background-color: #140c1c !important;
            color: #dddddd !important;
        }
        #MainMenu, footer, header { visibility: hidden; }

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
        h2, h3, h4 {
            font-family: 'Sora', sans-serif !important;
            font-weight: 600 !important;
            color: #dddddd !important;
        }
        [data-testid="stSidebar"] {
            background-color: #1e1030 !important;
            border-right: 1px solid #2a1454 !important;
        }
        [data-testid="stSidebar"] * { font-family: 'Sora', sans-serif !important; color: #dddddd !important; }
        [data-testid="stSidebarNav"] { display: none; }

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
        [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none !important; }

        .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
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
        .stButton > button:hover, .stFormSubmitButton > button:hover {
            transform: translateY(-2px) scale(1.02) !important;
            box-shadow: 6px 8px 24px rgba(135, 80, 247, 0.4) !important;
        }
        .stButton > button[kind="secondary"] {
            background: linear-gradient(135deg, #fd701c, #e05a10) !important;
            box-shadow: 6px 6px 18px rgba(253, 112, 28, 0.25) !important;
        }

        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div,
        .stTextArea textarea {
            font-family: 'Sora', sans-serif !important;
            background-color: #1e1030 !important;
            border: 1px solid #2a1454 !important;
            border-radius: 10px !important;
            color: #dddddd !important;
        }
        .stTextInput > div > div > input:focus,
        .stNumberInput > div > div > input:focus,
        .stTextArea textarea:focus {
            border-color: #8750f7 !important;
            box-shadow: 0 0 0 2px rgba(135, 80, 247, 0.2) !important;
        }

        label, .stSelectbox label, .stTextInput label, .stNumberInput label, .stRadio label {
            font-family: 'Sora', sans-serif !important;
            font-weight: 600 !important;
            color: #b0a0c8 !important;
            font-size: 0.82rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #1e1030 !important;
            border: 1px solid #2a1454 !important;
            border-radius: 16px !important;
            box-shadow: 12px 12px 50px rgba(0, 0, 0, 0.4) !important;
            padding: 1rem !important;
        }

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

        [data-testid="stProgressBar"] > div { background-color: #2a1454 !important; border-radius: 9999px !important; }
        [data-testid="stProgressBar"] > div > div {
            background: linear-gradient(90deg, #8750f7, #fd701c) !important;
            border-radius: 9999px !important;
        }

        [data-testid="stDataFrame"], .stDataEditor { border: 1px solid #2a1454 !important; border-radius: 12px !important; overflow: hidden !important; }
        hr { border-color: #2a1454 !important; margin: 1.5rem 0 !important; }
        [data-testid="stAlert"] { border-radius: 12px !important; border: none !important; font-family: 'Sora', sans-serif !important; }
        .stSpinner > div { border-top-color: #8750f7 !important; }
        .stCaption, caption { color: #7a6a90 !important; font-family: 'Sora', sans-serif !important; }

        /* Card de login */
        .login-card {
            background: #1e1030;
            border: 1px solid #2a1454;
            border-radius: 20px;
            padding: 2.5rem 2rem;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# AUTENTICAÇÃO
# ==========================================
if "usuario_id" not in st.session_state:
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("""
            <div style="text-align:center; margin-bottom: 2rem;">
                <div style="
                    background: linear-gradient(135deg, #8750f7, #fd701c);
                    border-radius: 18px; width: 60px; height: 60px;
                    display: inline-flex; align-items: center; justify-content: center;
                    font-size: 1.8rem; box-shadow: 0 8px 24px rgba(135,80,247,0.4);
                    margin-bottom: 1rem;
                ">💰</div>
                <h1 style="margin:0;">Copiloto Financeiro</h1>
                <p style="color:#7a6a90; font-size:0.85rem; margin-top:0.25rem;">Gestão inteligente das suas finanças</p>
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
                            st.session_state.usuario_id = u["id"]
                            st.session_state.usuario_nome = u["nome"]
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
                                st.session_state.usuario_id = u["id"]
                                st.session_state.usuario_nome = u["nome"]
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

# --- HEADER ---
st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:0.5rem;">
        <div style="
            background: linear-gradient(135deg, #8750f7, #fd701c);
            border-radius: 14px; width: 48px; height: 48px;
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

# --- SIDEBAR ---
st.sidebar.markdown(f"**Olá, {st.session_state.usuario_nome}!**")
if st.sidebar.button("Sair"):
    del st.session_state.usuario_id
    del st.session_state.usuario_nome
    st.rerun()

st.sidebar.divider()
st.sidebar.header("Resumo Consolidado")
st.sidebar.write("Apenas dados confirmados")

try:
    resumo_req = requests.get(f"{API_URL}/dashboard/resumo", params={"usuario_id": USUARIO_ID})
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
    if st.sidebar.button("🔄 Atualizar"):
        st.rerun()
except:
    st.sidebar.error("Servidor API offline.")

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
aba_dashboard, aba_extrato, aba_contas = st.tabs(["🏠 Painel de Controle", "🧾 Extrato", "🏦 Minhas Contas"])

# ==========================================
# ABA 1: PAINEL DE CONTROLE
# ==========================================
with aba_dashboard:
    st.write("### 📝 O que você gastou hoje?")
    texto_input = st.text_input("Descreva o gasto", placeholder="Ex: Gastei 45 reais com Uber para ir na reunião PJ")
    if st.button("Lançar com IA", use_container_width=True):
        if texto_input:
            with st.spinner("O Gemini está analisando sua frase..."):
                res = requests.post(f"{API_URL}/transacoes/ia", params={"texto": texto_input, "usuario_id": USUARIO_ID})
                if res.status_code == 200:
                    st.success("Entendido! O gasto foi para a Quarentena para sua revisão final.")
                    st.rerun()
                else:
                    st.error("Erro ao falar com a IA.")
        else:
            st.warning("Escreva algo antes de enviar.")
    st.divider()

    st.write("### 📂 Importar Extrato (CSV)")
    with st.expander("Faça upload do extrato do seu banco"):
        if not nomes_contas:
            st.warning("Cadastre uma conta na aba 'Minhas Contas' primeiro.")
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
        st.write("### 📈 Saúde Financeira")
        try:
            if 'resumo' in locals():
                pj_val = float(resumo["pj"]["despesas"].replace("R$ ", "").replace(",", ""))
                pf_val = float(resumo["pf"]["despesas"].replace("R$ ", "").replace(",", ""))
                if pj_val > 0 or pf_val > 0:
                    df_chart = pd.DataFrame({"Origem": ["Despesas Empresa (PJ)", "Despesas Pessoais (PF)"], "Valor": [pj_val, pf_val]})
                    fig = px.pie(df_chart, values='Valor', names='Origem', hole=.4, color_discrete_sequence=['#FF4B4B', '#1C83E1'])
                    st.plotly_chart(fig, use_container_width=True)

            req_hist_grafico = requests.get(f"{API_URL}/transacoes/historico", params={"usuario_id": USUARIO_ID})
            if req_hist_grafico.status_code == 200:
                hist_grafico = req_hist_grafico.json()
                if hist_grafico:
                    df_hist_graf = pd.DataFrame(hist_grafico)
                    df_desp = df_hist_graf[(df_hist_graf['valor'] < 0) & (~df_hist_graf['categoria'].str.contains('Transferência Interna', case=False, na=False))].copy()
                    if not df_desp.empty:
                        df_desp['valor_abs'] = df_desp['valor'].abs()
                        df_agrupado = df_desp.groupby(['categoria', 'tipo'])['valor_abs'].sum().reset_index()
                        st.write("#### 📊 Despesas por Categoria")
                        fig2 = px.bar(df_agrupado, x='valor_abs', y='categoria', color='tipo', orientation='h',
                                     color_discrete_sequence=['#FF4B4B', '#1C83E1'], labels={'valor_abs': 'Total (R$)', 'categoria': ''})
                        st.plotly_chart(fig2, use_container_width=True)
        except:
            st.info("Aguardando dados...")

    with col_quarentena:
        st.write("### ⏳ Quarentena (Revise e Confirme)")
        if st.button("🚨 Limpar Quarentena", use_container_width=True):
            res_limpar = requests.delete(f"{API_URL}/sistema/limpar-quarentena", params={"usuario_id": USUARIO_ID})
            if res_limpar.status_code == 200:
                st.success("Quarentena limpa!")
                st.rerun()

        try:
            res_quarentena = requests.get(f"{API_URL}/transacoes/quarentena", params={"usuario_id": USUARIO_ID})
            if res_quarentena.status_code == 200:
                transacoes = res_quarentena.json().get("transacoes", [])
                if transacoes:
                    if not nomes_contas:
                        st.warning("Cadastre pelo menos uma Conta Bancária na aba 'Minhas Contas'!")
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

                                opcoes_tipo = ["PF", "PJ"]
                                idx_tipo = opcoes_tipo.index(t['tipo']) if t['tipo'] in opcoes_tipo else 0
                                novo_tipo = c2.selectbox("Tipo", opcoes_tipo, index=idx_tipo, key=f"tipo_{t['id']}")

                                conta_id_salva = t.get('conta_id')
                                idx_conta = nomes_contas.index(id_para_nome[conta_id_salva]) if conta_id_salva in id_para_nome else 0
                                conta_selecionada = c3.selectbox("Pago com:", nomes_contas, index=idx_conta, key=f"conta_{t['id']}")
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
                    st.success("Tudo conferido! Não há pendências. ✅")
            else:
                st.error("Erro no Backend!")
        except Exception as e:
            st.error("Aguardando comunicação com a API...")

# ==========================================
# ABA 2: EXTRATO
# ==========================================
with aba_extrato:
    st.write("### 🧾 Histórico de Lançamentos")
    try:
        req_historico = requests.get(f"{API_URL}/transacoes/historico", params={"usuario_id": USUARIO_ID})
        if req_historico.status_code == 200:
            historico = req_historico.json()
            if historico:
                df_historico = pd.DataFrame(historico)
                c_filtro1, _ = st.columns(2)
                filtro_tipo = c_filtro1.selectbox("Filtrar por Tipo:", ["Todos", "PF", "PJ"])
                if filtro_tipo != "Todos":
                    df_historico = df_historico[df_historico['tipo'] == filtro_tipo]

                colunas_exibir = ['id', 'data', 'descricao', 'valor', 'categoria', 'tipo', 'conta_id']
                colunas_disponiveis = [col for col in colunas_exibir if col in df_historico.columns]
                st.dataframe(df_historico[colunas_disponiveis], use_container_width=True, hide_index=True)

                st.download_button(
                    label="📥 Baixar Planilha para o Contador (.csv)",
                    data=df_historico[colunas_disponiveis].to_csv(index=False).encode('utf-8'),
                    file_name="extrato_financeiro.csv",
                    mime="text/csv",
                    type="primary"
                )

                st.divider()
                st.write("#### ✏️ Editar Lançamento Manualmente")
                with st.expander("Clique aqui para corrigir um lançamento já confirmado"):
                    opcoes_edicao = {f"ID {x['id']} | {x.get('data','')} | {x['descricao']} (R$ {x['valor']})": x for x in historico}
                    if opcoes_edicao:
                        escolha_edicao = st.selectbox("Selecione o lançamento:", list(opcoes_edicao.keys()))
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
                            m_tipo = ce5.selectbox("Tipo", ["PF", "PJ"], index=0 if tx_edit['tipo']=="PF" else 1)
                            idx_c_ed = nomes_contas.index(id_para_nome[tx_edit['conta_id']]) if tx_edit['conta_id'] in id_para_nome else 0
                            m_conta = ce6.selectbox("Conta", nomes_contas, index=idx_c_ed)
                            if st.form_submit_button("Salvar Alterações ✅", type="primary"):
                                payload_edicao = {"data": m_data, "descricao": m_desc, "valor": m_val, "categoria": m_cat, "tipo": m_tipo, "conta_id": opcoes_contas[m_conta]}
                                res_put = requests.put(f"{API_URL}/transacoes/{tx_edit['id']}", json=payload_edicao)
                                if res_put.status_code == 200:
                                    st.success("Lançamento corrigido!")
                                    st.rerun()
                                else:
                                    st.error("Erro ao editar.")
            else:
                st.info("Seu extrato está vazio. Confirme alguns gastos na quarentena!")
        else:
            st.warning("Não foi possível carregar o histórico.")
    except:
        st.error("Erro ao carregar o extrato. A API está rodando?")

# ==========================================
# ABA 3: MINHAS CONTAS
# ==========================================
with aba_contas:
    st.write("### 🏦 Gerenciamento de Contas e Carteiras")

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
                    res = requests.post(f"{API_URL}/contas/", json=payload)
                    if res.status_code == 200:
                        st.success("Conta cadastrada!")
                        st.rerun()
                else:
                    st.warning("Preencha o nome e o banco.")

    st.divider()
    st.write("#### Suas Contas Atuais:")
    if contas:
        st.dataframe(pd.DataFrame(contas)[['id', 'nome', 'banco', 'tipo']], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma conta cadastrada ainda.")

    st.divider()
    st.write("#### ⚠️ Zona de Perigo")
    st.warning("Atenção: Ações abaixo são irreversíveis!")
    c_perigo1, c_perigo2 = st.columns(2)

    if c_perigo1.button("🗑️ Zerar Minhas Transações", type="secondary"):
        if requests.delete(f"{API_URL}/sistema/resetar-transacoes", params={"usuario_id": USUARIO_ID}).status_code == 200:
            st.success("Suas transações foram zeradas!")
            st.rerun()

    if c_perigo2.button("🚨 FORMATAR BANCO DE DADOS (APAGA TUDO)", type="primary"):
        if requests.delete(f"{API_URL}/sistema/recriar-banco").status_code == 200:
            st.success("Banco formatado! Faça login novamente.")
            del st.session_state.usuario_id
            del st.session_state.usuario_nome
            st.rerun()
