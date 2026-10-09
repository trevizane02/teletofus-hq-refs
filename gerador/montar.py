"""
Monta a página final: grade, bordas douradas com filigrana, balões, recordatórios e SFX, tudo por código.
O texto sai sempre certo, porque não é a IA que escreve.

Uso:
  python montar.py 4        -> monta saida/vol4/pagina_04.png com os quadros que existirem
  python montar.py 2-32     -> monta várias

Ajuste fino de um balão: no JSON da página, dentro do texto, acrescente
  "posicao": [0.70, 0.08]   (centro do balão, em fração da largura/altura do quadro)
  "cauda":   [0.55, 0.60]   (para onde a ponta do balão aponta)
e rode o montar.py de novo. Não gasta nada.
"""
import math
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from comum import (RAIZ, SAIDA, PAGINA_W, PAGINA_H, carregar_pagina, caixas_dos_quadros)

OURO = (196, 154, 72)
OURO_ESCURO = (120, 88, 34)
BEGE = (232, 214, 176)
PRETO = (0, 0, 0)
FONTE_TEXTO = RAIZ / "fontes" / "EBGaramond.ttf"
FONTE_SFX = RAIZ / "fontes" / "Cinzel.ttf"


def fonte(caminho, tamanho, peso="SemiBold"):
    f = ImageFont.truetype(str(caminho), tamanho)
    try:
        f.set_variation_by_name(peso)
    except Exception:
        pass
    return f


# ---------- quadros e moldura ----------

def encaixar(img, w, h):
    """Corta a imagem para cobrir a caixa (sem distorcer)."""
    iw, ih = img.size
    escala = max(w / iw, h / ih)
    nova = img.resize((math.ceil(iw * escala), math.ceil(ih * escala)), Image.LANCZOS)
    x = (nova.width - w) // 2
    y = (nova.height - h) // 3 if nova.height > h else 0   # corta mais embaixo, preserva cabeças
    return nova.crop((x, y, x + w, y + h))


def filigrana(d, x, y, sx, sy, t=1.0):
    """Ornamento dourado num canto. sx/sy = direção (+1/-1) para dentro do quadro."""
    L = int(46 * t)
    d.line([(x, y + sy * L), (x, y), (x + sx * L, y)], fill=OURO, width=3)
    d.line([(x + sx * 9, y + sy * (L - 14)), (x + sx * 9, y + sy * 9), (x + sx * (L - 14), y + sy * 9)], fill=OURO, width=2)
    cx, cy = x + sx * 9, y + sy * 9
    r = 7
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=OURO)
    for k in (1, 2):
        ax, ay = x + sx * (L + 6 * k), y
        d.ellipse([ax - 3, ay - 3, ax + 3, ay + 3], fill=OURO)
        bx, by = x, y + sy * (L + 6 * k)
        d.ellipse([bx - 3, by - 3, bx + 3, by + 3], fill=OURO)


def moldura_quadro(d, x, y, w, h):
    d.rectangle([x, y, x + w - 1, y + h - 1], outline=OURO, width=4)
    for cx, cy, sx, sy in ((x, y, 1, 1), (x + w - 1, y, -1, 1), (x, y + h - 1, 1, -1), (x + w - 1, y + h - 1, -1, -1)):
        filigrana(d, cx + sx * 6, cy + sy * 6, sx, sy, 0.8)


def moldura_pagina(d):
    m = 20
    d.rectangle([m, m, PAGINA_W - m - 1, PAGINA_H - m - 1], outline=OURO_ESCURO, width=3)
    for cx, cy, sx, sy in ((m, m, 1, 1), (PAGINA_W - m - 1, m, -1, 1), (m, PAGINA_H - m - 1, 1, -1), (PAGINA_W - m - 1, PAGINA_H - m - 1, -1, -1)):
        filigrana(d, cx, cy, sx, sy, 1.2)


# ---------- texto ----------

def quebrar(texto, f, largura_max, d):
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = (atual + " " + palavra).strip()
        if d.textlength(teste, font=f) <= largura_max or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def medir_bloco(texto, f, largura_max, d, entrelinha=1.12):
    linhas = quebrar(texto, f, largura_max, d)
    alt = int(f.size * entrelinha)
    larg = max(d.textlength(l, font=f) for l in linhas)
    return linhas, larg, alt * len(linhas), alt


def escrever_bloco(d, linhas, f, cx, topo, alt_linha, cor):
    for i, l in enumerate(linhas):
        d.text((cx, topo + i * alt_linha + alt_linha / 2), l, font=f, fill=cor, anchor="mm")


# ---------- balões ----------

def contorno_explosao(cx, cy, rx, ry, pontas=22):
    pts = []
    for i in range(pontas * 2):
        a = math.pi * i / pontas
        k = 1.18 if i % 2 == 0 else 0.98
        pts.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
    return pts


def ponto_na_elipse(cx, cy, rx, ry, alvo):
    ang = math.atan2((alvo[1] - cy) / ry, (alvo[0] - cx) / rx)
    return ang


