"""
Guido — Blog Handler
Recebe posts do projeto Marketing_guido (Opensquad) e publica direto no
blog do site (chamaoguido.com/blog).

Endpoints:
  POST /blog/publicar      → recebe markdown + frontmatter, publica
  GET  /blog/posts         → lista posts publicados (pra blog.html)
  GET  /blog/posts/{slug}  → post individual (pra blog-post.html)

Autenticação:
  POST exige header X-API-Key (BLOG_API_KEY do .env). GETs são públicos.

Fluxo do agente:
  1. Marketing_guido roda squad de 11 passos, gera blog-post.md
  2. Passo 12 (publicar_blog.py) lê o .md, parseia frontmatter, POSTa pra cá
  3. Backend converte markdown → HTML, salva no banco
  4. blog.html lista todos via GET /blog/posts
  5. blog-post.html?slug=xxx renderiza individual via GET /blog/posts/{slug}
"""
import os
import json
import re
from datetime import datetime
from typing import Optional

import markdown as md_lib
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

import models
import database

router = APIRouter(prefix="/blog", tags=["blog"])

BLOG_API_KEY = os.getenv("BLOG_API_KEY", "")


# ==========================================
# HELPERS
# ==========================================

def _slugify(texto: str) -> str:
    """Gera slug URL-friendly a partir de um título.
    Remove acentos, troca espaços por hífen, deixa minúsculo.
    """
    import unicodedata
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    s = re.sub(r"-+", "-", s)
    return s[:120] or "post"


def _md_to_html(conteudo_md: str) -> str:
    """Converte markdown pra HTML usando python-markdown com extensões úteis.
    - extra: tabelas, fenced code, footnotes
    - sane_lists: listas que não viram itálico marreta
    - smarty: aspas curvas, travessões
    """
    return md_lib.markdown(
        conteudo_md,
        extensions=["extra", "sane_lists", "smarty", "toc"],
        output_format="html5",
    )


def _validar_api_key(x_api_key: Optional[str]):
    if not BLOG_API_KEY:
        raise HTTPException(status_code=503, detail="Blog desabilitado: BLOG_API_KEY não configurada no servidor")
    if not x_api_key or x_api_key != BLOG_API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida")


# ==========================================
# SCHEMAS
# ==========================================

class PostInput(BaseModel):
    title: str
    conteudo_md: str
    slug: Optional[str] = None  # se não vier, gera do title
    meta_description: Optional[str] = None
    categoria: Optional[str] = None
    keywords: Optional[str] = None  # CSV
    autor: Optional[str] = "Equipe Guido"
    frontmatter: Optional[dict] = None  # YAML original serializado


# ==========================================
# ENDPOINTS
# ==========================================

@router.post("/publicar")
def publicar_post(
    payload: PostInput,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(database.get_db),
):
    """Recebe um post do Marketing_guido e publica no blog.

    Se já existir post com o mesmo slug, atualiza (upsert).
    """
    _validar_api_key(x_api_key)

    if not payload.title.strip() or not payload.conteudo_md.strip():
        raise HTTPException(status_code=400, detail="title e conteudo_md são obrigatórios")

    slug = (payload.slug or _slugify(payload.title)).strip()
    conteudo_html = _md_to_html(payload.conteudo_md)

    existente = db.query(models.BlogPost).filter(models.BlogPost.slug == slug).first()

    if existente:
        existente.title = payload.title
        existente.meta_description = payload.meta_description
        existente.categoria = payload.categoria
        existente.keywords = payload.keywords
        existente.autor = payload.autor or "Equipe Guido"
        existente.conteudo_md = payload.conteudo_md
        existente.conteudo_html = conteudo_html
        existente.frontmatter_json = json.dumps(payload.frontmatter, ensure_ascii=False) if payload.frontmatter else None
        existente.publicado_em = datetime.utcnow()
        existente.status = "publicado"
        post = existente
        acao = "atualizado"
    else:
        post = models.BlogPost(
            slug=slug,
            title=payload.title,
            meta_description=payload.meta_description,
            categoria=payload.categoria,
            keywords=payload.keywords,
            autor=payload.autor or "Equipe Guido",
            conteudo_md=payload.conteudo_md,
            conteudo_html=conteudo_html,
            frontmatter_json=json.dumps(payload.frontmatter, ensure_ascii=False) if payload.frontmatter else None,
            publicado_em=datetime.utcnow(),
            status="publicado",
        )
        db.add(post)
        acao = "criado"

    db.commit()
    db.refresh(post)

    return {
        "ok": True,
        "acao": acao,
        "id": post.id,
        "slug": post.slug,
        "url": f"/blog/{post.slug}",
    }


@router.get("/posts")
def listar_posts(db: Session = Depends(database.get_db), limit: int = 50):
    """Lista posts publicados em ordem decrescente de publicação.
    Resposta enxuta — só metadados, sem conteúdo (pra economizar payload na lista).
    """
    posts = (
        db.query(models.BlogPost)
        .filter(models.BlogPost.status == "publicado")
        .order_by(models.BlogPost.publicado_em.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "slug": p.slug,
            "title": p.title,
            "meta_description": p.meta_description,
            "categoria": p.categoria,
            "keywords": p.keywords.split(",") if p.keywords else [],
            "autor": p.autor,
            "publicado_em": p.publicado_em.isoformat() if p.publicado_em else None,
        }
        for p in posts
    ]


@router.get("/posts/{slug}")
def buscar_post(slug: str, db: Session = Depends(database.get_db)):
    """Retorna o post individual pra renderização no blog-post.html."""
    post = (
        db.query(models.BlogPost)
        .filter(models.BlogPost.slug == slug, models.BlogPost.status == "publicado")
        .first()
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post não encontrado")

    return {
        "slug": post.slug,
        "title": post.title,
        "meta_description": post.meta_description,
        "categoria": post.categoria,
        "keywords": post.keywords.split(",") if post.keywords else [],
        "autor": post.autor,
        "conteudo_html": post.conteudo_html,
        "publicado_em": post.publicado_em.isoformat() if post.publicado_em else None,
    }
