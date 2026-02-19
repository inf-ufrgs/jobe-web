import os
import re
import yaml
import time
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import migrate_beecrowd  # Ensure dependencies are met

# --- CONFIGURATION ---
# List the Beecrowd Problem IDs you want to clone
PROBLEM_IDS = {
    # 2485: "LAB01-A - Mensagem na Caixa",
    # 2487: "LAB01-B - Poeminha do Contra",
    # 2093: "LAB02-A - Tempo de viagem",
    # 2094: "LAB02-B - Salário mensal",
    # 2095: "LAB02-C - Pagamento parcelado",
    # 2096: "LAB02-D - Conta de luz",
    # 2097: "LAB02-E - Cálculo do peso ideal",
    # 2146: "LAB03-A - Maior Idade",
    # 2147: "LAB03-B - Passou ou Repetiu",
    # 2148: "LAB03-C - Par ou Ímpar",
    # 2150: "LAB03-D - Classe Eleitoral",
    # 2151: "LAB03-E - Dia da Semana",
    # 2152: "LAB03-F - Conceito Simplificado",
    # 2153: "LAB03-G - Classes para vacinar",
    # 2154: "LAB03-H - Operações ternárias",
    # 2155: "LAB03-I - Valor de multa",
    # 2164: "LAB04-A - Conceitos",
    # 2182: "LAB04-C - Ordenações",
    # 2183: "LAB04-D - Múltipla Escolha",
    # 2184: "LAB04-E - Números pares ordenados",
    # 2185: "LAB04-F - Números ímpares ordenados",
    # 2186: "LAB04-G - Menu",
    # 2187: "LAB05-A - Número Secreto Avançado",
    # 2188: "LAB05-B - Conceitos Avançados",
    # 2189: "LAB05-C - Médias dos Aprovados e Reprovados",
    # 2195: "LAB05-D - Balanço do Mês",
    # 2196: "LAB05-E - Algoritmo de Euclides",
    # 2197: "LAB05-F - Tabuadas",
    # 2198: "LAB05-G - Conjectura de Collatz",
    # 2212: "LAB06-A - Soma de números em um intervalo",
    # 2213: "LAB06-C - Retângulo de Asteriscos",
    # 2219: "LAB06-B - Imposto de Renda",
    # 2220: "LAB06-E - Pesquisa",
    # 2106: "LAB07-A - Média das temperaturas do ano",
    # 2111: "LAB07-B - Enquete",
    # 2113: "LAB07-C - Torneio",
    # 2114: "LAB07-D - Carros mais econômicos",
    # 2250: "LAB08-B - Sequência de DNA",
    # 2249: "LAB08-A - Anagrama",
    # 2251: "LAB08-C - Palíndromo",
    # 2252: "LAB08-D - Ocorrência de strings",
    # 2253: "LAB08-E - Substituição de palavra",
    # 2275: "LAB09-B - Mala Direta",
    # 2273: "LAB09-A - Ocorrência e Frequência",
    # 2611: "LAB09-C - Mês do Inventário UFRGS",
    # 2279: "LAB10-A - Palavra de trás para frente",
    # 2280: "LAB10-B - Moldura",
    # 2281: "LAB10-C - Função de Ackermann",
    # 2282: "LAB10-D - Fatorial de um número",
    # 2283: "LAB10-E - Múltiplos de 3 e 5",
    # 2314: "LAB11-B - Repetindo Palavras",
    # 2317: "LAB11-C - Convertendo horas",
    # 2318: "LAB11-D - Números primos",
    # 2967: "LAB11-A - Módulo Statistics",
    # 2265: "LAB13-A - Retângulo",
    # 2266: "LAB13-B - Distância Euclidiana",
    # 2268: "LAB13-C - Fatura de uma venda",
    # 2324: "LAB14-A - Informações sobre alunos",
    # 2325: "LAB14-B - Informações sobre produtos",
    # 2326: "LAB14-C - Aposentadoria de jogadores",
    # 2488: "EP01-A - Fantasma",
    # 2489: "EP01-B - Cubo",
    # 2490: "EP01-C - Coelho",
    # 1973: "EP02-A - Média ponderada",
    # 1975: "EP02-B - Moedas",
    # 2086: "EP02-Pyhon - Conversão de segundos",
    # 2087: "EP02-D - Operações básicas",
    # 2089: "EP02-E - Conversão de moedas",
    # 1978: "EP03-H - Triângulo",
    # 2108: "EP03-A - Poluição",
    # 2143: "EP03-B - Alturas",
    # 2144: "EP03-C - Quadrante",
    # 2145: "EP03-D - IMC",
    # 2156: "EP03-E - Crédito bancário",
    # 2157: "EP03-F - Calculadora simples",
    # 2158: "EP03-G - Fornecimento de energia elétrica",
    # 2173: "EP04-A - Índice de massa corporal (IMC)",
    # 2174: "EP04-B - Óvos de Páscoa",
    # 2175: "EP04-C - Consumo de Energia Elétrica",
    # 2176: "EP04-D - Eleição",
    # 2199: "EP05-A - Pesquisa no Bairro",
    # 2200: "EP05-B - Hamburgueria",
    # 2201: "EP05-C - Pet Shop",
    # 2214: "EP05-D - Aproximação da Raiz Quadrada",
    # 2209: "EP06-A - Decaimento Radioativo",
    # 2210: "EP06-B - Cálculo do seno aproximado",
    # 2211: "EP06-C - Números Amigos",
    # 2115: "EP07-A - Sorteio",
    # 2142: "EP07-B - Vendas online",
    # 2217: "EP07-C - Campeonato Brasileiro",
    # 2256: "EP08-C - Nível de senha",
    # 2254: "EP08-A - Número por extenso",
    # 2255: "EP08-B - Formatador de Referências",
    # 2274: "EP09-A - Histórico de uso de aplicativos",
    # 2276: "EP09-B - Pontuação do Texto",
    # 2905: "EP09-C - Cifra Imperial",
    # 3500: "EP09-D - Contagem da População IBGE 2022",
    # 2284: "EP10-A - Data com mês por extenso",
    # 2285: "EP10-B - Valor da prestação",
    # 2286: "EP10-C - Correspondência de dígitos",
    # 2321: "EP11-C - Cifra de César",
    # 2320: "EP11-B - Círculo circunscrito em um retângulo",
    # 2338: "EP11-D - Código Morse",
    2319: "EP11-A - Tabuada",
    # 2290: "EP13-A - Conjunto de inteiros",
    # 2291: "EP13-B - Adição de Frações",
    # 2292: "EP13-C - Flashcard",
    # 2393: "EP14-A - Venda de ingressos online",
    # 2394: "EP14-B - Recolhimento de imposto",
    # 2395: "EP14-C - Cartões de mensagens",
    # 2700: "EP14-D - Mês do Inventário UFRGS: A Batalha Final",
    # # Problems without README.md and config.yaml
    # 3654: "EP14-E - Sistema de Registro Acadêmico",
    # 4077: "LAB09-D - Convertendo Valores (PISA 2022)",
    # 4078: "LAB09-E - Inflação Mensal e Anual",
    # 4158: "LAB13-E - Lista de Compras",
    # 4159: "LAB13-D - Sistema de RH",
}

