#!/usr/bin/env python3
"""Gera a pasta export/ com os arquivos leves que o app Intensivo Fafram lê direto do GitHub.

O pluto.db completo é grande demais para um celular baixar e abrir. Este script tira dele
só o que o app usa e grava três arquivos pequenos:

  export/versao.json    versão do dataset e contagens (o app consulta este a cada abertura)
  export/questoes.json      questões de múltipla escolha com gabarito, 5 alternativas em texto e sem imagem
  export/questoes-img.json  questões com imagem no enunciado ou nas alternativas
  export/redacao.json       temas de redação do Ensino Médio com textos e imagens motivadores

As imagens não são copiadas: os arquivos citam o caminho delas neste repositório (assets/...),
no formato ![](assets/...), e o app as carrega direto do GitHub.

Uso:
  python tools/exportar_app.py caminho/para/pluto.db [--versao 2026.10.04] [--saida export]

Sem --versao, a versão é lida de database/version.json. Só usa a biblioteca padrão do Python.
"""
import argparse
import datetime
import json
import os
import re
import sqlite3
import sys

LETRAS = "ABCDE"
LIXO = re.compile(r"window\.|<script|function\s*\(", re.I)


def colunas(con, tabela):
    return {r[1] for r in con.execute(f"pragma table_info([{tabela}])")}


MARCA_IMG = re.compile(r"!\[[^\]]*\]\([^)]*\)")


def caminho_repo(arquivo):
    """Caminho da imagem dentro do repositório (o banco guarda com o prefixo Pluto/)."""
    arquivo = (arquivo or "").strip()
    return arquivo[len("Pluto/"):] if arquivo.startswith("Pluto/") else arquivo


def imagem_existe(caminho):
    # só confere quando o script roda na raiz do repositório, onde está a pasta assets/
    return bool(caminho) and (not os.path.isdir("assets") or os.path.isfile(caminho))


def exportar_questoes(con):
    """Devolve (questões só de texto, questões com imagem)."""
    alternativas = {}
    for qid, letra, texto, arquivo in con.execute(
        "select questao_id, letra, texto, arquivo from alternativas order by questao_id, letra"
    ):
        alternativas.setdefault(qid, []).append((letra, texto, arquivo))
    imagens = {}
    for qid, origem, arquivo in con.execute(
        "select qi.questao_id, qi.origem, im.arquivo from questao_imagens qi"
        " join imagens im on im.id = qi.imagem_id order by qi.rowid"
    ):
        imagens.setdefault(qid, {}).setdefault(origem, []).append(caminho_repo(arquivo))

    so_texto, com_imagem = [], []
    for qid, ano, numero, disciplina, idioma, contexto, intro, correta in con.execute(
        "select id, ano, numero, disciplina, coalesce(idioma,''), coalesce(contexto,''),"
        " coalesce(introducao_alternativas,''), alternativa_correta"
        " from questoes order by ano, numero, disciplina"
    ):
        alts = alternativas.get(qid)
        if correta not in LETRAS or len(correta or "") != 1 or not alts or len(alts) != 5:
            continue
        if any(a[0] != LETRAS[i] for i, a in enumerate(alts)):
            continue
        contexto, intro = contexto.strip(), intro.strip()
        if not contexto and not intro:
            continue
        imgs = imagens.get(qid, {})
        tem_marca = bool(MARCA_IMG.search(contexto + intro))

        if not imgs and not tem_marca:
            if any(a[2] or not (a[1] or "").strip() for a in alts):
                continue
            so_texto.append([ano, numero, disciplina, idioma, contexto, intro,
                             [a[1].strip() for a in alts], LETRAS.index(correta)])
            continue

        # questão com imagem: troca cada marca do enunciado pelo caminho da imagem no repositório
        fila = [c for c in imgs.get("enunciado", []) if imagem_existe(c)]
        if tem_marca and not fila:
            continue

        def troca(_):
            return f"![]({fila.pop(0)})" if fila else ""
        contexto = MARCA_IMG.sub(troca, contexto).strip()
        intro = MARCA_IMG.sub(troca, intro).strip()
        if fila:
            contexto = (contexto + "\n\n" + "\n\n".join(f"![]({c})" for c in fila)).strip()

        textos, ok = [], True
        for letra, texto, _arquivo in alts:
            texto = (texto or "").strip()
            if texto:
                textos.append(texto)
                continue
            c = next((c for c in imgs.get("alternativa_" + letra, []) if imagem_existe(c)), None)
            if not c:
                ok = False
                break
            textos.append(f"![]({c})")
        if ok:
            com_imagem.append([ano, numero, disciplina, idioma, contexto, intro, textos, LETRAS.index(correta), 1])
    return so_texto, com_imagem


