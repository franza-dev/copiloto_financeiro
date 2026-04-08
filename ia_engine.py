from google import genai
from google.genai import types
import json
import os
from dotenv import load_dotenv

load_dotenv()

CHAVE_API = os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=CHAVE_API)

# ==========================================
# PROMPT DO GUIDO
# ==========================================
# O prompt é montado dinamicamente a cada chamada porque injeta o contexto
# das contas reais do usuário. Isso permite que o Gemini escolha a conta
# certa (ex: "Nubank Black cartão" vs "Nubank Corrente") em vez de retornar
# uma string fuzzy que o backend precisaria adivinhar.

_PROMPT_BASE = """Você é o Guido, assistente financeiro de MEIs. Sua tarefa é converter frases em JSON estruturado.

IDENTIFIQUE A INTENÇÃO:

1. DEFINIR TETO/LIMITE: quando o usuário quer estabelecer um valor máximo para uma categoria.
   Exemplos: "meu teto de uber é 500", "quero gastar no máximo 200 em lazer"
   Retorne:
     "natureza": "config_limite"
     "categoria": nome da categoria
     "valor": o valor do teto (float positivo)
     "tipo": "PF" (padrão)
     "descricao": ""
     "conta_id": null

2. LANÇAMENTO DE TRANSAÇÃO: quando o usuário relata um gasto ou recebimento real.
   Retorne:
     "natureza": "saida" (pagamentos, gastos) ou "entrada" (recebimentos)
     "valor": número em float, SEMPRE POSITIVO (o sinal é tratado depois)
     "descricao": descrição curta e objetiva do que aconteceu
     "categoria": classificação do gasto (ex: Alimentação, Transporte, Material de Escritório)
     "tipo": "PF" (dinheiro da casa/pessoal) ou "PJ" (dinheiro do negócio)
     "conta_id": id da conta escolhida da lista abaixo (ou null se não souber)

COMO ESCOLHER A CONTA:
- Procure pelo banco/nome citado na frase ("no Nubank", "do Itaú", "no cartão Black")
- Palavras-chave de CARTÃO DE CRÉDITO: "crédito", "cartão", "fatura", nome específico do cartão
- Palavras-chave de CONTA CORRENTE: "pix", "débito", "transferência", "dinheiro", "boleto"
- Se a frase não dá pistas do banco mas fala em "crédito" → escolha qualquer cartão do tipo (PF ou PJ) correspondente
- Se a frase é sobre trabalho/empresa/cliente/fornecedor → prefira contas PJ
- Se a frase é sobre casa/pessoal/família → prefira contas PF
- Em caso de dúvida, deixe conta_id como null (vai pra quarentena pro usuário revisar)

REGRAS DE OURO:
- Responda APENAS o JSON puro, uma única linha ou formatado, sem explicações.
- NUNCA use aspas triplas (```json) nem texto antes/depois do JSON.
- Se não entender a frase, use categoria "A Classificar" e conta_id null.

EXEMPLOS:

Frase: "gastei 45 no uber pra reunião com cliente"
JSON: {"natureza":"saida","valor":45.0,"descricao":"Uber para reunião com cliente","categoria":"Transporte","tipo":"PJ","conta_id":null}

Frase: "comprei 150 de material de escritório no crédito do Nubank"
(supondo que existe conta id=2 "Nubank Black" modalidade cartao_credito PJ)
JSON: {"natureza":"saida","valor":150.0,"descricao":"Material de escritório","categoria":"Material de Escritório","tipo":"PJ","conta_id":2}

Frase: "paguei 80 de mercado no pix do Nubank"
(supondo que existe conta id=1 "Nubank Corrente" modalidade corrente PF)
JSON: {"natureza":"saida","valor":80.0,"descricao":"Mercado","categoria":"Alimentação","tipo":"PF","conta_id":1}

Frase: "cliente me pagou 500 reais por pix"
JSON: {"natureza":"entrada","valor":500.0,"descricao":"Pagamento de cliente","categoria":"Vendas / Receitas","tipo":"PJ","conta_id":null}

Frase: "meu teto de alimentação é 800"
JSON: {"natureza":"config_limite","categoria":"Alimentação","valor":800.0,"tipo":"PF","descricao":"","conta_id":null}
"""


