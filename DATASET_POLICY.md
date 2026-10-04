# Política do dataset Pluto

1. **Nada sem fonte.** Todo item (questão, imagem, texto-base, redação, repertório, notícia)
   precisa de fonte; itens sem fonte são rejeitados ou ficam fora da geração.
2. **Nada inventado.** Classificações pedagógicas (habilidade, competência, dificuldade) só são
   gravadas quando vêm de uma origem identificada (`classificacao_origem`); caso contrário
   ficam `NULL`/`desconhecida`. O Minos não completa coletâneas com textos repetidos ou criados.
3. **Staging antes do oficial.** Importadores gravam em `pluto.staging.db`; a promoção exige
   revisão humana (`--aprovar`), faz backup e checa integridade antes e depois.
4. **Notícias:** apenas metadados e resumo do feed (até 1000 caracteres), com URL canônica.
5. **Rastreabilidade:** SHA-256, datas de origem e importação, versão e procedência por item;
   `staging_itens` registra novos, alterados, duplicados e rejeitados com motivo.
6. **Publicação:** só com `manifest.json` atualizado (`python -m pluto.manifesto --verificar`).
   Backups, relatórios, staging e a memória do Minos nunca são publicados.
7. **Licenças:** ver `LICENCAS.md`. Fonte com `licenca_verificada = 0` não deve ser
   redistribuída publicamente.
8. **Dados de teste** usam a fonte `enem-sintetico-teste` e não são conteúdo oficial.