def exportar_redacao(con):
    """Temas do Ensino Médio, de fonte com licença verificada, com pelo menos um texto ou imagem de apoio."""
    verificadas = set()
    if "licenca_verificada" in colunas(con, "fontes"):
        verificadas = {r[0] for r in con.execute("select nome from fontes where licenca_verificada = 1")}
    tem_status = "status" in colunas(con, "redacao_temas")
    tem_tags = "tags_json" in colunas(con, "redacao_temas")
    tem_imagem = "imagem" in colunas(con, "redacao_coletanea")

    itens, imagens = {}, {}
    for rid, tipo, titulo, fonte, texto, imagem in con.execute(
        "select redacao_id, tipo, titulo, fonte, texto, " + ("imagem" if tem_imagem else "null")
        + " from redacao_coletanea order by redacao_id, ordem"
    ):
        texto = (texto or "").strip()
        if tipo == "Imagem":
            c = caminho_repo(imagem)
            if imagem_existe(c):
                # item de imagem: [título, "", fonte, caminho no repositório]
                itens.setdefault(rid, []).append([(titulo or "Imagem de apoio").strip(), "", (fonte or "").strip(), c])
                imagens[rid] = imagens.get(rid, 0) + 1
        elif len(texto) > 80 and not LIXO.search(texto):
            itens.setdefault(rid, []).append([(titulo or "Texto motivador").strip(), texto, (fonte or "").strip()])

    saida, vistos = [], set()
    campos = "id, tema, fonte, url" + (", status" if tem_status else ", null") + (", tags_json" if tem_tags else ", '[]'")
    for rid, tema, fonte, url, status, tags in con.execute(f"select {campos} from redacao_temas order by tema"):
        tema = (tema or "").strip()
        if not tema or fonte not in verificadas or rid not in itens:
            continue
        if tem_status and status != "APROVADO":
            continue
        tags = json.loads(tags or "[]")
        if "segmento:Ensino Médio" not in tags or tema.lower() in vistos:
            continue
        vistos.add(tema.lower())
        genero = next((t.split(":", 1)[1] for t in tags if t.startswith("genero:")), "")
        saida.append({"t": tema, "g": genero, "f": fonte, "u": url or "", "m": itens[rid], "img": imagens.get(rid, 0)})
    return saida


def gravar(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, separators=(",", ":"))
    return os.path.getsize(caminho)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("banco")
    p.add_argument("--versao")
    p.add_argument("--saida", default="export")
    a = p.parse_args()

    versao = a.versao
    if not versao:
        try:
            with open(os.path.join("database", "version.json"), encoding="utf-8") as f:
                versao = json.load(f)["dataset_version"]
        except (OSError, KeyError, ValueError):
            sys.exit("Informe --versao ou rode na raiz do repositório, onde existe database/version.json.")

    con = sqlite3.connect(f"file:{a.banco}?mode=ro", uri=True)
    questoes, questoes_img = exportar_questoes(con)
    temas = exportar_redacao(con)
    con.close()
    if not questoes:
        sys.exit("Nenhuma questão utilizável encontrada; export/ não foi alterada.")

    os.makedirs(a.saida, exist_ok=True)
    tamanhos = {
        "questoes.json": gravar(os.path.join(a.saida, "questoes.json"), {"v": versao, "q": questoes}),
        "questoes-img.json": gravar(os.path.join(a.saida, "questoes-img.json"), {"v": versao, "q": questoes_img}),
        "redacao.json": gravar(os.path.join(a.saida, "redacao.json"), {"v": versao, "temas": temas}),
    }
    gravar(os.path.join(a.saida, "versao.json"), {
        "formato": 2,
        "dataset_version": versao,
        "gerado_em": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "questoes": len(questoes),
        "questoes_com_imagem": len(questoes_img),
        "temas": len(temas),
        "arquivos": tamanhos,
    })
    print(f"versão {versao}: {len(questoes)} questões de texto, {len(questoes_img)} com imagem, {len(temas)} temas de redação")
    for nome, t in tamanhos.items():
        print(f"  {a.saida}/{nome}: {t / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
