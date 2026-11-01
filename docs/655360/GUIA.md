# Tradução experimental — dados 655360

Desenvolvimento na branch `ptbr/pokopia-v2.0.1a-655360`, a partir de `main` no commit `31093c5`. Tradução de referência: [LucianoNeo/pokemon-pokopia-pt-br](https://github.com/LucianoNeo/pokemon-pokopia-pt-br), por LucianoNeo e colaboradores. Foram preservadas as traduções reaproveitáveis, sem revisão estilística automática.

## Compatibilidade e estado

A identificação fornecida para o jogo é **2.0.1a (655360)**. O suporte desta ferramenta é definido pelos SHA-256 do par BIN/IDX em `reports/655360/source_manifest.json`, e não apenas pelo nome da pasta. O backup e os 44 arquivos do RomFS instalado foram comparados integralmente: iguais. O build ID do executável também coincide com o registrado no log existente do PokeDinner 2.0.0. Não foi obtida uma identificação independente da versão comercial a partir de metadados NACP.

O mod passou nas verificações de arquivos. **Ainda não foi testado no jogo nesta sessão.** Uma instância do emulador estava aberta e foi preservada. Não houve instalação automática, alteração de configurações, acesso de escrita a saves ou modificação dos originais. O primeiro teste visual ainda é necessário; iniciar o jogo não comprova compatibilidade completa.

Os bancos textuais ingleses são traduzidos. Imagens, vídeos, bancos antigos versão 0 e possíveis textos fora dos grupos de idiomas identificados ainda não foram adaptados. Não use os arquivos gráficos da tradução 1.0.4 nesta versão sem uma investigação própria.

## Gerar o mod na sua máquina

Requer Python 3.10 ou superior, sem pacotes externos. Execute os comandos na raiz deste repositório. Tenha uma cópia própria e intacta do RomFS correspondente aos hashes suportados.

```powershell
python scripts/project.py configure --source "CAMINHO/DO/SEU/BACKUP/romfs"
python -m unittest discover -s tests -v
python scripts/project.py build
```

O resultado fica em `build/Pokopia-PTBR-655360/romfs`. A configuração local fica em `local/config.json`, ignorada pelo Git. A geração recusa fontes com outros hashes e grava somente dentro de `build/`.

Se você recebeu o patch compacto, pode aplicá-lo sem extrair os bancos:

```powershell
python scripts/patch.py apply --source "CAMINHO/DO/SEU/BACKUP/romfs" --patch "Pokopia-PTBR-655360-patch.zip"
```

Nesse caso, o resultado fica em `build/from-patch/romfs`. O patch não contém o BIN original completo; exige a cópia original local e verifica os hashes antes e depois da aplicação.

## Instalar e remover no PokeDinner

1. Feche o jogo antes de instalar. Preserve seus backups e saves.
2. Na lista do emulador, use a opção de abrir a pasta de mods do jogo. O title ID confirmado no `main.npdm` é `0400A3A01EE4C000`. Na instalação Eden/PokeDinner observada, a raiz esperada é `%APPDATA%/eden/load/0400A3A01EE4C000/`; prefira a pasta indicada pelo próprio emulador.
3. Copie a pasta `Pokopia-PTBR-655360` gerada, mantendo `Pokopia-PTBR-655360/romfs/LD_C0_R.BIN` e `LI_C0_R.IDX` juntos. Para o resultado do patch, crie essa pasta e coloque `from-patch/romfs` dentro dela.
4. Ative somente este mod textual e mantenha o idioma do jogo em inglês. Inicie usando o `main` do update 655360 correspondente ao seu backup.
5. No primeiro teste, confirme que o mod aparece nas propriedades e que algum menu muda. Registre erros, texto e captura, se houver. Não é necessário testar a cada lote.

Para remover, feche o jogo e desative ou remova **somente a pasta deste mod**. Nenhuma substituição dos arquivos do update é necessária.

## Editar traduções

A base canônica é `translations/655360/catalog.jsonl`. Cada linha contém `id`, `source`, `translation`, `status`, banco, linha e campo. IDs como `b04610:r00687:f00` identificam um campo desta versão; não são IDs universais entre versões.

Para revisão em CSV:

```powershell
python scripts/project.py review
# Edite translations/655360/review.csv e salve como CSV UTF-8.
python scripts/project.py review --import-file "translations/655360/review.csv"
python scripts/project.py build
```

Altere apenas `translation` e `status`. Não altere `id` ou `source`. `reviewed` deve ser escolhido somente por uma pessoa após revisão. A importação valida os identificadores, fontes, tags e status antes de salvar. Não se sobrescrevem traduções revisadas durante os lotes automáticos. Para revisão parcial, o CSV pode conter só as linhas editadas.

Os estados são `pending_translation`, `translated_unreviewed`, `reviewed` e `needs_attention`. Candidatos antigos recusados tecnicamente ficam em `candidate_translation`; não entram no mod.

## Traduzir novos lotes

Consulte primeiro `translations/655360/glossary.tsv` e a memória gerada `memory.jsonl`. Não refaça traduções que já tenham status de tradução.

```powershell
python scripts/project.py queue --bank 3899 --limit 40 --output local/next_batch.jsonl
# Preencha translation, preservando source e id.
python scripts/project.py apply local/next_batch.jsonl
python scripts/project.py report
```

`apply` recebe apenas entradas pendentes; repetições idênticas são toleradas para retomar uma etapa interrompida. A IA marca seus lotes como `translated_unreviewed`. O comando `reuse` reaproveita somente fontes inteiras com tradução única na memória; não faz substituições parciais.

Os TSV dos lotes aceitam duas colunas (`source`, `translation`) ou quatro (`source singular`, `source plural`, `tradução singular`, `tradução plural`), sem cabeçalho. Compile com `scripts/compile_batch.py` e aplique o JSONL resultante.

## Contribuir por fork e Pull Request

Mantenha os arquivos de 655360 em suas pastas específicas. Inclua uma descrição do problema, ID afetado e a correção; evite alterar traduções já aprovadas sem contexto. Execute os testes e reconstrua após mudanças. No PR, diferencie validação de arquivos de teste real no jogo.

O fluxo combinado será fork → branch `ptbr/pokopia-v2.0.1a-655360` → push para seu fork → PR para o repositório original. **Nada foi publicado, enviado ou aberto automaticamente.** O remoto local ainda aponta para o upstream, sem alteração.

Não inclua `local/`, `build/`, backups, saves, chaves, firmware, executáveis ou arquivos originais do jogo em novos commits. Os binários já rastreados em `romfs/` pertencem ao histórico do upstream e permanecem intactos nesta branch. O material novo para distribuição deve priorizar ferramentas, base editável e patch compacto.

Não foi encontrada licença explícita no README ou na árvore do commit upstream consultado. Não foi atribuída uma licença presumida às traduções herdadas. Confirme com o mantenedor as condições para redistribuição e licenciamento antes da publicação; o direito de fazer fork no GitHub é descrito separadamente da licença de distribuição na [documentação do GitHub](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).
