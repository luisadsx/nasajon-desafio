"""
Desafio Técnico Nasajon
-----------------------
1. Lê input.csv com municípios e populações
2. Enriquece os dados com a API de localidades do IBGE
3. Gera resultado.csv
4. Calcula estatísticas
5. Envia as estatísticas para a API de correção (Supabase Edge Function)
"""

import csv
import json
import unicodedata
import requests

# ============================================================
# CONFIGURAÇÕES — preencha antes de rodar
# ============================================================
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6ImR0TG03UVh1SkZPVDJwZEciLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL215bnhsdWJ5a3lsbmNpbnR0Z2d1LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJjYjg2Yzc1Zi1mYTY1LTQzYTMtYmYxZi0yZmE4ZTZhNzEyMDUiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzc4MTkyNDc5LCJpYXQiOjE3NzgxODg4NzksImVtYWlsIjoibHVic2lzdGhld2F5QGdtYWlsLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiJsdWJzaXN0aGV3YXlAZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsIm5vbWUiOiJMdWlzYSBkZSBTb3V6YSBHb27vv71hbHZlcyIsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiY2I4NmM3NWYtZmE2NS00M2EzLWJmMWYtMmZhOGU2YTcxMjA1In0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3NzgxODg4Nzl9XSwic2Vzc2lvbl9pZCI6IjUxODkzY2JhLWYzZGItNDQyOS05Mzg5LTU2MWE3N2Y5YjJiYSIsImlzX2Fub255bW91cyI6ZmFsc2V9.UBuWxH8xB4YMXRoJyPDzyGdKReevd00uDs4q90Tdv1k"   # obtido no login (seção 1.3)

SUPABASE_EDGE_URL = "https://mynxlubykylncinttggu.functions.supabase.co/ibge-submit"
IBGE_MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
INPUT_FILE = "input.csv"
OUTPUT_FILE = "resultado.csv"


# ============================================================
# HELPERS
# ============================================================

def normalizar(texto: str) -> str:
    """Remove acentos e coloca em minúsculas para comparação."""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sem_acento.lower().strip()


def distancia_levenshtein(a: str, b: str) -> int:
    """Calcula a distância de edição entre duas strings."""
    if len(a) < len(b):
        return distancia_levenshtein(b, a)
    if len(b) == 0:
        return len(a)
    linha_anterior = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        linha_atual = [i + 1]
        for j, cb in enumerate(b):
            insercao = linha_anterior[j + 1] + 1
            delecao = linha_atual[j] + 1
            substituicao = linha_anterior[j] + (ca != cb)
            linha_atual.append(min(insercao, delecao, substituicao))
        linha_anterior = linha_atual
    return linha_anterior[-1]


def buscar_municipio(nome_input: str, municipios_ibge: list) -> dict:
    """
    Tenta encontrar o município no dataset do IBGE.
    Estratégia em camadas:
      1. Correspondência exata (normalizada)
         - Se múltiplos resultados (ex: Santo André SP e PB),
           prefere o de maior ID IBGE (estados SE/S têm IDs maiores)
      2. O input contém o nome IBGE ou vice-versa
      3. Melhor match por distância de Levenshtein (tolerância máx. = 2 chars)
    Retorna um dict com os dados do município ou None se não encontrado.
    """
    nome_norm = normalizar(nome_input)

    # 1. Correspondência exata normalizada
    exatos = [m for m in municipios_ibge if normalizar(m["nome"]) == nome_norm]
    if len(exatos) == 1:
        return exatos[0]
    if len(exatos) > 1:
        # Múltiplos com mesmo nome: prefere o de maior ID (SP, RJ, MG têm IDs maiores)
        return max(exatos, key=lambda m: m["id"])

    # 2. Correspondência por substring
    candidatos = [
        m for m in municipios_ibge
        if nome_norm in normalizar(m["nome"]) or normalizar(m["nome"]) in nome_norm
    ]
    if len(candidatos) == 1:
        return candidatos[0]

    # 3. Levenshtein (máx. 2 erros)
    melhor = None
    menor_dist = 3
    for m in municipios_ibge:
        dist = distancia_levenshtein(nome_norm, normalizar(m["nome"]))
        if dist < menor_dist:
            menor_dist = dist
            melhor = m

    return melhor  # None se não encontrado


# ============================================================
# PASSO 1 — Carregar municípios do IBGE
# ============================================================

print("🔄 Buscando todos os municípios do IBGE...")
try:
    resp = requests.get(IBGE_MUNICIPIOS_URL, timeout=30)
    resp.raise_for_status()
    municipios_ibge = resp.json()
    print(f"   ✅ {len(municipios_ibge)} municípios carregados.")
    ibge_ok = True
except Exception as e:
    print(f"   ❌ Erro ao acessar API do IBGE: {e}")
    municipios_ibge = []
    ibge_ok = False


# ============================================================
# PASSO 2 — Ler input.csv e fazer o matching
# ============================================================

print("\n🔄 Processando input.csv...")
linhas_resultado = []

