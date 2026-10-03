# Salão Sem Mensalidade: página de vendas

Site: https://salaosemmensalidade.netlify.app/ (deploy automático do Netlify a cada push na `main`).

## Importante para o SEO

O HTML exportado do editor Design vem como "Bundled Page": a página só aparece depois que o JavaScript desempacota tudo, e o Google recebe um arquivo de 4 MB sem título e sem texto. **Não suba o export direto como `index.html`.**

Sempre passe o export pelo conversor:

```bash
python3 tools/design-para-seo.py caminho/do/export-do-design.html
git add -A && git commit -m "Atualiza página" && git push
```

O conversor gera o `index.html` estático, leve e com SEO, a partir do export.

## Onde mexer

- `seo/head.html`: título, descrição, Open Graph e dados estruturados (schema). Se o domínio mudar, troque a URL aqui e em `robots.txt`.
- `seo/faq.html`: perguntas frequentes visíveis na página. Se alterar uma pergunta, altere também o bloco FAQPage em `seo/head.html`.
- `assets/`: fontes e imagens geradas pelo conversor.
- Copy: sem travessão no texto visível.
