import os
import google.generativeai as genai
import json
import re # Vamos usar busca por padrão
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

PROMPT_SISTEMA = """
Você é um assistente financeiro. Extraia: valor (float), descricao (string), tipo (PF ou PJ), categoria (string).
Responda APENAS o JSON.
"""

def processar_texto_com_gemini(texto_usuario):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        resposta = model.generate_content(f"{PROMPT_SISTEMA}\nFrase: '{texto_usuario}'")
        
        # Limpeza blindada: busca o que está entre chaves { }
        match = re.search(r'\{.*\}', resposta.text, re.DOTALL)
        if match:
            texto_json = match.group()
            return json.loads(texto_json)
        
        raise ValueError("JSON não encontrado na resposta")
    except Exception as e:
        print(f"ERRO NA IA: {e}") # Isso vai aparecer no seu terminal!
        return {"valor": 0, "descricao": "Erro na IA", "tipo": "PF", "categoria": "Erro"}