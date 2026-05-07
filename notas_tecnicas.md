# Notas Técnicas — Decisões do Projeto

## 1. Estratégia de matching de municípios

O `input.csv` contém erros intencionais de digitação (ex: `Belo Horzionte`, `Curitba`, `Santoo Andre`). Para lidar com isso, implementei uma estratégia de matching em três camadas:

1. **Correspondência exata normalizada**: remove acentos e ignora maiúsculas/minúsculas. Resolve casos como `Niteroi` → `Niterói`.
2. **Correspondência por substring**: verifica se o nome do input está contido no nome IBGE ou vice-versa. Útil para nomes parcialmente corretos.
3. **Distância de Levenshtein**: algoritmo clássico de similaridade de strings que conta o número mínimo de edições (inserções, remoções, substituições) para transformar uma string na outra. Tolera até 3 erros, o que cobre casos como `Curitba` → `Curitiba` (1 inserção) e `Belo Horzionte` → `Belo Horizonte` (1 transposição).

### Casos especiais do input
| Entrada | Decisão | Justificativa |
|---|---|---|
| `Belo Horzionte` | OK → Belo Horizonte | Levenshtein = 1 |
| `Curitba` | OK → Curitiba | Levenshtein = 1 |
| `Santoo Andre` | OK → Santo André | Levenshtein = 1 |
| `Santo Andre` | OK → Santo André | Normalização remove acento |

> **Nota**: `Santo Andre` e `Santoo Andre` são duplicatas no input e ambas mapeiam para o mesmo município oficial. Ambas são processadas e incluídas no `resultado.csv` com status `OK`, conforme o CSV de entrada fornecido.

## 2. Carregamento da API do IBGE

Optei por fazer **um único GET** para `https://servicodados.ibge.gov.br/api/v1/localidades/municipios`, carregando todos os ~5.570 municípios em memória. Isso é mais eficiente do que fazer uma chamada por município, reduz a latência total e evita sobrecarregar a API pública com múltiplas requisições.

## 3. Tratamento de erros

- `ERRO_API`: quando a API do IBGE está indisponível (exception na requisição HTTP).
- `NAO_ENCONTRADO`: quando nenhum dos algoritmos de matching encontra correspondência com distância aceitável.
- O programa continua processando as demais linhas mesmo se uma falhar.

## 4. Estatísticas

- `pop_total_ok`: soma apenas municípios com status `OK`, excluindo os não encontrados.
- `medias_por_regiao`: calculada com base na `populacao_input` (dado fornecido), não no censo do IBGE, conforme especificação.
- Municípios duplicados (ex: `Santo Andre` e `Santoo Andre`) são contados separadamente nas estatísticas, pois são linhas independentes do input.

## 5. Autenticação

O `ACCESS_TOKEN` (JWT) é obtido via login no Supabase e enviado no header `Authorization: Bearer <token>` para a Edge Function de correção, seguindo o padrão OAuth 2.0 Bearer Token (RFC 6750).
