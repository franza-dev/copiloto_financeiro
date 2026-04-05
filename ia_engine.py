import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

# Carrega as variáveis do .env
load_dotenv()

# Puxa a chave lá do .env em vez de deixar solta no código
CHAVE_API = os.getenv("GOOGLE_API_KEY")

def configurar_ia():
    genai.configure(api_key=CHAVE_API)
    return genai.GenerativeModel('gemini-2.5-flash')

# --- PROMPT MESTRE (A REGRA DE NEGÓCIO) ---
PROMPT_SISTEMA = """
Você é um assistente financeiro de alta precisão. Sua tarefa é converter frases ou áudios em dados JSON.

IDENTIFIQUE A INTENÇÃO DO USUÁRIO:
1. DEFINIR LIMITE/TETO: Se o usuário quer estabelecer um valor máximo para uma categoria (ex: "meu teto de Uber é 500", "limite de 200 para lazer").
   - "natureza": "config_limite"
   - "categoria": Nome da categoria (ex: "Uber", "Lazer")
   - "valor": O valor do limite (float positivo)
   - Preencha os demais campos como "" ou "PF".

2. LANÇAMENTO DE TRANSAÇÃO: Se o usuário relata um gasto ou ganho real.
   - "natureza": "saida" (pagamentos, gastos, transferir para fora) ou "entrada" (recebimentos, pix recebido).
   - "valor": O número (float sempre positivo).
   - "descricao": O que foi feito.
   - "categoria": Classificação (ex: Alimentação, Transporte).
   - "tipo": "PF" ou "PJ" (padrão "PF" se não houver indicação).
   - "banco": Nome do banco citado (ex: Nubank, Asaas).

REGRAS DE OURO:
- Responda APENAS o JSON puro.
- NUNCA use aspas triplas (```json).
- Se não entender algo, coloque "A Classificar" na categoria.
"""

def processar_texto_ia(texto):
    model = configurar_ia()
    try:
        response = model.generate_content(f"{PROMPT_SISTEMA}\n\nFrase do usuário: '{texto}'")
        texto_limpo = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto_limpo)
    except Exception as e:
        print(f"Erro Texto IA: {e}")
        return {"descricao": "Erro", "valor": 0, "natureza": "saida", "categoria": "Erro"}

def processar_audio_ia(caminho_audio):
    model = configurar_ia()
    try:
        # 1. Upload do arquivo para o servidor do Google
        arquivo_gemini = genai.upload_file(caminho_audio)
        
        # 2. Processamento multimodal
        response = model.generate_content([PROMPT_SISTEMA, arquivo_gemini])
        
        # 3. Limpeza do arquivo no Google
        arquivo_gemini.delete()
        
        texto_limpo = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto_limpo)
    except Exception as e:
        print(f"Erro Áudio IA: {e}")
        return {"descricao": "Erro de Áudio", "valor": 0, "natureza": "saida", "categoria": "Erro"}