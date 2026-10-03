#!/usr/bin/env python3
"""
Converte o HTML exportado do editor Design (formato "Bundled Page", que só
monta a página via JavaScript) em uma página estática otimizada para SEO.

Uso (a partir da raiz do repositório):
    python3 tools/design-para-seo.py caminho/do/export.html

O que ele faz:
  - extrai o conteúdo real da página do pacote e grava como HTML estático
    (o Google lê o texto direto, sem depender de JavaScript)
  - injeta o <head> de SEO de seo/head.html (title, description, schema...)
  - insere a seção de perguntas frequentes de seo/faq.html antes da oferta final
  - salva fontes em assets/fonts/ e a foto em WebP leve em assets/img/
  - troca os efeitos de hover do editor por CSS puro
Gera: index.html, assets/, e mantém robots.txt e sitemap.xml.
"""
import base64, gzip, io, json, re, sys, zlib
from datetime import date
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SEO = ROOT / "seo"


def bloco(src, nome):
    m = re.search(r'<script type="__bundler/' + nome + r'">(.*?)</script>', src, re.S)
    if not m:
        sys.exit(f"Arquivo não parece um export do Design (sem bloco {nome}).")
    return json.loads(m.group(1).strip())


def decodificar(item):
    raw = base64.b64decode(item["data"])
    if item.get("compressed"):
        for fn in (gzip.decompress, zlib.decompress, lambda b: zlib.decompress(b, -15)):
            try:
                return fn(raw)
            except Exception:
                pass
    return raw


def main(export_path):
    src = Path(export_path).read_text(encoding="utf-8")
    manifest = bloco(src, "manifest")
    tpl = bloco(src, "template")

    fonts_dir = ROOT / "assets" / "fonts"
    img_dir = ROOT / "assets" / "img"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    # ---- separa CSS (fontes + estilos) do corpo
    styles = re.findall(r"<style>(.*?)</style>", tpl, re.S)
    body = re.search(r"<helmet>.*?</helmet>(.*)</x-dc>", tpl, re.S).group(1).strip()

    css = "\n".join(styles)
    # fontes: grava arquivos e reescreve url
    for uid in set(re.findall(r'url\("([0-9a-f-]{36})"\)', css)):
        item = manifest[uid]
        (fonts_dir / f"{uid[:8]}.woff2").write_bytes(decodificar(item))
        css = css.replace(f'url("{uid}")', f'url("assets/fonts/{uid[:8]}.woff2")')

    # ---- imagens: WebP leve + srcset; a primeira (hero) vira também og-image
    imgs = re.findall(r'<img src="([0-9a-f-]{36})"([^>]*)>', body)
    for i, (uid, attrs) in enumerate(imgs):
        im = Image.open(io.BytesIO(decodificar(manifest[uid]))).convert("RGB")
        nome = "salao-de-beleza" if i == 0 else f"imagem-{i+1}"
        larguras = [800, 1400]
        for w in larguras:
            h = round(im.height * w / im.width)
            im.resize((w, h), Image.LANCZOS).save(img_dir / f"{nome}-{w}.webp", "WEBP", quality=78, method=6)
        if i == 0:
            og = im.copy()
            alvo = 1200 / 630
            if og.width / og.height > alvo:
                nw = round(og.height * alvo); x = (og.width - nw) // 2
                og = og.crop((x, 0, x + nw, og.height))
            og.resize((1200, 630), Image.LANCZOS).save(img_dir / "og-image.jpg", "JPEG", quality=82, optimize=True)
        h800 = round(im.height * 800 / im.width)
        extra = ' fetchpriority="high"' if i == 0 else ' loading="lazy"'
        novo = (f'<img src="assets/img/{nome}-800.webp" '
                f'srcset="assets/img/{nome}-800.webp 800w, assets/img/{nome}-1400.webp 1400w" '
                f'sizes="(max-width: 700px) 100vw, 560px" width="800" height="{h800}" '
                f'decoding="async"{extra}{attrs}>')
        body = body.replace(f'<img src="{uid}"{attrs}>', novo, 1)

    # ---- hover do editor -> classes CSS
    hover_css, n = [], 0
    def troca_hover(m):
        nonlocal n
        n += 1
        regras = ";".join(r.strip() + " !important" for r in m.group(1).split(";") if r.strip())
        hover_css.append(f".hv{n}:hover{{{regras}}}")
        return f'class="hv hv{n}"'
    body = re.sub(r'style-hover="([^"]*)"', troca_hover, body)
    body = body.replace("sc-camel-view-box=", "viewBox=")
    # ícones decorativos ficam fora da leitura de tela
    body = re.sub(r"<svg (?![^>]*aria-hidden)", '<svg aria-hidden="true" focusable="false" ', body)

    # ---- FAQ antes da oferta final
    faq = (SEO / "faq.html").read_text(encoding="utf-8").strip()
    if '<section id="oferta"' in body:
        body = body.replace('<section id="oferta"', faq + '\n\n  <section id="oferta"', 1)
    else:
        body = body.replace("<footer", faq + "\n\n  <footer", 1)
    # rodapé com o conteúdo principal separado
    body = body.replace("<footer", "</main>\n  <footer", 1)
    body = re.sub(r'(<div style="font-family: Manrope[^"]*">)', r'\1\n<main>', body, count=1)

    extra_css = """
  .hv { transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease; }
  img { max-width: 100%; }
  details summary { cursor: pointer; list-style: none; }
  details summary::-webkit-details-marker { display: none; }
  details[open] .faq-ic { transform: rotate(45deg); }
  @media (max-width: 600px) { [style*="left: -34px"] { left: 12px !important; bottom: 14px !important; } }
  @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
"""
    head = (SEO / "head.html").read_text(encoding="utf-8").strip()
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{head}
<link rel="preload" as="image" href="assets/img/salao-de-beleza-800.webp" imagesrcset="assets/img/salao-de-beleza-800.webp 800w, assets/img/salao-de-beleza-1400.webp 1400w" imagesizes="(max-width: 700px) 100vw, 560px">
<style>
{css}
{extra_css}
{chr(10).join(hover_css)}
</style>
</head>
<body>
{body}
</body>
</html>
"""
    (ROOT / "index.html").write_text(html, encoding="utf-8")

    # sitemap com data de hoje
    url = re.search(r'<link rel="canonical" href="([^"]+)"', head).group(1)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{url}</loc><lastmod>{date.today().isoformat()}</lastmod></url>\n"
        "</urlset>\n", encoding="utf-8")
    print(f"OK: index.html {len(html)//1024} KB, {len(imgs)} imagem(ns), {n} efeitos de hover.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
