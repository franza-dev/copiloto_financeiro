"""
Guido — Chat Handler
Chat conversacional dentro do app, com dois modos:

  - "suporte"     → tira dúvidas sobre como usar o sistema
  - "conselheiro" → conselhos financeiros baseados nos dados reais do usuário

Usa Gemini 2.5 Flash (mesmo modelo do whatsapp_handler).
"""
import os
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from google import genai

import models
import database

router = APIRouter(prefix="/chat", tags=["chat"])

_GEMINI_KEY = os.getenv("GOOGLE_API_KEY", "")
_client = genai.Client(api_key=_GEMINI_KEY) if _GEMINI_KEY else None


# ==========================================
# PROMPTS
# ==========================================

_PROMPT_SUPORTE = """Você é o Guido em modo SUPORTE: ajuda o usuário a entender e usar o sistema.

CONHECIMENTO DO SISTEMA:

VISÃO GERAL:
- O Guido é um assistente financeiro pra MEIs (microempreendedores).
- Separa o dinheiro da Casa (PF) do dinheiro do Negócio (PJ) automaticamente.
- O usuário interage de duas formas: pelo app (app.chamaoguido.com) e pelo WhatsApp.

WHATSAPP:
- Usuário pode mandar texto ou áudio relatando um gasto/recebimento.
- Exemplos: "gastei 80 em mercado", "recebi 500 do cliente", áudios narrando o gasto.
- O Guido interpreta com IA, escolhe a categoria e a conta certa, e lança automaticamente.
- Se a IA não tiver certeza, manda pra Quarentena no app pra revisão.
- Também responde consultas: "como tá o teto de alimentação?", "saldo do mês".

ABAS DO APP:
1. 🌱 Painel: lançamentos manuais, quarentena (pendentes de revisão), gráfico de saldo, barras de progresso de tetos.
2. 📊 Dashboards: 7 gráficos (evolução mensal, despesas por categoria, donut PF/PJ, heatmap, gauge MEI, etc).
3. 💰 Fluxo de Caixa: tabela pivô estilo Excel, dias × categorias, com saldo acumulado e tooltips por célula.
4. 🧾 Histórico: tabela editável de todas as transações, com checkbox pra excluir e edição inline.
5. 🏦 Contas: cadastro de contas correntes e cartões de crédito (com fechamento/vencimento).
6. 📂 Categorias & Metas: cria/edita/exclui categorias e define tetos mensais por categoria.
7. 👤 Minha Conta: dados pessoais, troca de senha, modo claro/escuro, gerenciamento de assinatura.

IMPORTAÇÃO DE EXTRATO (CSV):
- Aba Painel → "Subir extrato do banco (CSV)".
- Aceita formatos PT (data, descrição, valor) e EN (date, title, amount).
- Cartão de crédito: o sistema inverte automaticamente o sinal (CSV vem com positivo pra compras, negativo pra pagamentos).
- "Pagamento recebido" no cartão é classificado automaticamente como "Transferência Interna" (não duplica nos relatórios).
- Auto-categorização: se já houver transação confirmada com descrição parecida, o sistema sugere a categoria automaticamente.

CARTÃO DE CRÉDITO:
- Compras no cartão são contabilizadas pela DATA DA COMPRA (competência), não pela data de pagamento.
- O sistema calcula automaticamente a "data de caixa" (quando o dinheiro sai da conta corrente) baseado no fechamento e vencimento do cartão.

TETOS DE GASTOS:
- São MENSAIS. Cada categoria pode ter um valor máximo definido por mês.
- Quando ultrapassa 70%, fica amarelo. Quando estoura, fica vermelho.
- Na aba Dashboards, em "Ano todo", o teto é multiplicado pelo número de meses do período.

CATEGORIAS:
- Tabela única editável (sem distinção padrão vs personalizada).
- Pode renomear/excluir tudo, exceto "A Classificar" (usada pela quarentena).
- Renomear categoria propaga pras transações antigas (não fica órfão).
- Excluir categoria reatribui transações pra "A Classificar".

ASSINATURA:
- R$ 19/mês via Asaas (pagamento recorrente).
- Cancelamento na aba Minha Conta: o acesso continua até o fim do período pago.

REGRAS DE OURO:
- Responda em português brasileiro, tom conversacional ("você"), com no máximo 4-5 frases por resposta.
- Seja direto: explique COMO fazer, não só onde clicar.
- Se a pergunta for sobre finanças (não sobre o sistema), sugira mudar pro modo Conselheiro.
- NUNCA invente funcionalidades que não estão acima.
- Se não souber, diga que não sabe e sugira contato direto."""


