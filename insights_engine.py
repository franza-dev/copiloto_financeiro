"""
Guido — Motor de Insights Financeiros
Funções puras que recebem dados e retornam lista de insights priorizados.
Sem chamadas externas — tudo calculado localmente para performance.

Adaptado ao modelo de dados do Guido:
  - valor < 0 = despesa (saída)
  - valor > 0 = receita (entrada)
  - tipo = 'PF' (Casa) ou 'PJ' (Negócio)
  - categoria = nome da categoria
  - Exclui 'Transferência Interna' dos cálculos
"""
from dataclasses import dataclass
from typing import List
import pandas as pd


@dataclass
class Insight:
    tipo: str       # "ok" | "atencao" | "critico" | "info"
    emoji: str
    titulo: str
    mensagem: str
    prioridade: int  # 1=critico, 2=atencao, 3=info, 4=ok


def gerar_insights(
    df_atual: pd.DataFrame,
    df_anterior: pd.DataFrame,
    tetos: dict,
    faturamento_ano: float,
    limite_mei: float = 81000,
) -> List[Insight]:
    """Gera lista de insights priorizados a partir dos dados financeiros.

    Args:
        df_atual: transações do período atual (já filtrado, só confirmadas)
        df_anterior: transações do período anterior (pra comparação)
        tetos: dict {categoria: valor_teto}
        faturamento_ano: receitas PJ acumuladas no ano corrente
        limite_mei: teto anual do MEI (R$ 81.000 padrão)
    """
    insights = []

    # Filtra transferências internas
    df = df_atual[~df_atual['categoria'].str.contains('Transferência Interna', case=False, na=False)].copy()
    df_ant = df_anterior[~df_anterior['categoria'].str.contains('Transferência Interna', case=False, na=False)].copy() if not df_anterior.empty else pd.DataFrame()

    receitas = df[df['valor'] > 0]['valor'].sum()
    despesas = abs(df[df['valor'] < 0]['valor'].sum())
    saldo = receitas - despesas

    pct_mei = (faturamento_ano / limite_mei * 100) if limite_mei > 0 else 0
    gastos_cat = df[df['valor'] < 0].groupby('categoria')['valor'].apply(lambda x: abs(x.sum())).to_dict()

    # Período anterior
    receitas_ant = df_ant[df_ant['valor'] > 0]['valor'].sum() if not df_ant.empty else 0
    despesas_ant = abs(df_ant[df_ant['valor'] < 0]['valor'].sum()) if not df_ant.empty else 0

    # ── CRÍTICOS ──────────────────────────────────────────
    if despesas > receitas and receitas > 0:
        insights.append(Insight("critico", "🚨", "Despesas superaram receitas",
            f"Você gastou R$ {despesas - receitas:,.2f} a mais do que recebeu. "
            "Revise as categorias com maior gasto.", 1))

    if pct_mei >= 85:
        faltam = max(0, limite_mei - faturamento_ano)
        insights.append(Insight("critico", "🚨", "Limite MEI crítico",
            f"Você está em {pct_mei:.1f}% do limite anual. "
            f"Faltam apenas R$ {faltam:,.0f}. Considere parar de faturar ou migrar pra ME.", 1))

    for cat, teto in tetos.items():
        gasto = gastos_cat.get(cat, 0)
        if gasto > teto:
            excesso = gasto - teto
            insights.append(Insight("critico", "🚨", f"Teto estourado: {cat}",
                f"R$ {excesso:,.2f} acima do teto (R$ {gasto:,.2f} de R$ {teto:,.2f}).", 1))

    # ── ATENÇÃO ───────────────────────────────────────────
    if 60 <= pct_mei < 85:
        insights.append(Insight("atencao", "⚠️", "Fique de olho no limite MEI",
            f"Você já usou {pct_mei:.1f}% do limite anual. Monitore o faturamento.", 2))

    for cat, teto in tetos.items():
        gasto = gastos_cat.get(cat, 0)
        pct_teto = (gasto / teto * 100) if teto > 0 else 0
        if 75 <= pct_teto < 100:
            insights.append(Insight("atencao", "⚠️", f"Teto próximo: {cat}",
                f"{cat} está em {pct_teto:.0f}% do teto (R$ {gasto:,.0f} de R$ {teto:,.0f}).", 2))

    if despesas_ant > 0:
        variacao = (despesas - despesas_ant) / despesas_ant * 100
        if variacao > 20:
            insights.append(Insight("atencao", "⚠️", "Despesas crescendo",
                f"Aumentaram {variacao:.0f}% vs período anterior "
                f"(R$ {despesas_ant:,.0f} → R$ {despesas:,.0f}).", 2))

    # ── INFORMAÇÃO ────────────────────────────────────────
    if not df_ant.empty:
        gastos_ant = df_ant[df_ant['valor'] < 0].groupby('categoria')['valor'].apply(lambda x: abs(x.sum()))
        for cat, gasto in gastos_cat.items():
            if cat in gastos_ant.index and gastos_ant[cat] > 0:
                var = (gasto - gastos_ant[cat]) / gastos_ant[cat] * 100
                if var > 30:
                    insights.append(Insight("info", "💡", f"Gasto crescendo: {cat}",
                        f"{cat} cresceu {var:.0f}% vs anterior "
                        f"(R$ {gastos_ant[cat]:,.0f} → R$ {gasto:,.0f}).", 3))

    if 'data' in df.columns and len(df[df['valor'] < 0]) > 5:
        df_desp = df[df['valor'] < 0].copy()
        try:
            df_desp['_data'] = pd.to_datetime(df_desp['data'], errors='coerce')
            df_desp['dia_semana'] = df_desp['_data'].dt.day_name()
            dia_mais_gasto = df_desp.groupby('dia_semana')['valor'].apply(lambda x: abs(x.sum())).idxmax()
            nomes_pt = {
                'Monday': 'segunda', 'Tuesday': 'terça', 'Wednesday': 'quarta',
                'Thursday': 'quinta', 'Friday': 'sexta', 'Saturday': 'sábado', 'Sunday': 'domingo',
            }
            dia_pt = nomes_pt.get(dia_mais_gasto, dia_mais_gasto)
            insights.append(Insight("info", "💡", "Padrão de gasto detectado",
                f"Você tende a gastar mais nas {dia_pt}s.", 3))
        except Exception:
            pass

    # ── POSITIVOS ─────────────────────────────────────────
    if saldo > 0 and receitas > 0 and saldo > receitas * 0.3:
        insights.append(Insight("ok", "✅", "Mês saudável",
            f"Saldo de R$ {saldo:,.2f} ({saldo / receitas * 100:.0f}% das receitas). "
            "Bom controle.", 4))

    if receitas_ant > 0 and receitas > receitas_ant:
        crescimento = (receitas - receitas_ant) / receitas_ant * 100
        insights.append(Insight("ok", "✅", "Receitas em crescimento",
            f"Cresceram {crescimento:.0f}% vs anterior. Continue assim!", 4))

    if pct_mei < 40:
        insights.append(Insight("ok", "✅", "Limite MEI sob controle",
            f"Apenas {pct_mei:.0f}% do limite anual usado. Espaço de sobra.", 4))

    # Máximo 6 insights, priorizados
    return sorted(insights, key=lambda x: x.prioridade)[:6]