def desenhar_balao(img, tipo, cx, cy, rx, ry, cauda, linhas, f, alt_linha):
    d = ImageDraw.Draw(img)
    contorno, largura = PRETO, 4
    # cauda (triângulo) primeiro, para a elipse cobrir a base
    if cauda and tipo != "pensamento":
        ang = ponto_na_elipse(cx, cy, rx, ry, cauda)
        abertura = 0.22
        b1 = (cx + rx * 0.92 * math.cos(ang - abertura), cy + ry * 0.92 * math.sin(ang - abertura))
        b2 = (cx + rx * 0.92 * math.cos(ang + abertura), cy + ry * 0.92 * math.sin(ang + abertura))
        d.polygon([b1, cauda, b2], fill="white", outline=contorno)
        d.line([b1, cauda, b2], fill=contorno, width=largura, joint="curve")
    if tipo == "grito":
        pts = contorno_explosao(cx, cy, rx, ry)
        d.polygon(pts, fill="white")
        d.line(pts + [pts[0]], fill=contorno, width=largura, joint="curve")
    else:
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill="white")
        if tipo == "sussurro":
            n = 60
            for i in range(0, n, 2):
                a1, a2 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
                d.line([(cx + rx * math.cos(a1), cy + ry * math.sin(a1)), (cx + rx * math.cos(a2), cy + ry * math.sin(a2))], fill=contorno, width=largura)
        else:
            d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=contorno, width=largura)
    if cauda and tipo == "pensamento":
        for k, r in ((0.35, 16), (0.65, 11), (0.9, 7)):
            px = cx + (cauda[0] - cx) * k
            py = cy + ry + (cauda[1] - cy - ry) * k
            d.ellipse([px - r, py - r, px + r, py + r], fill="white", outline=contorno, width=3)
    # recobre a base da cauda por dentro
    d.ellipse([cx - rx + largura + 2, cy - ry + largura + 2, cx + rx - largura - 2, cy + ry - largura - 2], fill="white") if tipo != "grito" else None
    escrever_bloco(d, linhas, f, cx, cy - alt_linha * len(linhas) / 2, alt_linha, PRETO)


def recordatorio(img, x, y, largura_max, texto, f):
    d = ImageDraw.Draw(img)
    linhas, larg, alt, al = medir_bloco(texto, f, largura_max - 60, d)
    w, h = int(larg + 60), int(alt + 44)
    caixa = Image.new("RGBA", (w, h), (8, 6, 4, 235))
    img.paste(caixa, (int(x), int(y)), caixa)
    d.rectangle([x, y, x + w, y + h], outline=OURO, width=3)
    d.rectangle([x + 7, y + 7, x + w - 7, y + h - 7], outline=OURO_ESCURO, width=2)
    escrever_bloco(d, linhas, f, x + w / 2, y + 22, al, BEGE)
    return w, h


