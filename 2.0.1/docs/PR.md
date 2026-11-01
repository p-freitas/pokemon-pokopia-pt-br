# Sugestão de Pull Request

Título: **Complementa a tradução 2.0.1 e adiciona ferramentas de edição e validação**

A tradução 2.0.0 da versão 2.0.1 permanece como base. A contribuição acrescenta 75 campos de interface, tutoriais, missões e descrições ainda em inglês, sem substituir traduções existentes. Corrige também 248 registros IDX cujo tamanho armazenado era menor que o extent descrito pelo contêiner comprimido.

Ferramentas, catálogo editável, candidatos pendentes, testes e documentação ficam dentro de `2.0.1/`, seguindo a organização por versão. A pasta `1.0.4/` e os recursos gráficos da 2.0.1 permanecem intactos. As traduções novas estão explicitamente em `translated_unreviewed`.

Validação: sete testes automatizados; extração das fontes reproduzida; leitura estrita dos 12.298 registros; comparação dos 12.292 payloads intocados e dos 75 campos novos em seis bancos; reconstrução idempotente e reaplicação do patch por hashes. O teste visual no PokeDinner ainda está pendente. As métricas técnicas do catálogo não substituem a contagem editorial da release.

Os candidatos antigos não aplicados e as divergências de tags herdadas permanecem separados para avaliação. Não houve instalação automática ou alteração de saves/configurações.
