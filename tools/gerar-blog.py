#!/usr/bin/env python3
"""
Gera o blog estático a partir dos artigos em blog/posts/*.md e atualiza o sitemap.xml.

Uso (a partir da raiz do repositório):
    python3 tools/gerar-blog.py

Cada artigo é um .md com cabeçalho simples:
    ---
    title: Título que aparece no Google (até ~60 caracteres)
    h1: Título grande dentro do artigo (opcional, padrão = title)
    slug: endereco-do-artigo
    description: Resumo para o Google (até ~155 caracteres)
    date: 2026-10-05
    updated: 2026-10-05   (opcional)
    resposta: Resposta direta de 2 ou 3 frases, mostrada em destaque no topo (opcional)
    ---
    Texto em Markdown...

Citações (linhas começando com ">") viram balões de WhatsApp com botão "Copiar".
Uma seção "## Perguntas frequentes" com perguntas em "###" vira também o schema FAQPage.
A página Quem somos vem de blog/sobre.md.
"""
import html
import json
import re
from datetime import date
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://salaosemmensalidade.netlify.app"
POSTS = ROOT / "blog" / "posts"
BRAND = "Salão Sem Mensalidade"

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def data_br(iso):
    a, m, d = iso.split("-")
    return f"{int(d)} de {MESES[int(m) - 1]} de {a}"


def ler_post(p):
    txt = p.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n(.*)", txt, re.S)
    meta = {}
    for linha in m.group(1).splitlines():
        if ":" in linha:
            k, v = linha.split(":", 1)
            meta[k.strip()] = v.strip()
    meta.setdefault("h1", meta["title"])
    meta.setdefault("updated", meta["date"])
    meta["md"] = m.group(2).strip()
    return meta