_PROMPT_CONSELHEIRO_BASE = """Você é o Guido em modo CONSELHEIRO FINANCEIRO: especialista em finanças de MEI/microempreendedor brasileiro.

SEU PAPEL:
- Dar conselhos práticos baseados nos DADOS REAIS do usuário (injetados abaixo).
- Trazer insights, padrões e recomendações específicas — não respostas genéricas.
- Linguagem clara, sem jargão de contador. Tom amigo experiente.
- Foco em: separação Casa/Negócio, controle de tetos, limite MEI, gestão de cartão, pró-labore, fluxo de caixa.

DIRETRIZES:
- Cite números concretos do contexto (R$ X em Y, Z% do teto, etc).
- Quando relevante, mencione tendências ("você gastou mais em X esse mês").
- Se faltar dado pra responder bem, peça especificações.
- 4-7 frases por resposta. Direto ao ponto.
- Se a pergunta for sobre o sistema (como fazer X no app), sugira mudar pro modo Suporte.

CONTEXTO FINANCEIRO DO USUÁRIO (mês corrente):
"""


# ==========================================
# SCHEMAS
# ==========================================

class MensagemChat(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatInput(BaseModel):
    usuario_id: int
    modo: str  # "suporte" | "conselheiro"
    mensagem: str
    historico: Optional[List[MensagemChat]] = None  # mensagens anteriores pra contexto


# ==========================================
# CONTEXTO PRO CONSELHEIRO
# ==========================================

def _montar_contexto_financeiro(db: Session, usuario_id: int) -> str:
    """Coleta dados do mês atual pra injetar no prompt do Conselheiro."""
    hoje = date.today()
    prefixo_mes = f"{hoje.year:04d}-{hoje.month:02d}"

    # Receitas e despesas do mês (exclui Transferência Interna)
    txs = db.query(models.Transacao).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Transacao.confirmado == True,
        models.Transacao.data.like(f"{prefixo_mes}%"),
        models.Transacao.categoria != "Transferência Interna",
    ).all()

    receitas_pf = sum(t.valor for t in txs if t.valor > 0 and t.tipo == "PF")
    receitas_pj = sum(t.valor for t in txs if t.valor > 0 and t.tipo == "PJ")
    despesas_pf = abs(sum(t.valor for t in txs if t.valor < 0 and t.tipo == "PF"))
    despesas_pj = abs(sum(t.valor for t in txs if t.valor < 0 and t.tipo == "PJ"))

    # Top 5 categorias de gasto
    gastos_cat = {}
    for t in txs:
        if t.valor < 0:
            gastos_cat[t.categoria] = gastos_cat.get(t.categoria, 0) + abs(t.valor)
    top_cats = sorted(gastos_cat.items(), key=lambda x: x[1], reverse=True)[:5]

    # Tetos cadastrados e % usado
    limites = db.query(models.LimiteCategoria).filter(
        models.LimiteCategoria.usuario_id == usuario_id,
    ).all()
    tetos_status = []
    for lim in limites:
        gasto_cat = gastos_cat.get(lim.categoria, 0)
        pct = (gasto_cat / lim.valor_teto * 100) if lim.valor_teto > 0 else 0
        tetos_status.append((lim.categoria, gasto_cat, lim.valor_teto, pct))

    # Faturamento PJ do ano (pra limite MEI)
    prefixo_ano = f"{hoje.year:04d}-"
    faturamento_pj = db.query(func.sum(models.Transacao.valor)).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Transacao.confirmado == True,
        models.Transacao.tipo == "PJ",
        models.Transacao.valor > 0,
        models.Transacao.data.like(f"{prefixo_ano}%"),
        models.Transacao.categoria != "Transferência Interna",
    ).scalar() or 0
    pct_mei = (faturamento_pj / 81000) * 100  # limite MEI 2025: R$ 81k

    # Contas
    contas = db.query(models.ContaBancaria).filter(
        models.ContaBancaria.usuario_id == usuario_id,
    ).all()

    # Monta texto
    linhas = [
        f"Mês de referência: {prefixo_mes}",
        f"",
        f"💰 RESUMO DO MÊS:",
        f"  Receitas PF (Casa):     R$ {receitas_pf:,.2f}",
        f"  Receitas PJ (Negócio):  R$ {receitas_pj:,.2f}",
        f"  Despesas PF (Casa):     R$ {despesas_pf:,.2f}",
        f"  Despesas PJ (Negócio):  R$ {despesas_pj:,.2f}",
        f"  Saldo PF: R$ {receitas_pf - despesas_pf:,.2f}",
        f"  Saldo PJ: R$ {receitas_pj - despesas_pj:,.2f}",
    ]

    if top_cats:
        linhas.append(f"")
        linhas.append(f"📊 TOP CATEGORIAS DE GASTO:")
        for cat, val in top_cats:
            linhas.append(f"  {cat}: R$ {val:,.2f}")

    if tetos_status:
        linhas.append(f"")
        linhas.append(f"🎯 TETOS DE GASTO (mensais):")
        for cat, gasto, teto, pct in tetos_status:
            sinal = "🔴 estourado" if pct > 100 else ("🟡 atenção" if pct >= 70 else "🟢 ok")
            linhas.append(f"  {cat}: R$ {gasto:,.2f} de R$ {teto:,.2f} ({pct:.0f}%) {sinal}")

    linhas.append(f"")
    linhas.append(f"🏛️ LIMITE MEI:")
    linhas.append(f"  Faturamento PJ no ano: R$ {faturamento_pj:,.2f} de R$ 81.000 ({pct_mei:.1f}%)")

    if contas:
        linhas.append(f"")
        linhas.append(f"🏦 CONTAS CADASTRADAS: {len(contas)}")
        for c in contas:
            modalidade = "💳 cartão" if c.modalidade == "cartao_credito" else "🏦 corrente"
            linhas.append(f"  {modalidade} · {c.nome} ({c.banco}) · {c.tipo}")

    return "\n".join(linhas)


