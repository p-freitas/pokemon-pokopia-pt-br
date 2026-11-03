# Gerar uma release com BIN comprimido

A ferramenta usa os quatro arquivos traduzidos de `2.0.1/romfs` como entrada.
Ela gera um ZIP com a mesma estrutura da release atual: README, instalador
independente e `2.0.1/romfs` com BIN, IDX e os dois recursos gráficos.

## Compilar no Windows

Com Git LFS e Python 3.11 ou superior instalados, na raiz do repositório:

```powershell
git lfs pull
py -3 tools/release/build_release.py --version 2.5.1
```

Substitua `2.5.1` pela versão que será publicada. O processo usa o script
existente `tools/installer/build.ps1`, que prepara PyInstaller e compila o EXE.
É necessário acesso à internet para instalar as dependências de compilação.
Os jogadores continuam sem precisar de Python ou de programas de compressão.

O resultado fica em `dist/Pokemon-Pokopia-PT-BR-v2.5.1.zip`. Publique esse ZIP na
release com tag `v2.5.1`. A URL alternativa de download do instalador é gerada
com essa mesma versão. Para publicar em outro repositório, use
`--repository dono/repositorio`. Não publique um pacote de teste como release
estável antes de validar o carregamento no jogo.

O relatório `*-build.json`, ao lado do ZIP, contém os tamanhos, os hashes de
entrada e saída e a quantidade de registros verificados. Ele não entra no ZIP.
Use `--output C:\caminho\saida` para escolher outra pasta; a ferramenta recusa
sobrescrever uma release existente.

Para gerar somente os arquivos de instalação manual, sem compilar o EXE:

```powershell
py -3 tools/release/build_release.py --version 2.5.1-teste --manual-only
```

Essa opção funciona também fora do Windows e produz um ZIP com sufixo `-manual`.

## O que muda na build

- Reempacota os registros ativos do BIN, mantendo a ordem do IDX e alinhamento
  de 256 bytes entre registros. Espaço sem referência no IDX não é copiado.
- Mantém os blocos já comprimidos sem recomprimi-los. Bancos crus são convertidos
  para o contêiner zlib em blocos de 65.536 bytes somente quando houver economia.
  Dentro do contêiner, blocos e tabelas mantêm alinhamento de 128 bytes.
- Atualiza offsets, tamanhos armazenados e indicadores de compressão no IDX.
  Registros antigos cujo tamanho armazenado subestima a tabela de blocos são
  reparados usando a extensão física descrita pelo próprio contêiner.
- Decodifica todos os registros antes e depois e compara seus conteúdos byte a
  byte, incluindo bancos fora do catálogo textual. Qualquer diferença aborta
  a build. Os recursos gráficos são copiados sem alterações e seus hashes no
  ZIP final também são conferidos.
- Gera uma cópia temporária do código do instalador com os hashes do pacote
  comprimido. Preserva as assinaturas do jogo original e das traduções anteriores
  para permitir instalação limpa, atualização e reconhecimento da nova build.

Não altera os arquivos traduzidos versionados nem exige um original do jogo
para construir o pacote. As verificações de dados são automáticas; elas não
substituem o teste no jogo dos bancos que passam a usar compressão.

## Instalação pelos jogadores

O procedimento continua igual: extrair o ZIP e executar o instalador, ou copiar
o conteúdo de `2.0.1/romfs` para o RomFS do update. BIN e IDX devem sempre vir da
mesma build. Backups, detecção de versão e substituição dos quatro arquivos
continuam sendo feitos pelo instalador existente.

Na base v2.5.0, o BIN passou de 252.779.776 para 147.951.360 bytes: economia de
41,47%, com os 12.298 registros decodificados idênticos. O arquivo fica menor que
o BIN original do jogo porque 757 bancos antes crus passam a usar compressão;
nenhum idioma, texto ou outro conteúdo referenciado no IDX é removido.
O tamanho exato e os hashes podem variar entre versões do zlib; as versões de
Python e zlib usadas na build ficam registradas no relatório.
