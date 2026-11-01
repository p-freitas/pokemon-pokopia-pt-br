# Formato observado e evidências

Os detalhes abaixo resultam da leitura dos arquivos locais, não de uma especificação oficial do jogo. A consulta ao código do servidor Eden foi impedida por proteção Cloudflare; não se afirma ter auditado o loader do fork. O log local existente registra `FindLooseRomFS` e aplicação de patches LayeredFS para o title ID confirmado no NPDM.

## Arquivo e compressão

`LI_C0_R.IDX` tem registros little-endian de 32 bytes: quatro `uint64` contendo offset, tamanho descomprimido, tamanho armazenado e flag. O update local tem 12.298 registros, contra 11.783 no patch 1.0.4. Há entradas vazias, dados crus e flag de compressão 1.

O contêiner comprimido começa com três `uint32`: tamanho máximo do bloco, quantidade de blocos e total descomprimido. Segue uma tabela de tamanhos. Cabeçalho e blocos são alinhados a 128 bytes. Foram observados blocos máximos de 65.536, 131.072 e 524.288 bytes. Blocos comprimidos possuem prefixo de quatro bytes e stream zlib; quando o tamanho registrado coincide com o tamanho esperado descomprimido, o bloco é cru e não possui esse prefixo.

Todos os 12.298 registros atuais e os 11.783 antigos foram lidos. A leitura antiga usa uma tolerância explícita apenas para obter traduções: 234 registros do patch publicado subestimam o tamanho armazenado requerido pelo cabeçalho. Essa tolerância nunca é aplicada ao jogo atual ou ao resultado gerado. Os binários antigos não são copiados para o mod atual.

## Textos

O cabeçalho das tabelas possui quantidade no offset 0, versão no offset 4 e registros a partir de 64. Strings são UTF-8 terminadas em NUL, referenciadas por ponteiros `int32` relativos à posição do próprio ponteiro. Foram identificados layouts de 8 bytes com um campo, 12 bytes com dois campos e 32 bytes com seis campos. Metadados restantes são opacos e preservados. Layouts ambíguos são recusados pelo parser.

O scanner atual reconheceu 2.702 tabelas versão 2 e 274 grupos não vazios de nove idiomas. Selecionou o segundo banco de cada grupo como o banco inglês, com âncoras de conteúdo japonês no primeiro e chinês no último. Algumas entradas desse banco ainda são candidatos japoneses/debug, mantidos sem tradução. Os 39.201 campos não vazios catalogados não equivalem necessariamente a 39.201 frases únicas destinadas ao jogador. Existem 31.775 fontes distintas e 7.426 repetições.

Não se presume equivalência de offsets ou números de linha entre versões. O reaproveitamento associa um campo pela tupla exata das fontes nos outros oito idiomas. Traduções antigas divergentes para a mesma chave são recusadas. Depois, reaproveita-se a memória por fonte inglesa completa, somente quando a tradução é única. Não há inglês original da 1.0.4 no repositório para uma comparação independente; a correspondência multilíngue é a evidência utilizada, com proveniência registrada no catálogo.

## Reconstrução conservadora

O BIN original inteiro permanece como prefixo idêntico do resultado. Para cada banco alterado, preserva-se a tabela original, acrescentam-se as novas strings ao final e mudam-se apenas seus ponteiros. Os metadados e o pool antigo permanecem intactos. O banco é recomprimido e acrescentado ao arquivo; somente seu registro IDX recebe os quatro valores novos, incluindo tamanho armazenado correto.

Após reconstruir, o código reabre cada banco alterado, confere todos os campos, compara os bytes opacos, verifica os registros IDX intocados e o prefixo completo do BIN. Tags, variáveis e comandos são comparados por multiconjunto exato, incluindo `<br>`. Portanto, mudanças legítimas de formatação no patch antigo também podem exigir atenção manual. A contagem exata de tags não garante que sua posição na frase seja semanticamente adequada; a revisão humana continua necessária.

Não foi confirmado limite de comprimento visual ou de largura dos menus. A expansão do arquivo e o alcance dos ponteiros são validados tecnicamente; o encaixe da tradução e os efeitos do tamanho maior do banco ainda precisam do teste no jogo.

## Retomada

O catálogo é o checkpoint canônico. `reports/655360/progress.json` registra as contagens; `source_manifest.json` fixa os hashes suportados; `build_validation.json` guarda o último build. `backup_comparison.json` documenta a comparação completa somente com caminhos relativos. O glossário e os lotes estão em `translations/655360/`.

Não execute `extract` sobre uma base existente. Para reconstruir em outra máquina, use `configure` com um RomFS original que passe nos hashes. O uso normal da base distribuída não depende do BIN antigo. A extração inicial, caso necessária para pesquisa, requer os binários antigos do upstream, incluindo Git LFS, e uma base nova vazia.