# ==========================================
# ENDPOINT
# ==========================================

@router.post("/")
def conversar(payload: ChatInput, db: Session = Depends(database.get_db)):
    if not _client:
        raise HTTPException(status_code=503, detail="Gemini não configurado (GOOGLE_API_KEY ausente)")

    if payload.modo not in ("suporte", "conselheiro"):
        raise HTTPException(status_code=400, detail="modo deve ser 'suporte' ou 'conselheiro'")

    if not payload.mensagem.strip():
        raise HTTPException(status_code=400, detail="mensagem vazia")

    # Monta o prompt sistema baseado no modo
    if payload.modo == "suporte":
        system_prompt = _PROMPT_SUPORTE
    else:
        contexto = _montar_contexto_financeiro(db, payload.usuario_id)
        system_prompt = _PROMPT_CONSELHEIRO_BASE + contexto

    # Monta o histórico no formato esperado pela API do Gemini
    contents = []
    if payload.historico:
        for m in payload.historico[-10:]:  # últimas 10 mensagens só
            role = "user" if m.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m.content}]})
    contents.append({"role": "user", "parts": [{"text": payload.mensagem}]})

    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config={"system_instruction": system_prompt},
        )
        resposta = response.text.strip() if response.text else "Desculpa, não consegui gerar uma resposta."
    except Exception as e:
        print(f"[Chat] Erro Gemini: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na IA: {e}")

    return {"resposta": resposta}
