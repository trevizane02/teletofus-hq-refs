"""
Gera os QUADROS da HQ com o Nano Banana (API do Gemini), um quadro por chamada e SEM texto.
Os balões e falas são colocados depois pelo montar.py.

Uso:
  python gerar.py 4             -> gera os quadros da página 4 que ainda não existem e monta a página
  python gerar.py 4-7           -> páginas 4 a 7
  python gerar.py capa          -> capa (essa sai inteira, com títulos)
  python gerar.py 4 --refazer 2 -> gera de novo só o quadro 2 da página 4
  python gerar.py 4 --ver       -> só mostra os prompts e as imagens que iriam, sem gastar nada

A chave fica na variável de ambiente GEMINI_API_KEY (nunca coloque a chave no GitHub).
"""
import argparse
import csv
import io
import json
import os
import sys
import time
from datetime import datetime

from comum import (REFS, SAIDA, carregar_biblia, carregar_pagina, caixas_dos_quadros,
                   proporcao_mais_proxima)

MODELO_PADRAO = "gemini-nano-banana-2.1"   # até 4 imagens de personagem por chamada
MODELO_GRUPO = "gemini-3-pro-image"        # Nano Banana Pro: até 5 personagens (usado quando o quadro tem 5)
RESOLUCAO = "2K"


def limpar_cenario(c):
    """'4 quadros (câmara da hidra)' -> 'câmara da hidra'"""
    import re
    c = re.sub(r"^\s*\d+\s+quadros?[^(]*", "", c).strip()
    return c[1:-1] if c.startswith("(") and c.endswith(")") else c


def prompt_do_quadro(biblia, pag, q):
    pers = q["personagens_esquerda_para_direita"]
    linhas = [
        "Create ONE single comic panel illustration (not a page, not a grid, no borders, no frame).",
        f"STYLE: {biblia['estilo']} Match the rendering of the attached STYLE PAGE exactly, but never copy its scene, characters or text.",
        "ABSOLUTELY NO TEXT in the image: no speech bubbles, no captions, no letters, no sound effects, no signatures, no watermarks.",
        "Keep the top 25% of the panel calm and darker (background, sky, wall, shadow) with no faces touching the top edge: speech balloons will be added there later.",
        f"SCENE (setting: {limpar_cenario(pag.get('cenario', ''))}). Camera: {q.get('enquadramento') or 'medium shot'}.",
        q["cena"],
    ]
    if pers:
        nomes = ", ".join(biblia["personagens"][p]["nome"] for p in pers)
        linhas.append(f"CHARACTERS IN THIS PANEL, placed from LEFT to RIGHT in this order: {nomes}. "
                      f"Exactly {len(pers)} named character(s); each appears only once. No other named character appears.")
        for p in pers:
            c = biblia["personagens"][p]
            linhas.append(f"- {c['nome']}: {c['ficha']} Copy face, age, hair color and texture, outfit, colors and weapon EXACTLY from the attached reference images labeled {c['nome']}.")
        if any(p in ("will", "iske", "eve", "maya", "derken") for p in pers):
            linhas.append(biblia["marca"] + " Only show it if the forearm is visible.")
    else:
        linhas.append("No main characters in this panel unless the scene describes them.")
    for o in q.get("objetos", []):
        linhas.append(biblia["objetos"][o])
    if "eve" in pers:
        if pag.get("eve_com_flecha"):
            linhas.append(biblia["objetos"]["eve_flecha.jpg"] + " Show it whenever her abdomen is visible, unless the scene says the arrow is expelled.")
        else:
            linhas.append("Eve has NO arrow in her body anymore (it was expelled).")
    linhas.append("The faces and outfits of the reference images win over any other description. Keep anatomy correct (hands, fingers).")
    return "\n".join(linhas)


def prompt_pagina_inteira(biblia, pag):
    q = pag["quadros"][0]
    textos = "\n".join(f'- "{t["texto"]}"' for t in q["textos"])
    base = prompt_do_quadro(biblia, pag, q)
    base = base.replace("Create ONE single comic panel illustration (not a page, not a grid, no borders, no frame).",
                        "Create a full comic book COVER, vertical 2:3, one single illustration, thin ornate gold frame with filigree corners.")
    base = base.replace("ABSOLUTELY NO TEXT in the image: no speech bubbles, no captions, no letters, no sound effects, no signatures, no watermarks.",
                        "Write ONLY these texts, letter by letter, in gold aged lettering, at the positions described in the scene:\n" + textos)
    base = base.replace("Keep the top 25% of the panel calm and darker (background, sky, wall, shadow) with no faces touching the top edge: speech balloons will be added there later.\n", "")
    return base


def imagens_do_quadro(biblia, pag, q):
    """Lista (rótulo, arquivo). Personagens: até 4 imagens no 2.1 (5 no Pro)."""
    pers = q["personagens_esquerda_para_direita"]
    imgs = [("STYLE PAGE (copy only the rendering style)", pag["estilo"])]
    if len(pers) <= 2:
        for p in pers:
            c = biblia["personagens"][p]
            imgs.append((f"Reference of {c['nome']} (full body)", c["referencia"]))
            imgs.append((f"Reference of {c['nome']} (face)", c["rosto"]))
    else:
        for p in pers:
            c = biblia["personagens"][p]
            imgs.append((f"Reference of {c['nome']} (full body)", c["referencia"]))
    for o in q.get("objetos", []):
        imgs.append((f"Reference object: {o}", o))
    if "eve" in pers and pag.get("eve_com_flecha"):
        imgs.append(("Reference: position of the arrow in Eve's abdomen", "eve_flecha.jpg"))
    return imgs