def sfx(img, cx, cy, texto, tamanho, angulo=-8):
    f = fonte(FONTE_SFX, tamanho, "Black")
    tmp = Image.new("RGBA", (int(tamanho * len(texto) * 0.9) + 80, int(tamanho * 1.8)), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.text((tmp.width / 2, tmp.height / 2), texto, font=f, fill=(222, 178, 84), anchor="mm",
           stroke_width=max(4, tamanho // 14), stroke_fill=(30, 18, 6))
    tmp = tmp.rotate(angulo, expand=True, resample=Image.BICUBIC)
    img.paste(tmp, (int(cx - tmp.width / 2), int(cy - tmp.height / 2)), tmp)


def letreiro_do_quadro(img, caixa, q):
    x, y, w, h = caixa
    d = ImageDraw.Draw(img)
    pers = q.get("personagens_esquerda_para_direita", [])
    estreito = w < 1200
    tam = 40 if not estreito else 36
    f = fonte(FONTE_TEXTO, tam, "Bold")
    f_rec = fonte(FONTE_TEXTO, tam - 2, "SemiBold")
    margem = 26

    textos = q.get("textos", [])
    recs = [t for t in textos if t["tipo"] == "recordatorio"]
    falas = [t for t in textos if t["tipo"] in ("fala", "grito", "sussurro", "pensamento")]
    efeitos = [t for t in textos if t["tipo"] == "sfx"]

    ocupado_esq = 0
    topo_rec = y + margem
    for t in recs:
        if "posicao" in t:
            px, py = x + t["posicao"][0] * w, y + t["posicao"][1] * h
            recordatorio(img, px, py, w * 0.5, t["texto"], f_rec)
            continue
        rw, rh = recordatorio(img, x + margem, topo_rec, w * (0.48 if not estreito else 0.9), t["texto"], f_rec)
        ocupado_esq = max(ocupado_esq, rw + margem * 2)
        topo_rec += rh + 14

    cursor_x = x + ocupado_esq + margem if (ocupado_esq and not estreito) else x + margem
    topo = y + margem if not (recs and estreito) else topo_rec + 6
    ultimo_falante, ultimo_fundo = None, None
    for t in falas:
        cabe = (w - 2 * margem - 40) * 0.74
        comprimento = d.textlength(t["texto"], font=f)
        ideal = math.sqrt(comprimento * f.size * 1.25 * 2.4)   # bloco ~2,4x mais largo que alto
        largura_max = max(f.size * 5, min(ideal, cabe, w * (0.42 if not estreito else 0.9)))
        linhas, larg, alt, al = medir_bloco(t["texto"], f, largura_max, d)
        while alt > h * 0.38 and f.size > 26:
            f = fonte(FONTE_TEXTO, f.size - 2, "Bold")
            linhas, larg, alt, al = medir_bloco(t["texto"], f, largura_max, d)
        rx = min(larg / 2 / 0.74 + 20, (w - 2 * margem) / 2)
        ry = alt / 2 / 0.70 + 18
        # onde está o falante
        falante = t.get("falante") or ""
        if falante in pers:
            fx = x + w * (pers.index(falante) + 0.5) / len(pers)
            alvo = (fx, y + h * 0.52)
        elif t.get("fora_do_quadro"):
            fx = x + w * 0.85
            alvo = (x + w - 4, y + h * 0.45)
        else:
            fx = x + w * 0.5
            alvo = (fx, y + h * 0.55)
        if "posicao" in t:
            cx, cy = x + t["posicao"][0] * w, y + t["posicao"][1] * h
        elif falante and falante == ultimo_falante and ultimo_fundo:
            cx, cy = ultimo_fundo[0] + rx * 0.35, ultimo_fundo[1] + ry + 10
        else:
            cx = max(cursor_x + rx, min(fx, x + w - margem - rx))
            cy = topo + ry
        cx = max(x + margem + rx, min(cx, x + w - margem - rx))
        cy = max(y + margem + ry, min(cy, y + h - margem - ry))
        if "cauda" in t:
            alvo = (x + t["cauda"][0] * w, y + t["cauda"][1] * h)
        # cauda não pode passar de 30% da altura do quadro
        dy = alvo[1] - (cy + ry)
        if dy > h * 0.3:
            alvo = (alvo[0], cy + ry + h * 0.3)
        mesmo = falante and falante == ultimo_falante
        desenhar_balao(img, t["tipo"], cx, cy, rx, ry, None if mesmo else alvo, linhas, f, al)
        if mesmo:   # liga os dois balões do mesmo falante
            d.line([ultimo_fundo, (cx, cy - ry)], fill=PRETO, width=4)
        cursor_x = cx + rx + 14
        ultimo_falante, ultimo_fundo = falante, (cx, cy + ry)

    for i, t in enumerate(efeitos):
        if "posicao" in t:
            cx, cy = x + t["posicao"][0] * w, y + t["posicao"][1] * h
        else:
            cx, cy = x + w * (0.72 - 0.3 * i), y + h * (0.72 - 0.08 * i)
        sfx(img, cx, cy, t["texto"], int(min(h * 0.22, 150) if len(t["texto"]) < 12 else min(h * 0.16, 110)))


# ---------- página ----------

def montar_pagina(volume, pagina):
    pag, nome = carregar_pagina(volume, pagina)
    pasta = SAIDA / volume / nome
    destino = SAIDA / volume / f"{nome}.png"
    if pag.get("modo") == "pagina_inteira_com_texto":
        arte = pasta / "pagina.png"
        if not arte.exists():
            print(f" {nome}: falta gerar a arte (pagina.png)")
            return None
        encaixar(Image.open(arte).convert("RGB"), PAGINA_W, PAGINA_H).save(destino)
        print(f" página pronta: {destino.relative_to(SAIDA.parent)}")
        return destino

    img = Image.new("RGB", (PAGINA_W, PAGINA_H), PRETO)
    d = ImageDraw.Draw(img)
    caixas = caixas_dos_quadros(pag["grade"])
    faltando = []
    for q in pag["quadros"]:
        x, y, w, h = caixas[q["n"]]
        arq = pasta / f"q{q['n']}.png"
        if arq.exists():
            img.paste(encaixar(Image.open(arq).convert("RGB"), w, h), (x, y))
        else:
            faltando.append(q["n"])
            d.rectangle([x, y, x + w, y + h], fill=(38, 34, 30))
            d.text((x + w / 2, y + h / 2), f"QUADRO {q['n']}\n(ainda não gerado)", font=fonte(FONTE_TEXTO, 44), fill=(120, 110, 95), anchor="mm", align="center")
        camada = img.crop((x, y, x + w, y + h))
        letreiro_do_quadro(camada, (0, 0, w, h), q)
        img.paste(camada, (x, y))
        moldura_quadro(ImageDraw.Draw(img), x, y, w, h)
    moldura_pagina(ImageDraw.Draw(img))
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino)
    aviso = f" (faltam os quadros {faltando})" if faltando else ""
    print(f" página montada: {destino.relative_to(SAIDA.parent)}{aviso}")
    return destino


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    from gerar import expandir_paginas
    vol = sys.argv[2] if len(sys.argv) > 2 else "vol4"
    for p in expandir_paginas(sys.argv[1]):
        montar_pagina(vol, p)