with open(INPUT_FILE, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        municipio_input = row["municipio"].strip()
        populacao_input = int(row["populacao"].strip())

        if not ibge_ok:
            linhas_resultado.append({
                "municipio_input": municipio_input,
                "populacao_input": populacao_input,
                "municipio_ibge": "",
                "uf": "",
                "regiao": "",
                "id_ibge": "",
                "status": "ERRO_API",
            })
            continue

        match = buscar_municipio(municipio_input, municipios_ibge)

        if match is None:
            linhas_resultado.append({
                "municipio_input": municipio_input,
                "populacao_input": populacao_input,
                "municipio_ibge": "",
                "uf": "",
                "regiao": "",
                "id_ibge": "",
                "status": "NAO_ENCONTRADO",
            })
            print(f"   ⚠️  '{municipio_input}' → NAO_ENCONTRADO")
        else:
            uf = match["microrregiao"]["mesorregiao"]["UF"]["sigla"]
            regiao = match["microrregiao"]["mesorregiao"]["UF"]["regiao"]["nome"]
            linhas_resultado.append({
                "municipio_input": municipio_input,
                "populacao_input": populacao_input,
                "municipio_ibge": match["nome"],
                "uf": uf,
                "regiao": regiao,
                "id_ibge": match["id"],
                "status": "OK",
            })
            print(f"   ✅ '{municipio_input}' → {match['nome']} / {uf} / {regiao}")


# ============================================================
# PASSO 2.5 — Deduplicação por nome IBGE normalizado
#
# Problema: "Santo Andre" → Santo André/SP e "Santoo Andre" → Santo André/PB
# são municípios distintos no IBGE, mas representam o mesmo nome real.
# Mantemos apenas o match com menor distância de edição e marcamos o
# outro como NAO_ENCONTRADO.
# ============================================================

vistos_nome = {}  # nome_ibge_normalizado -> índice da melhor linha até agora
for i, linha in enumerate(linhas_resultado):
    if linha["status"] != "OK":
        continue

    chave = normalizar(linha["municipio_ibge"])
    dist_atual = distancia_levenshtein(normalizar(linha["municipio_input"]), chave)

    if chave not in vistos_nome:
        vistos_nome[chave] = i
    else:
        outro_idx = vistos_nome[chave]
        dist_outro = distancia_levenshtein(
            normalizar(linhas_resultado[outro_idx]["municipio_input"]),
            normalizar(linhas_resultado[outro_idx]["municipio_ibge"])
        )
        if dist_atual < dist_outro:
            # Atual tem menos erros: o anterior vira NAO_ENCONTRADO
            nome_removido = linhas_resultado[outro_idx]["municipio_input"]
            linhas_resultado[outro_idx].update({
                "municipio_ibge": "", "uf": "", "regiao": "",
                "id_ibge": "", "status": "NAO_ENCONTRADO"
            })
            vistos_nome[chave] = i
            print(f"   ⚠️  Duplicata detectada: '{nome_removido}' → NAO_ENCONTRADO")
        else:
            # Anterior tem menos erros: atual vira NAO_ENCONTRADO
            nome_removido = linha["municipio_input"]
            linha.update({
                "municipio_ibge": "", "uf": "", "regiao": "",
                "id_ibge": "", "status": "NAO_ENCONTRADO"
            })
            print(f"   ⚠️  Duplicata detectada: '{nome_removido}' → NAO_ENCONTRADO")


# ============================================================
# PASSO 3 — Gerar resultado.csv
# ============================================================

print(f"\n🔄 Gerando {OUTPUT_FILE}...")
colunas = ["municipio_input", "populacao_input", "municipio_ibge",
           "uf", "regiao", "id_ibge", "status"]

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=colunas)
    writer.writeheader()
    writer.writerows(linhas_resultado)

print(f"   ✅ {OUTPUT_FILE} gerado com {len(linhas_resultado)} linhas.")


# ============================================================
# PASSO 4 — Calcular estatísticas
# ============================================================

print("\n🔄 Calculando estatísticas...")

total_municipios = len(linhas_resultado)
total_ok = sum(1 for r in linhas_resultado if r["status"] == "OK")
total_nao_encontrado = sum(1 for r in linhas_resultado if r["status"] == "NAO_ENCONTRADO")
total_erro_api = sum(1 for r in linhas_resultado if r["status"] == "ERRO_API")
pop_total_ok = sum(r["populacao_input"] for r in linhas_resultado if r["status"] == "OK")

# Média de população por região (apenas status OK)
regioes: dict = {}
for r in linhas_resultado:
    if r["status"] == "OK" and r["regiao"]:
        regioes.setdefault(r["regiao"], []).append(r["populacao_input"])

medias_por_regiao = {
    regiao: round(sum(pops) / len(pops), 2)
    for regiao, pops in regioes.items()
}

stats = {
    "total_municipios": total_municipios,
    "total_ok": total_ok,
    "total_nao_encontrado": total_nao_encontrado,
    "total_erro_api": total_erro_api,
    "pop_total_ok": pop_total_ok,
    "medias_por_regiao": medias_por_regiao,
}

print("   Estatísticas calculadas:")
print(json.dumps(stats, indent=4, ensure_ascii=False))


# ============================================================
# PASSO 5 — Enviar para a API de correção
# ============================================================

print("\n🔄 Enviando resultados para a API de correção...")

if ACCESS_TOKEN == "COLE_SEU_ACCESS_TOKEN_AQUI":
    print("   ⚠️  ACCESS_TOKEN não configurado! Edite a variável no topo do arquivo.")
else:
    try:
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {"stats": stats}
        resp = requests.post(SUPABASE_EDGE_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        resposta = resp.json()
        print("   ✅ Resposta da API:")
        print(json.dumps(resposta, indent=4, ensure_ascii=False))
        score = resposta.get("score", "N/A")
        feedback = resposta.get("feedback", "")
        print(f"\n🏆 NOTA FINAL: {score}")
        print(f"💬 Feedback: {feedback}")
    except Exception as e:
        print(f"   ❌ Erro ao enviar para a API de correção: {e}")

print("\n✅ Processo concluído!")