def modelo_para(q, forcado):
    if forcado:
        return forcado
    return MODELO_GRUPO if len(q["personagens_esquerda_para_direita"]) >= 5 else MODELO_PADRAO


def chamar_api(cliente, modelo, prompt, imagens, proporcao):
    from google.genai import types
    from PIL import Image

    conteudo = [prompt]
    for rotulo, arq in imagens:
        conteudo.append(rotulo + ":")
        conteudo.append(Image.open(REFS / arq))
    config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(aspect_ratio=proporcao, image_size=RESOLUCAO),
    )
    espera = 10
    for tentativa in range(5):
        try:
            resp = cliente.models.generate_content(model=modelo, contents=conteudo, config=config)
            for part in (resp.candidates[0].content.parts if resp.candidates else []):
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    return part.inline_data.data, resp
            motivo = resp.candidates[0].finish_reason if resp.candidates else getattr(resp, "prompt_feedback", None)
            raise RuntimeError(f"A API não devolveu imagem (motivo: {motivo}).")
        except Exception as e:
            msg = str(e)
            temporario = any(c in msg for c in ("429", "500", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "DEADLINE"))
            if not temporario or tentativa == 4:
                raise
            print(f"   limite/erro temporário, tentando de novo em {espera}s...")
            time.sleep(espera)
            espera *= 2


def registrar_custo(pasta, linha):
    arq = SAIDA / "registro.csv"
    novo = not arq.exists()
    with open(arq, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["quando", "pagina", "quadro", "modelo", "tokens_entrada", "tokens_saida"])
        w.writerow(linha)


def expandir_paginas(arg):
    if arg.lower() in ("capa", "contracapa"):
        return [arg.lower()]
    if "-" in arg:
        a, b = arg.split("-")
        return [str(i) for i in range(int(a), int(b) + 1)]
    return [x.strip() for x in arg.split(",")]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paginas", help="ex.: 4  |  4-7  |  4,9,12  |  capa  |  contracapa")
    ap.add_argument("--volume", default="vol4")
    ap.add_argument("--refazer", default="", help="números dos quadros para gerar de novo, ex.: 2 ou 1,3")
    ap.add_argument("--ver", action="store_true", help="só mostra prompts e imagens, sem chamar a API")
    ap.add_argument("--modelo", default="", help="força um modelo (ex.: gemini-3-pro-image)")
    ap.add_argument("--nao-montar", action="store_true")
    a = ap.parse_args()

    biblia = carregar_biblia()
    refazer = {int(x) for x in a.refazer.split(",") if x.strip()}
    cliente = None
    if not a.ver:
        chave_arq = os.path.join(os.path.dirname(__file__), "chave.txt")
        if not os.environ.get("GEMINI_API_KEY") and os.path.exists(chave_arq):
            os.environ["GEMINI_API_KEY"] = open(chave_arq, encoding="utf-8").read().strip()
        if not os.environ.get("GEMINI_API_KEY"):
            sys.exit("Falta a chave: defina GEMINI_API_KEY (veja o LEIA-ME).")
        from google import genai
        cliente = genai.Client()

    for p in expandir_paginas(a.paginas):
        pag, nome = carregar_pagina(a.volume, p)
        pasta = SAIDA / a.volume / nome
        pasta.mkdir(parents=True, exist_ok=True)
        inteira = pag.get("modo") == "pagina_inteira_com_texto"
        caixas = caixas_dos_quadros(pag["grade"])
        print(f"\n== {nome} ({'página inteira' if inteira else str(len(pag['quadros'])) + ' quadros'}) ==")

        for q in pag["quadros"]:
            destino = pasta / ("pagina.png" if inteira else f"q{q['n']}.png")
            if destino.exists() and q["n"] not in refazer:
                print(f" quadro {q['n']}: já existe, pulando (use --refazer {q['n']} para gerar de novo)")
                continue
            if inteira:
                prompt, proporcao = prompt_pagina_inteira(biblia, pag), "2:3"
            else:
                x, y, w, h = caixas[q["n"]]
                prompt, proporcao = prompt_do_quadro(biblia, pag, q), proporcao_mais_proxima(w, h)
            imagens = imagens_do_quadro(biblia, pag, q)
            modelo = modelo_para(q, a.modelo)
            print(f" quadro {q['n']}: {modelo}, proporção {proporcao}, {len(imagens)} imagens: {', '.join(i[1] for i in imagens)}")
            if a.ver:
                print("   " + prompt.replace("\n", "\n   "))
                continue
            if destino.exists():
                antigo = destino.with_name(destino.stem + datetime.now().strftime("_antigo_%H%M%S") + ".png")
                destino.rename(antigo)
            dados, resp = chamar_api(cliente, modelo, prompt, imagens, proporcao)
            destino.write_bytes(dados)
            (pasta / (destino.stem + ".json")).write_text(json.dumps(
                {"modelo": modelo, "proporcao": proporcao, "imagens": [i[1] for i in imagens], "prompt": prompt},
                ensure_ascii=False, indent=2), encoding="utf-8")
            u = getattr(resp, "usage_metadata", None)
            registrar_custo(pasta, [datetime.now().isoformat(timespec="seconds"), nome, q["n"], modelo,
                                    getattr(u, "prompt_token_count", ""), getattr(u, "candidates_token_count", "")])
            print(f"   salvo em {destino.relative_to(SAIDA.parent)}")

        if not a.ver and not a.nao_montar:
            import montar
            montar.montar_pagina(a.volume, p)


if __name__ == "__main__":
    main()
