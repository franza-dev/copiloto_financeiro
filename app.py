import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Copiloto Financeiro IA", page_icon="💰", layout="wide")

API_URL = "https://copiloto-backend-api.onrender.com"

st.title("🤖 Copiloto Financeiro IA")

# --- SIDEBAR: RESUMO RÁPIDO ---
st.sidebar.header("📊 Resumo Consolidado")
st.sidebar.write("Apenas dados confirmados")

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

# --- DADOS GLOBAIS DE CONTAS (Carregados com Segurança) ---
contas = []
opcoes_contas = {}
nomes_contas = []
id_para_nome = {}
try:
    req_contas = requests.get(f"{API_URL}/contas/1")
    if req_contas.status_code == 200:
        contas = req_contas.json()
        opcoes_contas = {f"{c['nome']} ({c['tipo']})": c['id'] for c in contas}
        nomes_contas = list(opcoes_contas.keys())
        id_para_nome = {v: k for k, v in opcoes_contas.items()}
except:
    pass

# --- ESTRUTURA DE ABAS ---
aba_dashboard, aba_extrato, aba_contas = st.tabs(["🏠 Painel de Controle", "🧾 Extrato", "🏦 Minhas Contas"])

# ==========================================
# ABA 1: PAINEL DE CONTROLE E DASHBOARD
# ==========================================
with aba_dashboard:
    # --- ÁREA 1: LANÇAMENTO COM IA ---
    st.write("### 📝 O que você gastou hoje?")
    texto_input = st.text_input("Descreva o gasto", placeholder="Ex: Gastei 45 reais com Uber para ir na reunião PJ")
    if st.button("Lançar com IA", use_container_width=True):
        if texto_input:
            with st.spinner("O Gemini está analisando sua frase..."):
                res = requests.post(f"{API_URL}/transacoes/ia?texto={texto_input}&usuario_id=1")
                if res.status_code == 200:
                    st.success("Entendido! O gasto foi para a Quarentena para sua revisão final.")
                    st.rerun()
                else:
                    st.error("Erro ao falar com a IA ou Usuário ID 1 não existe.")
        else:
            st.warning("Escreva algo antes de enviar.")
    st.divider()
    
    # --- ÁREA 1.5: OPEN FINANCE DE GUERRILHA (UPLOAD CSV) ---
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
                        if any('valor' in celula for celula in linha_texto) and any('descri' in celula or 'hist' in celula for celula in linha_texto):
                            header_idx = i
                            break
                    
                    df_extrato.columns = df_extrato.iloc[header_idx].astype(str).str.lower()
                    df_extrato = df_extrato.iloc[header_idx+1:].reset_index(drop=True)
                    
                    col_desc = next((c for c in df_extrato.columns if 'descri' in c or 'historico' in c), None)
                    col_val = next((c for c in df_extrato.columns if 'valor' in c), None)
                    # Busca a coluna de data inteligente!
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
                                        transacoes_para_api.append({
                                            "data": data_extrato,
                                            "descricao": str(row[col_desc]),
                                            "valor": valor_float
                                        })
                            except ValueError:
                                pass 
                                
                        payload = {"conta_id": id_conta_upload, "transacoes": transacoes_para_api}
                        res_lote = requests.post(f"{API_URL}/transacoes/lote", json=payload)
                        if res_lote.status_code == 200:
                            st.success(f"Bingo! As transações foram enviadas para a Quarentena.")
                            st.rerun()
                        else:
                            st.error("Erro ao enviar lote para a API.")
                    else:
                        st.error("Ops! Não consegui achar as colunas no seu arquivo.")
                except Exception as e:
                    st.error(f"Erro ao ler o CSV. Detalhe: {e}")

    st.divider()

    # --- ÁREA 2: DASHBOARD E QUARENTENA ---
    col_grafico, col_quarentena = st.columns([1, 1.5])

    # GRÁFICOS (PIZZA + BARRAS POR CATEGORIA)
    with col_grafico:
        st.write("### 📈 Saúde Financeira")
        try:
            # Gráfico Original (Pizza)
            if 'resumo' in locals():
                pj_val = float(resumo["pj"]["despesas"].replace("R$ ", "").replace(",", ""))
                pf_val = float(resumo["pf"]["despesas"].replace("R$ ", "").replace(",", ""))
                if pj_val > 0 or pf_val > 0:
                    df_chart = pd.DataFrame({
                        "Origem": ["Despesas Empresa (PJ)", "Despesas Pessoais (PF)"],
                        "Valor": [pj_val, pf_val]
                    })
                    fig = px.pie(df_chart, values='Valor', names='Origem', hole=.4, color_discrete_sequence=['#FF4B4B', '#1C83E1'])
                    st.plotly_chart(fig, use_container_width=True)

            # Novo Gráfico (Barras por Categoria)
            req_hist_grafico = requests.get(f"{API_URL}/transacoes/historico")
            if req_hist_grafico.status_code == 200:
                hist_grafico = req_hist_grafico.json()
                if hist_grafico:
                    df_hist_graf = pd.DataFrame(hist_grafico)
                    # Filtra apenas despesas (valor < 0) e ignora as transferências internas
                    df_desp = df_hist_graf[(df_hist_graf['valor'] < 0) & (~df_hist_graf['categoria'].str.contains('Transferência Interna', case=False, na=False))].copy()
                    
                    if not df_desp.empty:
                        df_desp['valor_abs'] = df_desp['valor'].abs()
                        df_agrupado = df_desp.groupby(['categoria', 'tipo'])['valor_abs'].sum().reset_index()
                        
                        st.write("#### 📊 Despesas por Categoria")
                        fig2 = px.bar(df_agrupado, x='valor_abs', y='categoria', color='tipo', orientation='h', 
                                     color_discrete_sequence=['#FF4B4B', '#1C83E1'], labels={'valor_abs': 'Total (R$)', 'categoria': ''})
                        st.plotly_chart(fig2, use_container_width=True)
        except:
            st.info("Aguardando dados ou banco precisa ser formatado...")

    # QUARENTENA BLINDADA (COM DATA E EDIÇÃO DE VALORES)
    with col_quarentena:
        st.write("### ⏳ Quarentena (Revise e Confirme)")
        if st.button("🚨 Epa, importei errado! Limpar Quarentena", use_container_width=True):
            res_limpar = requests.delete(f"{API_URL}/sistema/limpar-quarentena")
            if res_limpar.status_code == 200:
                st.success("Quarentena limpa! Agora você pode importar o arquivo correto.")
                st.rerun()
                
        try:
            res_quarentena = requests.get(f"{API_URL}/transacoes/quarentena")
            if res_quarentena.status_code == 200:
                transacoes = res_quarentena.json().get("transacoes", [])

                if transacoes:
                    if not nomes_contas:
                        st.warning("Cadastre pelo menos uma Conta Bancária na aba 'Minhas Contas'!")
                    else:
                        categorias_aprendidas = set()
                        try:
                            req_hist = requests.get(f"{API_URL}/transacoes/historico")
                            if req_hist.status_code == 200:
                                categorias_aprendidas = {x['categoria'] for x in req_hist.json()}
                        except: pass
                            
                        lista_base = [
                            "Vendas / Receitas", "Prestação de Serviços", "Transferência Interna", 
                            "Alimentação", "Transporte e Combustível", "Impostos (DAS, etc)",
                            "Ferramentas e Software", "Tarifas Bancárias", "Pró-Labore / Salário",
                            "Equipamentos", "A Classificar"
                        ]
                        
                        lista_dinamica = sorted(list(set(lista_base) | categorias_aprendidas))
                        lista_dinamica.append("Outra...")

                        for t in transacoes:
                            # Titulo do Expander mostra a data e o valor
                            titulo_expander = f"🛒 {t.get('data','')} | {t['descricao']} - R$ {t['valor']:.2f}"
                            with st.expander(titulo_expander, expanded=True):
                                
                                # --- NOVOS CAMPOS EDITÁVEIS (DATA, DESCRIÇÃO, VALOR) ---
                                col_d, col_de, col_v = st.columns([1,2,1])
                                ed_data = col_d.text_input("Data", value=t.get('data',''), key=f"d_{t['id']}")
                                ed_desc = col_de.text_input("Descrição", value=t['descricao'], key=f"de_{t['id']}")
                                ed_val = col_v.number_input("Valor", value=float(t['valor']), step=0.01, key=f"v_{t['id']}")
                                
                                c1, c2, c3 = st.columns(3)
                                
                                cat_atual = t['categoria']
                                if cat_atual not in lista_dinamica:
                                    lista_dinamica.insert(0, cat_atual)
                                    
                                escolha_cat = c1.selectbox("Categoria", lista_dinamica, index=lista_dinamica.index(cat_atual), key=f"sel_cat_{t['id']}")
                                
                                if escolha_cat == "Outra...":
                                    nova_cat = c1.text_input("Qual nova categoria?", key=f"txt_cat_{t['id']}")
                                else:
                                    nova_cat = escolha_cat
                                
                                opcoes_tipo = ["PF", "PJ"]
                                idx_tipo = opcoes_tipo.index(t['tipo']) if t['tipo'] in opcoes_tipo else 0
                                novo_tipo = c2.selectbox("Tipo", opcoes_tipo, index=idx_tipo, key=f"tipo_{t['id']}")
                                
                                conta_id_salva = t.get('conta_id')
                                idx_conta = nomes_contas.index(id_para_nome[conta_id_salva]) if conta_id_salva in id_para_nome else 0
                                
                                conta_selecionada = c3.selectbox("Pago com:", nomes_contas, index=idx_conta, key=f"conta_{t['id']}")
                                id_conta_escolhida = opcoes_contas[conta_selecionada]
                                
                                c_btn1, c_btn2 = st.columns(2)
                                if c_btn1.button("Confirmar ✅", key=f"btn_{t['id']}", use_container_width=True):
                                    payload = {
                                        "data": ed_data,
                                        "descricao": ed_desc,
                                        "valor": ed_val,
                                        "categoria": nova_cat, 
                                        "tipo": novo_tipo, 
                                        "conta_id": id_conta_escolhida
                                    }
                                    conf_res = requests.patch(f"{API_URL}/transacoes/{t['id']}/confirmar", json=payload)
                                    if conf_res.status_code == 200:
                                        st.rerun()
                                
                                if c_btn2.button("Apagar 🗑️", key=f"del_{t['id']}", use_container_width=True):
                                    requests.delete(f"{API_URL}/transacoes/{t['id']}")
                                    st.rerun()
                else:
                    st.success("Tudo conferido! Não há pendências. ✅")
            else:
                st.error("Erro no Backend! Pode ser necessário formatar o banco de dados na aba de Minhas Contas.")
        except Exception as e:
            st.error(f"Aguardando comunicação com a API...")

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
                
                # --- FILTROS LATERAIS ---
                c_filtro1, c_filtro2 = st.columns(2)
                filtro_tipo = c_filtro1.selectbox("Filtrar por Tipo:", ["Todos", "PF", "PJ"])
                
                if filtro_tipo != "Todos":
                    df_historico = df_historico[df_historico['tipo'] == filtro_tipo]
                
                # Exibe a tabela incluindo a Data
                colunas_exibir = ['id', 'data', 'descricao', 'valor', 'categoria', 'tipo', 'conta_id']
                colunas_disponiveis = [col for col in colunas_exibir if col in df_historico.columns]
                
                st.dataframe(df_historico[colunas_disponiveis], use_container_width=True, hide_index=True)
                
                st.download_button(
                    label="📥 Baixar Planilha para o Contador (.csv)",
                    data=df_historico[colunas_disponiveis].to_csv(index=False).encode('utf-8'),
                    file_name="meu_extrato_financeiro.csv",
                    mime="text/csv",
                    type="primary"
                )
                
                # --- MÓDULO DE EDIÇÃO MANUAL ---
                st.divider()
                st.write("#### ✏️ Editar Lançamento Manualmente")
                with st.expander("Clique aqui para corrigir um lançamento já confirmado"):
                    # Cria um dicionário bonito para o selectbox
                    opcoes_edicao = {f"ID {x['id']} | {x.get('data','')} | {x['descricao']} (R$ {x['valor']})": x for x in historico}
                    
                    if opcoes_edicao:
                        escolha_edicao = st.selectbox("Selecione o lançamento que deseja editar:", list(opcoes_edicao.keys()))
                        tx_edit = opcoes_edicao[escolha_edicao]
                        
                        with st.form("form_edicao"):
                            ce1, ce2, ce3 = st.columns([1,2,1])
                            m_data = ce1.text_input("Data", value=tx_edit.get('data', ''))
                            m_desc = ce2.text_input("Descrição", value=tx_edit['descricao'])
                            m_val = ce3.number_input("Valor", value=float(tx_edit['valor']), step=0.01)

                            ce4, ce5, ce6 = st.columns(3)
                            
                            # Recupera a lista dinâmica ou cria uma base rápida
                            lista_cats_ed = [tx_edit['categoria']] if 'lista_dinamica' not in locals() else lista_dinamica.copy()
                            if tx_edit['categoria'] not in lista_cats_ed: 
                                lista_cats_ed.insert(0, tx_edit['categoria'])
                            
                            m_cat = ce4.selectbox("Categoria", lista_cats_ed, index=lista_cats_ed.index(tx_edit['categoria']))
                            if m_cat == "Outra...": 
                                m_cat = ce4.text_input("Qual nova categoria?")
                            
                            m_tipo = ce5.selectbox("Tipo", ["PF", "PJ"], index=0 if tx_edit['tipo']=="PF" else 1)
                            
                            idx_c_ed = nomes_contas.index(id_para_nome[tx_edit['conta_id']]) if tx_edit['conta_id'] in id_para_nome else 0
                            m_conta = ce6.selectbox("Conta", nomes_contas, index=idx_c_ed)

                            if st.form_submit_button("Salvar Alterações ✅", type="primary"):
                                payload_edicao = {
                                    "data": m_data, 
                                    "descricao": m_desc, 
                                    "valor": m_val,
                                    "categoria": m_cat, 
                                    "tipo": m_tipo, 
                                    "conta_id": opcoes_contas[m_conta]
                                }
                                res_put = requests.put(f"{API_URL}/transacoes/{tx_edit['id']}", json=payload_edicao)
                                if res_put.status_code == 200:
                                    st.success("Lançamento corrigido com sucesso!")
                                    st.rerun()
                                else:
                                    st.error("Erro ao editar o lançamento.")
            else:
                st.info("Seu extrato está vazio. Confirme alguns gastos na quarentena!")
        else:
            st.warning("Não foi possível carregar o histórico. Você precisa formatar o banco?")
    except Exception as e:
        st.error(f"Erro ao carregar o extrato. A API está rodando?")

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
            nome_conta = c1.text_input("Nome (Ex: Nubank PJ)")
            banco_conta = c2.text_input("Banco (Ex: Nubank)")
            tipo_conta = c3.selectbox("Finalidade", ["PJ", "PF"])
            
            submit_conta = st.form_submit_button("Salvar Conta", type="primary")
            
            if submit_conta:
                if nome_conta and banco_conta:
                    payload = {"nome": nome_conta, "banco": banco_conta, "tipo": tipo_conta, "usuario_id": 1}
                    res = requests.post(f"{API_URL}/contas/", json=payload)
                    if res.status_code == 200:
                        st.success("Conta cadastrada com sucesso!")
                        st.rerun()
                else:
                    st.warning("Preencha o nome e o banco.")
                
    st.divider()
    
    st.write("#### Suas Contas Atuais:")
    if contas:
        df_contas = pd.DataFrame(contas)
        st.dataframe(df_contas[['id', 'nome', 'banco', 'tipo']], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma conta cadastrada ou servidor offline.")

    # --- ZONA DE PERIGO (COM BOTÃO DE FORMATAR O BANCO) ---
    st.divider()
    st.write("#### ⚠️ Zona de Perigo")
    st.warning("Atenção: Ações abaixo são irreversíveis!")
    
    c_perigo1, c_perigo2 = st.columns(2)
    
    if c_perigo1.button("🗑️ Zerar Transações (Mantém Contas)", type="secondary"):
        res_reset = requests.delete(f"{API_URL}/sistema/resetar-transacoes")
        if res_reset.status_code == 200:
            st.success("Transações zeradas!")
            st.rerun()

    if c_perigo2.button("🚨 FORMATAR BANCO DE DADOS (APAGA TUDO)", type="primary"):
        res_formatar = requests.delete(f"{API_URL}/sistema/recriar-banco")
        if res_formatar.status_code == 200:
            st.success("Banco de Dados formatado com sucesso! Atualize a página e recadastre suas contas.")
            st.rerun()
