"""Coisas compartilhadas entre gerar.py e montar.py: caminhos, leitura dos JSONs e a grade da página."""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
REFS = RAIZ.parent / "refs"
SAIDA = RAIZ / "saida"

# Página final: 2:3, igual às páginas aprovadas
PAGINA_W, PAGINA_H = 2048, 3072
MARGEM = 56      # borda preta externa
CALHA = 30       # espaço preto entre quadros

PROPORCOES = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]


def carregar_biblia():
    return json.loads((RAIZ / "biblia.json").read_text(encoding="utf-8"))


def arquivo_pagina(volume, pagina):
    p = str(pagina).lower()
    nome = p if p in ("capa", "contracapa") else p.zfill(2)
    return RAIZ / volume / f"pagina_{nome}.json"


def carregar_pagina(volume, pagina):
    caminho = arquivo_pagina(volume, pagina)
    if not caminho.exists():
        raise SystemExit(f"Não achei {caminho}. Páginas disponíveis: "
                         + ", ".join(sorted(x.stem.replace('pagina_', '') for x in (RAIZ / volume).glob('pagina_*.json'))))
    return json.loads(caminho.read_text(encoding="utf-8")), caminho.stem


def caixas_dos_quadros(grade):
    """Devolve {numero_do_quadro: (x, y, largura, altura)} para a grade [[1],[2],[3,4],[5]]."""
    linhas = len(grade)
    util_h = PAGINA_H - 2 * MARGEM - (linhas - 1) * CALHA
    altura = util_h // linhas
    caixas = {}
    y = MARGEM
    for linha in grade:
        n = len(linha)
        util_w = PAGINA_W - 2 * MARGEM - (n - 1) * CALHA
        largura = util_w // n
        x = MARGEM
        for q in linha:
            caixas[q] = (x, y, largura, altura)
            x += largura + CALHA
        y += altura + CALHA
    return caixas


def proporcao_mais_proxima(w, h):
    alvo = w / h
    def valor(p):
        a, b = p.split(":")
        return int(a) / int(b)
    return min(PROPORCOES, key=lambda p: abs(valor(p) - alvo))
