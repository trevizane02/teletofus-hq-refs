# Gerador da HQ Teletofus (Nano Banana 2.1)

O gerador faz a HQ **quadro por quadro, sem texto**, usando a API do Gemini (Nano Banana 2.1).
Depois o próprio programa monta a página: grade, bordas douradas com filigrana, balões, recordatórios e SFX.
O texto é sempre escrito pelo código, então nunca sai com erro de letra.

## Instalar (uma vez só)

1. Instale o **Python 3.11 ou mais novo**: https://www.python.org/downloads/
   Na instalação, marque **"Add python.exe to PATH"**.
2. Baixe este repositório: botão verde **Code → Download ZIP** no GitHub. Descompacte.
   A pasta `refs` precisa ficar ao lado da pasta `gerador`, como está no repositório.
3. Dentro da pasta `gerador`, dê dois cliques em **`1_instalar.bat`**.
4. Ainda na pasta `gerador`, crie um arquivo **`chave.txt`** e cole dentro dele **só a sua chave** da API do Gemini.
   Esse arquivo nunca vai para o GitHub (está no `.gitignore`).

## Gerar uma página

- Dê dois cliques em **`2_gerar.bat`** e responda qual página quer (ex.: `2`, `4-7`, `capa`).
- Os quadros já gerados são **pulados**. Assim você pode gerar aos poucos sem gastar duas vezes.
- Se um quadro saiu ruim, rode de novo e responda o número dele em "Refazer algum quadro?".
  A versão antiga é guardada com o nome `_antigo` no fim.
- O resultado fica em `saida/vol4/pagina_XX.png`. Os quadros soltos ficam em `saida/vol4/pagina_XX/`.
- Cada chamada fica anotada em `saida/registro.csv`, com os tokens gastos, para você acompanhar o custo.

## Arrumar balões sem gastar nada

O JSON de cada página está em `vol4/pagina_XX.json`. Ali você pode:

- **Corrigir uma fala:** edite o campo `"texto"`.
- **Mudar a ordem dos personagens no quadro:** edite `"personagens_esquerda_para_direita"`.
  O gerador desenha os personagens nessa ordem, e o balão aponta para quem fala.
- **Mudar a posição de um balão:** acrescente no texto `"posicao": [0.7, 0.1]`.
  Os números são frações do quadro: o primeiro é de 0 (esquerda) a 1 (direita), o segundo de 0 (topo) a 1 (base).
- **Mudar para onde a ponta do balão aponta:** acrescente `"cauda": [0.5, 0.6]`, no mesmo formato.

Depois dê dois cliques em **`3_montar_de_novo.bat`**. Ele só remonta a página, sem chamar a IA.

## Modelos e custo

- Por padrão o gerador usa `gemini-nano-banana-2.1`, que aceita até 4 personagens.
- Quadros com os 5 heróis usam o **Nano Banana Pro** (`gemini-3-pro-image`), que aceita 5. Ele custa mais.
- Para forçar outro modelo: `py gerar.py 4 --modelo gemini-3-pro-image`.
- Para ver os prompts sem gastar nada: `py gerar.py 4 --ver`.

## Personagens e regras

- **`biblia.json`:** ficha de cada personagem, estilo travado e objetos (hidra, flecha da Eve, fragmento de mana).
- **`../refs/`:** as imagens de referência.

Mudou um personagem? Mude a `biblia.json` e o próximo quadro gerado já segue a mudança.
