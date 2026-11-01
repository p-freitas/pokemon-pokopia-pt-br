# Formato e validação da integração

As estruturas abaixo foram observadas nos arquivos locais; não constituem especificação oficial.

- IDX: 12.298 registros little-endian de 32 bytes, com quatro `uint64`: offset, tamanho descomprimido, tamanho armazenado e flag.
- Contêiner comprimido: tamanho de bloco, quantidade e total em três `uint32`, tabela de tamanhos e blocos alinhados a 128 bytes. Foram observados blocos máximos de 65.536, 131.072 e 524.288 bytes. Streams zlib têm prefixo de tamanho; blocos crus usam diretamente o tamanho esperado.
- Tabelas textuais: quantidade no offset 0, versão no 4 e registros a partir de 64. Strings UTF-8 terminadas em NUL, com ponteiros `int32` relativos à posição de cada ponteiro. Layouts reconhecidos: 8 bytes/um campo, 12 bytes/dois campos, 32 bytes/seis campos. Layouts ambíguos são recusados.

## Base e reaproveitamento

A `main` atualizada, commit `94c8f42`, passou a publicar `1.0.4/romfs` e `2.0.1/romfs`. A integração parte do par da 2.0.1. Não se aplica o mod experimental anterior sobre ele.

A comparação do catálogo encontrou 34.397 campos já modificados pelo upstream e preservou todos. Entre os campos ainda idênticos ao inglês, 78 tinham traduções dos novos lotes locais. Foram mantidos 75; três campos permaneceram em inglês para respeitar a política de nomes de golpes e títulos relacionados. Os 708 candidatos herdados da tradução antiga ficaram separados, sem aplicação automática. As 467 variantes locais divergentes de traduções upstream não substituíram o mantenedor.

Essas contagens são do catálogo técnico, que inclui repetições, variantes, nomes e candidatos debug. Não recalculam a porcentagem editorial de 96,8% da release 2.0.0.

## Correção do tamanho armazenado

No par upstream, 248 registros comprimidos informavam tamanho armazenado menor que o exigido pelo próprio cabeçalho e sua tabela de chunks. Uma leitura limitada pelo IDX resultava em truncamento. A tolerância de leitura é restrita a bases com hashes previamente reconhecidos, para recuperar os contêineres completos.

A correção altera somente o terceiro `uint64` desses registros para o extent alinhado derivado dos chunks, exceto nos bancos também reconstruídos, que recebem os valores completos do novo contêiner. Não se move nem se modifica seu payload. O resultado inteiro é relido estritamente, sem tolerância a tamanho desatualizado. Não se afirma que essa divergência causava um defeito específico no jogo: o efeito demonstrado é a consistência entre índice, contêiner e tamanho físico.

## Reconstrução e limites

O BIN da base upstream permanece como prefixo idêntico. Nos seis bancos que recebem textos novos, preservam-se cabeçalho, metadados e pool antigo; acrescentam-se strings e atualizam-se apenas seus ponteiros. O banco recomprimido é acrescentado ao BIN. Os demais conteúdos, inclusive fora do catálogo, permanecem iguais.

A validação comparou os 12.298 payloads: 12.292 bancos byte a byte idênticos; nos outros seis, somente os 75 campos previstos mudaram, preservando 3.781 outros campos. Todos os registros gerados passaram pela leitura estrita. Recursos gráficos e a versão 1.0.4 não têm diferenças em relação ao upstream.

Novas traduções são validadas por multiconjunto exato de tags/placeholders, caracteres de controle e quebras de linha. Isso não comprova posicionamento semântico das tags, encaixe visual ou execução de todas as cenas. As 618 diferenças de tags herdadas, inclusive formatação, foram sinalizadas e preservadas, sem revisão estilística.

`integration.json`, `integration_build.json` e `integration_validation.json` registram o delta e as verificações. `build_validation.json` representa o último build, que pode conter zero alterações quando a base consolidada já incorpora o catálogo. Os hashes aceitos estão em `source_manifest.json`.

Ainda falta o primeiro teste visual do mod integrado no PokeDinner. Não houve teste nesta sessão, instalação ou alteração de saves/configurações. A consulta ao código do loader do fork havia sido bloqueada por Cloudflare; o suporte a LayeredFS observado provém do log local existente, não de uma auditoria completa do loader.
