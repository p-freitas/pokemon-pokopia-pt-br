# Checkpoint da contribuição 2.0.1

Branch: `ptbr/pokopia-v2.0.1a-655360`. Base upstream: `94c8f42`. `origin` é o fork `p-freitas/pokemon-pokopia-pt-br`; `upstream` é `LucianoNeo/pokemon-pokopia-pt-br`. O usuário autorizou commits e pushes no fork. O usuário abrirá o Pull Request; não criar PR automaticamente.

Leia `GUIA.md`, `FORMATO.md` e os relatórios em `../reports/`. O catálogo canônico está em `../translations/catalog.jsonl`. Não reextraia por cima dele. Os 75 campos úteis dos lotes anteriores foram integrados sobre a tradução nova do mantenedor. Os 708 candidatos antigos não foram aplicados; 467 traduções sobrepostas divergentes foram resolvidas mantendo o upstream.

O BIN/IDX consolidado preserva o conteúdo do upstream, acrescenta os 75 campos e corrige 248 tamanhos armazenados no índice. As imagens da 2.0.1 e toda a versão 1.0.4 permanecem iguais. A base consolidada está na própria `2.0.1/romfs`. `build` gera resultado isolado e não sobrescreve a RomFS versionada.

Fontes pessoais ficam somente em `2.0.1/local/config.json`. Não publicar backups, saves, chaves, firmware ou configurações. O backup original foi comparado integralmente com a instalação na sessão anterior: 44 arquivos idênticos. O suporte usa hashes, sem afirmar a versão comercial apenas pelo nome da pasta.

Próximos passos: primeiro teste visual controlado; depois, continuar pendentes e candidatos escolhidos pelo usuário. Não repetir revisão estilística, abrir o emulador por lote ou alterar traduções revisadas. O usuário continua responsável pela revisão linguística. A licença upstream não foi identificada; não inventar uma licença para o material herdado.
