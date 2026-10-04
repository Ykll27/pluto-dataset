#!/usr/bin/env python3
"""Gera a pasta export/ com os arquivos leves que o app Intensivo Fafram lê direto do GitHub.

O pluto.db completo é grande demais para um celular baixar e abrir. Este script tira dele
só o que o app usa e grava três arquivos pequenos:

  export/versao.json    versão do dataset e contagens (o app consulta este a cada abertura)
  export/questoes.json  questões de múltipla escolha com gabarito, 5 alternativas em texto e sem imagem
  export/redacao.json   temas de redação do Ensino Médio com seus textos motivadores

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


def exportar_questoes(con):
    alternativas = {}
    for qid, letra, texto, arquivo in con.execute(
        "select questao_id, letra, texto, arquivo from alternativas order by questao_id, letra"
    ):
        alternativas.setdefault(qid, []).append((letra, texto, arquivo))
    com_imagem = {r[0] for r in con.execute("select distinct questao_id from questao_imagens")}

    saida = []
    for qid, ano, numero, disciplina, idioma, contexto, intro, correta in con.execute(
        "select id, ano, numero, disciplina, coalesce(idioma,''), coalesce(contexto,''),"
        " coalesce(introducao_alternativas,''), alternativa_correta"
        " from questoes order by ano, numero, disciplina"
    ):
        alts = alternativas.get(qid)
        if correta not in LETRAS or len(correta or "") != 1 or qid in com_imagem or not alts or len(alts) != 5:
            continue
        if any(a[0] != LETRAS[i] or a[2] or not (a[1] or "").strip() for i, a in enumerate(alts)):
            continue
        contexto, intro = contexto.strip(), intro.strip()
        if (not contexto and not intro) or "![" in contexto + intro:
            continue
        saida.append([ano, numero, disciplina, idioma, contexto, intro,
                      [a[1].strip() for a in alts], LETRAS.index(correta)])
    return saida


def exportar_redacao(con):
    """Temas do Ensino Médio, de fonte com licença verificada, com pelo menos um texto motivador."""
    verificadas = set()
    if "licenca_verificada" in colunas(con, "fontes"):
        verificadas = {r[0] for r in con.execute("select nome from fontes where licenca_verificada = 1")}
    tem_status = "status" in colunas(con, "redacao_temas")
    tem_tags = "tags_json" in colunas(con, "redacao_temas")

    textos, imagens = {}, {}
    for rid, tipo, titulo, fonte, texto in con.execute(
        "select redacao_id, tipo, titulo, fonte, texto from redacao_coletanea order by redacao_id, ordem"
    ):
        texto = (texto or "").strip()
        if tipo == "Imagem":
            imagens[rid] = imagens.get(rid, 0) + 1
        elif len(texto) > 80 and not LIXO.search(texto):
            textos.setdefault(rid, []).append([(titulo or "Texto motivador").strip(), texto, (fonte or "").strip()])

    saida, vistos = [], set()
    campos = "id, tema, fonte, url" + (", status" if tem_status else ", null") + (", tags_json" if tem_tags else ", '[]'")
    for rid, tema, fonte, url, status, tags in con.execute(f"select {campos} from redacao_temas order by tema"):
        tema = (tema or "").strip()
        if not tema or fonte not in verificadas or rid not in textos:
            continue
        if tem_status and status != "APROVADO":
            continue
        tags = json.loads(tags or "[]")
        if "segmento:Ensino Médio" not in tags or tema.lower() in vistos:
            continue
        vistos.add(tema.lower())
        genero = next((t.split(":", 1)[1] for t in tags if t.startswith("genero:")), "")
        saida.append({"t": tema, "g": genero, "f": fonte, "u": url or "", "m": textos[rid], "img": imagens.get(rid, 0)})
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
    questoes = exportar_questoes(con)
    temas = exportar_redacao(con)
    con.close()
    if not questoes:
        sys.exit("Nenhuma questão utilizável encontrada; export/ não foi alterada.")

    os.makedirs(a.saida, exist_ok=True)
    tamanhos = {
        "questoes.json": gravar(os.path.join(a.saida, "questoes.json"), {"v": versao, "q": questoes}),
        "redacao.json": gravar(os.path.join(a.saida, "redacao.json"), {"v": versao, "temas": temas}),
    }
    gravar(os.path.join(a.saida, "versao.json"), {
        "formato": 1,
        "dataset_version": versao,
        "gerado_em": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "questoes": len(questoes),
        "temas": len(temas),
        "arquivos": tamanhos,
    })
    print(f"versão {versao}: {len(questoes)} questões, {len(temas)} temas de redação")
    for nome, t in tamanhos.items():
        print(f"  {a.saida}/{nome}: {t / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
