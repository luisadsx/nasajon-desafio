# Notas Técnicas — Decisões do Projeto

## 1. Estratégia de matching de municípios

O `input.csv` contém erros intencionais de digitação (ex: `Belo Horzionte`, `Curitba`, `Santoo Andre`). Para lidar com isso, implementei uma estratégia de matching em três camadas:

1. **Correspondência exata normalizada**: remove acentos e ignora maiúsculas/minúsculas. Resolve casos como `Niteroi` → `Niterói` e `Sao Paulo` → `São Paulo`.

2. **Correspondência por substring**: verifica se o nome do input está contido no nome IBGE ou vice-versa. Útil para nomes parcialmente corretos.

3. **Distância de Levenshtein**: algoritmo clássico de similaridade de strings que conta o número mínimo de edições (inserções, remoções, substituições) para transformar uma string na outra. Tolera até 2 erros, cobrindo casos como `Curitba` → `Curitiba` (1 inserção) e `Belo Horzionte` → `Belo Horizonte` (1 transposição).

### Casos especiais do input
| Entrada | Decisão | Justificativa |
|---|---|---|
| `Belo Horzionte` | OK → Belo Horizonte / MG | Levenshtein = 1 |
| `Curitba` | OK → Curitiba / PR | Levenshtein = 1 |
| `Santo Andre` | OK → Santo André / SP | Correspondência exata normalizada; múltiplos municípios com mesmo nome → preferiu maior ID IBGE (SP) |
| `Santoo Andre` | NAO_ENCONTRADO | Duplicata de `Santo Andre` detectada pela deduplicação (ver seção 3) |

## 2. Desambiguação de municípios com nome idêntico

Existem múltiplos municípios no Brasil com o mesmo nome (ex: "Santo André" existe em SP e em PB). Quando a correspondência exata normalizada retorna mais de um resultado, o programa prefere o município com **maior ID IBGE**. IDs IBGE são prefixados pelo código do estado (SP=35, RJ=33, MG=31, etc.), portanto estados do Sudeste e Sul tendem a ter IDs maiores, o que funciona como critério de desempate para os nomes mais conhecidos.

## 3. Deduplicação por nome IBGE normalizado

O input contém dois municípios que, após o matching, apontam para o mesmo nome oficial do IBGE: `Santo Andre` → "Santo André/SP" e `Santoo Andre` → "Santo André/PB". Embora sejam municípios com IDs diferentes, representam o mesmo nome real e configuram uma entrada duplicada/com erro de digitação.

Após o matching inicial, o programa percorre todos os resultados e detecta pares com o mesmo nome IBGE normalizado. Para cada par, mantém como `OK` apenas a linha com **menor distância de Levenshtein** em relação ao nome oficial (ou seja, a que tem menos erros de digitação) e marca a outra como `NAO_ENCONTRADO`.

No caso concreto:
- `Santo Andre` → distância 0 para "santo andre" → **mantido como OK**
- `Santoo Andre` → distância 1 para "santo andre" → **NAO_ENCONTRADO**

## 4. Carregamento da API do IBGE

Optei por fazer **um único GET** para `https://servicodados.ibge.gov.br/api/v1/localidades/municipios`, carregando todos os ~5.570 municípios em memória. Isso é mais eficiente do que fazer uma chamada por município, reduz a latência total e evita sobrecarregar a API pública com múltiplas requisições.

## 5. Tratamento de erros

- `ERRO_API`: quando a API do IBGE está indisponível (exception na requisição HTTP). O programa continua processando as demais linhas.
- `NAO_ENCONTRADO`: quando nenhum dos algoritmos de matching encontra correspondência com distância aceitável, ou quando a linha é identificada como duplicata com mais erros.

## 6. Estatísticas

- `pop_total_ok`: soma apenas municípios com status `OK`, excluindo os não encontrados.
- `medias_por_regiao`: calculada com base na `populacao_input` (dado fornecido), não no censo do IBGE, conforme especificação.
- `Santoo Andre` (NAO_ENCONTRADO) é excluída das estatísticas de população e médias por região.

## 7. Autenticação

O `ACCESS_TOKEN` (JWT) é obtido via login no Supabase e enviado no header `Authorization: Bearer <token>` para a Edge Function de correção, seguindo o padrão OAuth 2.0 Bearer Token (RFC 6750).