OUTPUT_DIR = migrate_beecrowd.OUTPUT_DIR

def parse_html(html_content, problem_id, problem_name):
    soup = BeautifulSoup(html_content, 'html.parser')

    # --- 1. GET TEXTAREA WITH SOURCE CODE ---
    textarea = soup.find('textarea', id='source-code')
    if not textarea:
        raise ValueError("Could not find source code textarea.")
    source_code = textarea.get_text()

    return {
        "id": problem_id,
        "title": problem_name,
        "source_code": source_code
    }

def save_to_disk(data):
    # 1. Verify if the folder exists
    folder_slug = migrate_beecrowd.sanitize_slug(data['title'])
    folder_path = os.path.join(OUTPUT_DIR, folder_slug)
    # Check if folder exists
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    print(f"   💾 Saving to: {folder_path}/")

    # 2. Create config.yaml
    config_data = {
        "title": data['title'],
        "source": data['source_code']
    }
    
    # Create a file named solution.py with the source code if the file does not exist
    solution_path = os.path.join(folder_path, "solution.py")
    if os.path.exists(solution_path):
        print(f"   ⚠️ solution.py already exists. Skipping to avoid overwrite.")
        return
    with open(solution_path, 'w', encoding='utf-8') as f:
        f.write(data['source_code'])
    print(f"   💾 Saved source code to: {solution_path}")

def main():
    # Setup Chrome Options
    options = webdriver.ChromeOptions()
    
    # --- CRITICAL FIXES FOR LINUX ---
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    
    # If you are running on a server without a monitor (e.g., SSH/WSL), 
    # you MUST uncomment the next line.
    # However, this makes "Manual Login" impossible. 
    # See "Step 3" below if you are on a headless server.
    # options.add_argument("--headless") 

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"❌ Error initializing Chrome: {e}")
        print("Tip: Make sure Google Chrome is installed (not just Chromium).")
        return

    try:
        # 1. Login Phase
        print("👉 OPENING BROWSER. Log in to Beecrowd manually.")
        driver.get("https://academic.beecrowd.com/pt/login")
        
        # INCREASED TIMEOUT: Wait for you to actually log in
        input("👉 Press ENTER in this terminal once you are logged in...")

        # 2. Scraping Phase
        for pid in PROBLEM_IDS:
            print(f"🔄 Processing ID: {pid}...")
            url = f"https://academic.beecrowd.com/pt/custom-problems/editcode/{pid}/1"
            driver.get(url)
            time.sleep(2)
            
            html = driver.page_source
            data = parse_html(html, pid, PROBLEM_IDS[pid])
            save_to_disk(data)
            
    finally:
        driver.quit()
        print("✅ Migration Complete.")

if __name__ == "__main__":
    main()