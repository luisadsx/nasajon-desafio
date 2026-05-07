# Desafio Técnico Nasajon — Curadoria IBGE

## Requisitos
- Python 3.8+
- Biblioteca `requests`

## Instalação
```bash
pip install requests
```

## Como rodar

1. **Criar conta e fazer login** no Supabase (conforme instruções do desafio) para obter o `ACCESS_TOKEN`.

2. **Editar `main.py`**: substituir `"COLE_SEU_ACCESS_TOKEN_AQUI"` pelo token obtido.

3. **Executar**:
```bash
python main.py
```

O programa irá:
- Ler `input.csv`
- Consultar a API do IBGE para enriquecer os dados
- Gerar `resultado.csv`
- Calcular estatísticas
- Enviar automaticamente para a API de correção e exibir a nota no console

## Arquivos
| Arquivo | Descrição |
|---|---|
| `main.py` | Código principal |
| `input.csv` | Arquivo de entrada com municípios e populações |
| `resultado.csv` | Gerado pelo programa após a execução |
| `notas_tecnicas.md` | Decisões técnicas explicadas |