def extrair_faq(md):
    """Lê a seção '## Perguntas frequentes' (perguntas em ###) para o schema FAQPage."""
    m = re.search(r"^## Perguntas frequentes.*?\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    if not m:
        return []
    itens = []
    for bloco in re.split(r"^### ", m.group(1), flags=re.M)[1:]:
        q, _, a = bloco.partition("\n")
        a = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", a)   # links viram texto
        a = re.sub(r"[*_>`]", "", a)
        a = re.sub(r"\s+", " ", a).strip()
        if q.strip() and a:
            itens.append({"@type": "Question", "name": q.strip(),
                          "acceptedAnswer": {"@type": "Answer", "text": a}})
    return itens


def render_md(md):
    # linha em branco entre duas citações separa mensagens diferentes
    # (para uma mensagem com vários parágrafos, use ">" sozinho na linha do meio)
    md = re.sub(r"(^>.*\n)\n(?=>)", r"\1\n<!-- msg -->\n\n", md, flags=re.M)
    h = markdown.markdown(md, extensions=["tables", "sane_lists"])
    # balões de mensagem com botão copiar
    def balao(m):
        return ('<figure class="msg"><div class="msg-txt">' + m.group(1).strip() +
                '</div><button type="button" class="copiar" aria-label="Copiar mensagem">Copiar</button></figure>')
    h = re.sub(r"<blockquote>(.*?)</blockquote>", balao, h, flags=re.S)
    h = h.replace("<table>", '<div class="tabela"><table>').replace("</table>", "</table></div>")
    return h


CSS = """
:root { --bg:#FBF3E8; --bg2:#FDF9F2; --card:#fff; --ink:#1B1F3B; --muted:#5E6076; --soft:#8A8598;
  --line:#F1E4D6; --acc:#C0234A; --acc2:#A81742; --pink:#F9D9E1; --wa:#DCF8C6; }
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin:0; background:var(--bg); color:var(--ink); font-family: Manrope, system-ui, sans-serif;
  -webkit-font-smoothing: antialiased; line-height:1.7; }
a { color: var(--acc2); }
.wrap { max-width: 760px; margin: 0 auto; padding: 0 20px; }
.top { padding: 18px 0; border-bottom: 1px solid var(--line); background: var(--bg2); }
.top .wrap { display:flex; align-items:center; justify-content:space-between; gap:12px; max-width:1080px; }
.logo { display:flex; align-items:center; gap:10px; text-decoration:none; color:var(--ink); font-weight:800; font-size:15px; }
.logo i { display:inline-flex; width:34px; height:34px; border-radius:10px; background:var(--acc); color:#fff;
  font: 400 22px/34px 'DM Serif Display', Georgia, serif; justify-content:center; font-style:normal; }
.top nav a { font-size:14px; font-weight:700; text-decoration:none; margin-left:16px; }
.top nav a.cta { white-space:nowrap; background: linear-gradient(135deg,#D62F58,#A81742); color:#fff; padding:9px 16px; border-radius:999px; }
.crumbs { font-size:13px; color:var(--soft); margin: 28px 0 0; }
.crumbs a { color:var(--soft); }
h1, h2, h3 { font-family: 'DM Serif Display', Georgia, serif; font-weight:400; line-height:1.18; letter-spacing:-.005em; }
h1 { font-size: clamp(32px, 6vw, 48px); margin: 14px 0 14px; }
h2 { font-size: clamp(25px, 4vw, 32px); margin: 44px 0 12px; }
h3 { font-size: 22px; margin: 30px 0 8px; }
.meta { font-size: 14px; color: var(--soft); margin: 0 0 26px; }
.lead { font-size: 19px; color: var(--muted); }
article p, article li { font-size: 17px; }
article ul, article ol { padding-left: 22px; }
article li { margin: 6px 0; }
article strong { color: var(--ink); }
.msg { position: relative; margin: 16px 0; background: var(--wa); border-radius: 4px 16px 16px 16px;
  padding: 14px 16px 44px; box-shadow: 0 10px 24px -20px rgba(27,31,59,.6); }
.msg-txt p { margin: 0 0 8px; font-size: 16px; line-height: 1.6; }
.msg-txt p:last-child { margin: 0; }
.copiar { position:absolute; right:10px; bottom:10px; border:0; background:#fff; color:var(--acc2); font: 700 13px Manrope, sans-serif;
  padding: 6px 12px; border-radius: 999px; cursor:pointer; box-shadow: 0 2px 6px rgba(0,0,0,.08); }
.copiar.ok { background: var(--acc); color:#fff; }
.tabela { overflow-x:auto; margin: 18px 0; border-radius: 14px; border:1px solid var(--line); background:#fff; }
table { border-collapse: collapse; width:100%; font-size:15px; }
th, td { text-align:left; padding: 11px 14px; border-bottom:1px solid var(--line); vertical-align: top; }
th { background: var(--pink); color: var(--acc2); font-weight:800; }
tr:last-child td { border-bottom:0; }
.resposta { margin: 6px 0 30px; padding: 20px 22px; border-radius: 18px; background: #fff;
  border: 1px solid var(--line); border-left: 5px solid var(--acc); }
.resposta-tit { margin: 0 0 6px !important; font-size: 12px !important; font-weight: 800; letter-spacing: .08em;
  text-transform: uppercase; color: var(--acc2); }
.resposta p { margin: 0; font-size: 17px; line-height: 1.65; }
.cta-box { margin: 48px 0 20px; padding: 30px 26px; border-radius: 24px; color:#fff; text-align:center;
  background: linear-gradient(135deg, #C0234A, #8E1738); }
.cta-box h2 { color:#fff; margin: 0 0 10px; font-size: clamp(24px, 4vw, 30px); }
.cta-box p { color: rgba(255,255,255,.88); margin: 0 auto 22px; max-width: 30em; font-size:16px; }
.cta-box a { display:inline-block; background:#fff; color:var(--acc2); text-decoration:none; font-weight:800; letter-spacing:.06em;
  text-transform: uppercase; font-size:14px; padding: 16px 26px; border-radius:999px; }
.rel { margin: 50px 0 10px; }
.rel h2 { font-size: 26px; }
.cards { display:grid; gap:14px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
.card { display:block; background: var(--card); border:1px solid var(--line); border-radius: 18px; padding: 20px 20px 22px;
  text-decoration:none; color: var(--ink); transition: transform .2s, border-color .2s; }
.card:hover { transform: translateY(-3px); border-color:#E9BFCB; }
.card h3 { margin: 0 0 8px; font-size: 21px; }
.card p { margin: 0; font-size: 15px; color: var(--muted); line-height: 1.55; }
.hero-blog { padding: 44px 0 10px; }
.hero-blog p { font-size: 18px; color: var(--muted); max-width: 34em; }
.lista { display:grid; gap:16px; margin: 26px 0 40px; }
footer { margin-top: 50px; padding: 30px 0; border-top: 1px solid var(--line); background: var(--bg2); text-align:center; font-size: 13px; color: var(--soft); }
@media (max-width: 560px) { .top nav a:not(.cta) { display:none; } .top nav a.cta { font-size:13px; padding:8px 13px; margin-left:0; } .logo { font-size:14px; line-height:1.25; } article p, article li { font-size: 16.5px; } }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
"""

JS = """<script>
document.addEventListener('click', function (e) {
  var b = e.target.closest('.copiar'); if (!b) return;
  var t = b.parentNode.querySelector('.msg-txt').innerText.trim();
  function ok() { b.textContent = 'Copiado!'; b.classList.add('ok'); setTimeout(function(){ b.textContent='Copiar'; b.classList.remove('ok'); }, 1800); }
  if (navigator.clipboard) { navigator.clipboard.writeText(t).then(ok, function(){}); }
  else { var a = document.createElement('textarea'); a.value = t; document.body.appendChild(a); a.select();
    try { document.execCommand('copy'); ok(); } catch (x) {} document.body.removeChild(a); }
});
</script>"""


def pagina(titulo, descricao, url, corpo, jsonld, prefixo, og_type="article"):
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(titulo)}</title>
<meta name="description" content="{html.escape(descricao)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="theme-color" content="#C0234A">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='24' fill='%23C0234A'/%3E%3Ctext x='50' y='72' text-anchor='middle' font-family='Georgia,serif' font-size='64' fill='%23fff'%3ES%3C/text%3E%3C/svg%3E">
<meta property="og:type" content="{og_type}">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:title" content="{html.escape(titulo)}">
<meta property="og:description" content="{html.escape(descricao)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/assets/img/og-image.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="{prefixo}assets/fonts.css">
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>
</head>
<body>
<header class="top"><div class="wrap">
  <a class="logo" href="{prefixo}"><i>S</i>{BRAND}</a>
  <nav><a href="{prefixo}blog/">Blog</a><a href="{prefixo}sobre/">Quem somos</a><a class="cta" href="{prefixo}">Conhecer o sistema</a></nav>
