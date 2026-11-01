# Checkpoint — 655360

Leia `docs/655360/GUIA.md`, `docs/655360/FORMATO.md` e `reports/655360/progress.json`. Continue na branch `ptbr/pokopia-v2.0.1a-655360`. Não altere os binários rastreados em `romfs/`: são o patch upstream 1.0.4.

A base canônica é `translations/655360/catalog.jsonl`; não reextraia nem substitua o catálogo. Fontes locais estão somente em `local/config.json`, ignorado pelo Git. O backup foi localizado e os 44 arquivos coincidem com o RomFS instalado; o relatório de hashes usa apenas caminhos relativos.

Foram processados seis lotes: 1.688 campos preenchidos, dos quais 1.674 diferem da fonte. Outros 30.682 campos modificados foram reaproveitados do upstream/memória. Nomes e comandos sem texto podem ser preservados sem modificação. Todas as 34.882 entradas preenchidas aguardam revisão humana; nenhuma foi automaticamente marcada como revisada. Há 4.051 pendentes e 268 com atenção necessária.

O par experimental contém 248 bancos alterados e 32.356 campos efetivamente modificados. Testes de integridade e reaplicação do patch passaram. Não houve teste no jogo, instalação ou alteração de saves/configurações. A instância do PokeDinner encontrada aberta foi preservada. Não encerre a sessão do usuário para testar.

Próximo trabalho: obter o primeiro teste visual controlado e continuar os pendentes por `queue`, priorizando diálogos novos e descrições. Os maiores grupos pendentes podem ser contados com Python, sem imprimir o catálogo inteiro. Consulte apenas glossário/memória relevantes. Não repita revisão estilística ou testes de emulador por lote.

O usuário fará fork + PR no futuro. Não faça push, abra PR, altere remoto nem publique sem autorização explícita. Licença upstream não identificada; registre essa pendência, sem inventar permissões. Não enviar arquivos a tradutores externos. Sem necessidade de subagentes.
