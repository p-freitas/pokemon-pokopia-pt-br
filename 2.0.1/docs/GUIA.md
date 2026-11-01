# Desenvolvimento da tradução 2.0.1 — update 655360

Esta pasta segue a divisão por versão do repositório de LucianoNeo. A base é a release 2.0.0, commit `94c8f42`. A pasta `1.0.4/` e os arquivos gráficos de `2.0.1/romfs/` permanecem intactos.

A contribuição acrescenta **75 campos** ainda em inglês na base upstream, distribuídos por seis bancos. Não substitui traduções existentes por variantes locais: 467 divergências foram resolvidas mantendo o upstream. Outros 708 candidatos antigos foram separados para avaliação, fora do mod. Os nomes de golpes continuam em inglês.

O conjunto ainda exige teste no jogo. Não foi aberto o emulador, instalado o mod ou alterado qualquer save. A identificação fornecida como 2.0.1a corresponde ao update 655360; o código verifica hashes dos arquivos, sem deduzir a versão pelo nome da pasta.

## Instalar e remover

1. Feche o jogo e preserve seus backups.
2. No PokeDinner, abra a pasta de mods do jogo. O title ID confirmado é `0400A3A01EE4C000`.
3. Crie uma pasta para esta tradução e copie `2.0.1/romfs` para dentro dela. A estrutura final deve ser `NOME-DO-MOD/romfs/LD_C0_R.BIN`, com o IDX ao lado e os recursos gráficos nas subpastas existentes.
4. Ative o mod e mantenha o jogo em inglês. Não misture os arquivos de `1.0.4/` e `2.0.1/`.
5. No primeiro teste, confirme o carregamento do mod e alguns textos de interface. Não é necessário reiniciar o jogo a cada lote.

Para remover, feche o jogo e desative ou remova somente a pasta deste mod. Não é necessário substituir os arquivos originais do update.

## Editar e reconstruir

Requer Python 3.10+, sem dependências externas. O BIN usa Git LFS: em um clone Git, execute `git lfs pull` antes de reconstruir. Comandos abaixo executados na raiz do repositório:

```powershell
python 2.0.1/tools/project.py configure --source "CAMINHO/DO/BACKUP/romfs"
python 2.0.1/tools/project.py review
# Edite 2.0.1/translations/review.csv em UTF-8.
python 2.0.1/tools/project.py review --import-file "2.0.1/translations/review.csv"
python -m unittest discover -s 2.0.1/tests -v
python 2.0.1/tools/project.py build
```

O resultado fica em `2.0.1/build/Pokopia-PTBR-655360/romfs`. O build usa a cópia original para conferir fontes e a RomFS versionada como base, preservando inclusive bancos fora do catálogo. Não sobrescreve o jogo ou a RomFS versionada. Para gerar um pacote instalável completo, junte o par de texto gerado aos recursos gráficos da `2.0.1/romfs`; estes não são modificados pelo script.

A configuração pessoal fica em `2.0.1/local/config.json`, ignorada pelo Git. O par original precisa coincidir com `2.0.1/reports/source_manifest.json`. Bases de outra versão ou alterações não reconhecidas são recusadas. O build é idempotente: sem alterações no catálogo, a base consolidada produz o mesmo par BIN/IDX.

A base canônica é `2.0.1/translations/catalog.jsonl`: uma entrada por linha, com `id`, `source`, `translation`, `status`, banco, linha e campo. Preserve `id` e `source`; edite a tradução e o status. O CSV pode conter só as linhas que deseja importar. A importação inteira é validada antes de salvar.

Estados: `pending_translation`, `translated_unreviewed`, `reviewed`, `needs_attention`. Somente uma pessoa deve marcar `reviewed`. Lotes automáticos não sobrescrevem traduções existentes. Diferenças técnicas herdadas do upstream, inclusive mudanças de `<br>`, são sinalizadas sem apagar o texto da base. Novas alterações devem preservar tags e placeholders.

## Continuar a tradução

Consulte `glossary.tsv` e a memória gerada por `report`, evitando retraduzir textos já preenchidos:

```powershell
python 2.0.1/tools/project.py queue --limit 40 --output 2.0.1/local/next_batch.jsonl
# Preencha translation, mantendo source e id.
python 2.0.1/tools/project.py apply 2.0.1/local/next_batch.jsonl
python 2.0.1/tools/project.py report
```

`additions.jsonl` registra os 75 campos acrescentados nesta integração. `legacy_candidates.jsonl` guarda os 708 candidatos antigos não aplicados. Não os trate como traduções aprovadas. O catálogo também contém nomes preservados e candidatos debug/japoneses: suas métricas não equivalem às contagens editoriais da release.

Para conferir a extração sem modificar o catálogo:

```powershell
python 2.0.1/tools/project.py extract --source "CAMINHO/DO/BACKUP/romfs" --output 2.0.1/local/originais.jsonl
```

## Contribuir

Faça alterações dentro da versão correspondente e descreva IDs, problema e correção no PR. Execute testes e reconstrução; informe separadamente se houve teste no jogo. Não inclua backups, saves, chaves, firmware, configurações pessoais ou novos arquivos originais completos do jogo. Arquivos gerados temporariamente ficam em `2.0.1/build/`.

Créditos da base: [LucianoNeo e colaboradores](https://github.com/LucianoNeo/pokemon-pokopia-pt-br). A contribuição local foi preparada por Pedro Freitas com auxílio do Codex. Não foi identificada licença explícita no commit consultado; não foi atribuída uma licença presumida ao material herdado. Essa condição permanece documentada para alinhamento com o mantenedor, sem alterar o fluxo de fork e PR autorizado pelo usuário.
