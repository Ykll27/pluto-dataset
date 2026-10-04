# Licenças — componentes separados

Este repositório distribui coisas diferentes, com regimes diferentes. **Nenhuma licença
abaixo é presumida**: onde o status é "a definir" ou "não verificada", o item não deve ser
redistribuído publicamente até que o responsável confirme.

| Componente | Onde | Situação |
|---|---|---|
| Código-fonte (Pluto, Minos, ARTEMIS, scripts) | `pluto/`, `artemis/`, `*.py` | **A definir pelo autor.** Sem arquivo `LICENSE`, todos os direitos ficam reservados ao autor. |
| Banco SQLite (estrutura e organização) | `Pluto/database/pluto.db` | A definir pelo autor. A licença da compilação não se estende ao conteúdo de terceiros. |
| Questões e textos das provas | tabela `questoes` (`fonte`, `licenca`, `atribuicao`) | Conteúdo de terceiros (ex.: INEP/ENEM, obtido via enem.dev). Ver `DATASET_POLICY.md`. |
| Imagens | `Pluto/assets/`, tabela `imagens` (`licenca`, `fonte`, `url_origem`) | Conteúdo de terceiros; licença registrada por imagem quando conhecida, senão `NULL`. |
| Textos motivadores e temas de redação | `redacao_temas`, `redacao_coletanea` | Cada texto mantém a própria fonte; páginas do UOL seguem os termos do UOL. |
| Notícias | `noticias` | Somente título, resumo do feed, URL e metadados — **nunca** o artigo completo. Licença do veículo (ex.: Agência Brasil) registrada em `licenca`/`atribuicao` quando verificada. |
| Dependências de terceiros | `requests`, `Pillow`, `reportlab`, opcionais `tqdm`, `pypdf` | Licenças próprias de cada projeto. |

A tabela `fontes` possui `licenca` e `licenca_verificada` (0/1). Enquanto
`licenca_verificada = 0`, trate a fonte como **não liberada** para redistribuição.