</div></header>
{corpo}
<footer><div class="wrap">
  <p style="margin:0 0 6px;"><a href="{prefixo}">Sistema para salão pelo celular, sem mensalidade</a> · <a href="{prefixo}blog/">Blog</a> · <a href="{prefixo}sobre/">Quem somos</a></p>
  <p style="margin:0;">© {date.today().year} {BRAND}. Todos os direitos reservados.</p>
</div></footer>
{JS}
</body>
</html>
"""


CTA = """<aside class="cta-box">
  <h2>Organize suas clientes pelo celular</h2>
  <p>Cadastro em segundos, retorno que aparece sozinho na sua Google Agenda e alerta de aniversário. A gente configura tudo pra você. R$147 uma vez, sem mensalidade.</p>
  <a href="../../">Conhecer o sistema</a>
</aside>"""


def main():
    posts = [ler_post(p) for p in sorted(POSTS.glob("*.md"))]
    posts.sort(key=lambda m: m["date"], reverse=True)  # mais novos primeiro; mesma data mantém a ordem dos arquivos
    org = {"@type": "Organization", "name": BRAND, "url": SITE + "/",
           "description": "Sistema simples para salão de beleza usado pelo celular, com pagamento único.",
           "founder": {"@type": "Person", "name": "Wesley"},
           "parentOrganization": {"@type": "Organization", "name": "Snipes Digital"},
           "address": {"@type": "PostalAddress", "addressLocality": "Belo Horizonte", "addressRegion": "MG", "addressCountry": "BR"}}

    for i, p in enumerate(posts):
        url = f"{SITE}/blog/{p['slug']}/"
        outros = [posts[(i + k) % len(posts)] for k in range(1, min(4, len(posts)))]
        rel = "".join(f'<a class="card" href="../{q["slug"]}/"><h3>{html.escape(q["h1"])}</h3><p>{html.escape(q["description"])}</p></a>' for q in outros)
        conteudo = render_md(p["md"])
        resposta = ""
        if p.get("resposta"):
            resposta = f'<div class="resposta"><p class="resposta-tit">Resposta rápida</p><p>{html.escape(p["resposta"])}</p></div>'
        faq = extrair_faq(p["md"])
        corpo = f"""<main class="wrap">