def _montar_contexto_contas(contas):
    """Formata a lista de contas do usuário em texto legível pra injeção no prompt.

    Args:
        contas: lista de dicts com chaves id, nome, banco, tipo, modalidade.
                Pode ser None ou vazia.

    Returns:
        String formatada pra colar no prompt, ou aviso se sem contas.
    """
    if not contas:
        return "CONTAS DO USUÁRIO: (nenhuma conta cadastrada — sempre retorne conta_id: null)"

    linhas = ["CONTAS DISPONÍVEIS DO USUÁRIO (escolha uma delas pelo id):"]
    for c in contas:
        modalidade_label = "cartão de crédito" if c.get("modalidade") == "cartao_credito" else "conta corrente"
        tipo_label = "Negócio/PJ" if c.get("tipo") == "PJ" else "Casa/PF"
        linhas.append(
            f'  - id={c["id"]}: "{c["nome"]}" no {c["banco"]} ({modalidade_label}, {tipo_label})'
        )
    return "\n".join(linhas)


def _montar_prompt(contas):
    """Monta o prompt final juntando o prompt base + contexto de contas."""
    return f"{_PROMPT_BASE}\n\n{_montar_contexto_contas(contas)}\n"


def _resposta_fallback(motivo: str) -> dict:
    """Resposta padrão quando a IA falha — vai sempre pra quarentena."""
    return {
        "descricao": f"Erro: {motivo}",
        "valor": 0,
        "natureza": "saida",
        "categoria": "A Classificar",
        "tipo": "PF",
        "conta_id": None,
    }


def processar_texto_ia(texto, contas=None):
    """Interpreta uma frase do usuário e retorna um dict estruturado.

    Args:
        texto: a frase do usuário.
        contas: lista de contas do usuário pra ancorar a escolha (ver
                _montar_contexto_contas). Se None, a IA retorna conta_id null.
    """
    try:
        prompt_completo = _montar_prompt(contas)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{prompt_completo}\n\nFrase do usuário: '{texto}'"
        )
        texto_limpo = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto_limpo)
    except Exception as e:
        print(f"Erro Texto IA: {e}")
        return _resposta_fallback("falha ao interpretar texto")


def processar_audio_ia(caminho_audio, contas=None):
    """Interpreta um áudio do usuário e retorna um dict estruturado.

    Args:
        caminho_audio: path local do arquivo de áudio.
        contas: lista de contas do usuário pra ancorar a escolha.
    """
    try:
        prompt_completo = _montar_prompt(contas)

        # 1. Upload do arquivo para o servidor do Google
        # Detecta mime type pelo nome do arquivo
        mime_map = {".ogg": "audio/ogg", ".oga": "audio/ogg", ".mp4": "audio/mp4",
                    ".m4a": "audio/mp4", ".wav": "audio/wav", ".mp3": "audio/mpeg",
                    ".webm": "audio/webm", ".opus": "audio/ogg"}
        ext = os.path.splitext(caminho_audio)[1].lower()
        mime = mime_map.get(ext, "audio/ogg")

        with open(caminho_audio, "rb") as f:
            arquivo_gemini = client.files.upload(
                file=f,
                config=types.UploadFileConfig(
                    display_name=caminho_audio,
                    mime_type=mime,
                )
            )

        # 2. Processamento multimodal
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt_completo, arquivo_gemini]
        )

        # 3. Limpeza do arquivo no Google
        try:
            client.files.delete(name=arquivo_gemini.name)
        except Exception:
            pass  # não é crítico se falhar a limpeza

        texto_limpo = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto_limpo)
    except Exception as e:
        print(f"Erro Áudio IA: {e}")
        return _resposta_fallback("falha ao interpretar áudio")