<nav class="crumbs" aria-label="Você está em"><a href="../../">Início</a> › <a href="../">Blog</a></nav>
<article>
<h1>{html.escape(p['h1'])}</h1>
<p class="meta">Por <a href="../../sobre/">Equipe {BRAND}</a> · {data_br(p['date'])}</p>
{resposta}
{conteudo}
{CTA}
</article>
<section class="rel"><h2>Leia também</h2><div class="cards">{rel}</div></section>
</main>"""
        ld = {"@context": "https://schema.org", "@graph": [
            {"@type": "BlogPosting", "headline": p["h1"], "description": p["description"],
             "datePublished": p["date"], "dateModified": p["updated"], "inLanguage": "pt-BR",
             "mainEntityOfPage": url, "image": f"{SITE}/assets/img/og-image.jpg",
             "author": org, "publisher": org},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Início", "item": SITE + "/"},
                {"@type": "ListItem", "position": 2, "name": "Blog", "item": SITE + "/blog/"},
                {"@type": "ListItem", "position": 3, "name": p["h1"], "item": url}]}]}
        if faq:
            ld["@graph"].append({"@type": "FAQPage", "mainEntity": faq})
        out = ROOT / "blog" / p["slug"]
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(pagina(p["title"], p["description"], url, corpo, ld, "../../"), encoding="utf-8")

    # índice do blog
    itens = "".join(f'<a class="card" href="{p["slug"]}/"><h3>{html.escape(p["h1"])}</h3><p>{html.escape(p["description"])}</p></a>' for p in posts)
    corpo = f"""<main class="wrap">
<section class="hero-blog">
<h1>Blog para donas de salão</h1>
<p>Mensagens prontas para WhatsApp, ideias de promoção e jeitos simples de fazer suas clientes voltarem mais vezes.</p>
</section>
<div class="lista">{itens}</div>
</main>"""
    ld = {"@context": "https://schema.org", "@type": "Blog", "name": f"Blog {BRAND}", "url": SITE + "/blog/",
          "inLanguage": "pt-BR", "publisher": org}
    (ROOT / "blog" / "index.html").write_text(
        pagina(f"Blog para donas de salão | {BRAND}",
               "Mensagens prontas para WhatsApp, ideias de promoção e dicas simples para fazer as clientes do salão voltarem mais vezes.",
               SITE + "/blog/", corpo, ld, "../", og_type="website"), encoding="utf-8")

    # página Quem somos
    sobre_md = (ROOT / "blog" / "sobre.md").read_text(encoding="utf-8")
    corpo = f"""<main class="wrap">
<nav class="crumbs" aria-label="Você está em"><a href="../">Início</a></nav>
<article>
{render_md(sobre_md)}
{CTA.replace('href="../../"', 'href="../"')}
</article>
</main>"""
    ld = {"@context": "https://schema.org", "@type": "AboutPage", "url": SITE + "/sobre/", "inLanguage": "pt-BR",
          "about": org}
    (ROOT / "sobre").mkdir(exist_ok=True)
    (ROOT / "sobre" / "index.html").write_text(
        pagina(f"Quem somos | {BRAND}",
               "Conheça o Salão Sem Mensalidade: um sistema simples para donas de salão organizarem as clientes pelo celular, com pagamento único e configuração feita pela nossa equipe.",
               SITE + "/sobre/", corpo, ld, "../", og_type="website"), encoding="utf-8")

    # sitemap
    home_mod = date.fromtimestamp((ROOT / "index.html").stat().st_mtime).isoformat()
    urls = [(SITE + "/", home_mod), (SITE + "/blog/", posts[0]["updated"] if posts else home_mod)]
    urls += [(f"{SITE}/blog/{p['slug']}/", p["updated"]) for p in posts]
    urls.append((SITE + "/sobre/", date.fromtimestamp((ROOT / "blog" / "sobre.md").stat().st_mtime).isoformat()))
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"  <url><loc>{u}</loc><lastmod>{d}</lastmod></url>\n" for u, d in urls) + "</urlset>\n",
        encoding="utf-8")
    print(f"Blog: {len(posts)} artigo(s), sitemap com {len(urls)} URLs.")


if __name__ == "__main__":
    main()
