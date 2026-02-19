import os
import re
import yaml
import time
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION ---
# List the Beecrowd Problem IDs you want to clone
PROBLEM_IDS = [
    # 2485, # LAB01-A - Mensagem na Caixa
    # 2487, # LAB01-B - Poeminha do Contra
    # 2093, # LAB02-A - Tempo de viagem
    # 2094, # LAB02-B - Salário mensal
    # 2095, # LAB02-C - Pagamento parcelado
    # 2096, # LAB02-D - Conta de luz
    # 2097, # LAB02-E - Cálculo do peso ideal
    # 2146, # LAB03-A - Maior Idade
    # 2147, # LAB03-B - Passou ou Repetiu
    # 2148, # LAB03-C - Par ou Ímpar
    # 2150, # LAB03-D - Classe Eleitoral
    # 2151, # LAB03-E - Dia da Semana
    # 2152, # LAB03-F - Conceito Simplificado
    # 2153, # LAB03-G - Classes para vacinar
    # 2154, # LAB03-H - Operações ternárias
    # 2155, # LAB03-I - Valor de multa
    # 2164, # LAB04-A - Conceitos
    # 2182, # LAB04-C - Ordenações
    # 2183, # LAB04-D - Múltipla Escolha
    # 2184, # LAB04-E - Números pares ordenados
    # 2185, # LAB04-F - Números ímpares ordenados
    # 2186, # LAB04-G - Menu
    # 2187, # LAB05-A - Número Secreto Avançado
    # 2188, # LAB05-B - Conceitos Avançados
    # 2189, # LAB05-C - Médias dos Aprovados e Reprovados
    # 2195, # LAB05-D - Balanço do Mês
    # 2196, # LAB05-E - Algoritmo de Euclides
    # 2197, # LAB05-F - Tabuadas
    # 2198, # LAB05-G - Conjectura de Collatz
    # 2212, # LAB06-A - Soma de números em um intervalo
    # 2213, # LAB06-C - Retângulo de Asteriscos
    # 2219, # LAB06-B - Imposto de Renda
    # 2220, # LAB06-E - Pesquisa
    # 2106, # LAB07-A - Média das temperaturas do ano
    # 2111, # LAB07-B - Enquete
    # 2113, # LAB07-C - Torneio
    # 2114, # LAB07-D - Carros mais econômicos
    # 2250, # LAB08-B - Sequência de DNA
    # 2249, # LAB08-A - Anagrama
    # 2251, # LAB08-C - Palíndromo
    # 2252, # LAB08-D - Ocorrência de strings
    # 2253, # LAB08-E - Substituição de palavra
    # 2275, # LAB09-B - Mala Direta
    # 2273, # LAB09-A - Ocorrência e Frequência
    # 2611, # LAB09-C - Mês do Inventário UFRGS
    # 2279, # LAB10-A - Palavra de trás para frente
    # 2280, # LAB10-B - Moldura
    # 2281, # LAB10-C - Função de Ackermann
    # 2282, # LAB10-D - Fatorial de um número
    # 2283, # LAB10-E - Múltiplos de 3 e 5
    # 2314, # LAB11-B - Repetindo Palavras
    # 2317, # LAB11-C - Convertendo horas
    # 2318, # LAB11-D - Números primos
    # 2967, # LAB11-A - Módulo Statistics
    # 2265, # LAB13-A - Retângulo
    # 2266, # LAB13-B - Distância Euclidiana
    # 2268, # LAB13-C - Fatura de uma venda
    # 2324, # LAB14-A - Informações sobre alunos
    # 2325, # LAB14-B - Informações sobre produtos
    # 2326, # LAB14-C - Aposentadoria de jogadores
    # 2488, # EP01-A - Fantasma
    # 2489, # EP01-B - Cubo
    # 2490, # EP01-C - Coelho
    # 1973, # EP02-A - Média ponderada
    # 1975, # EP02-B - Moedas
    # 2086, # EP02-Pyhon - Conversão de segundos
    # 2087, # EP02-D - Operações básicas
    # 2089, # EP02-E - Conversão de moedas
    # 1978, # EP03-H - Triângulo
    # 2108, # EP03-A - Poluição
    # 2143, # EP03-B - Alturas
    # 2144, # EP03-C - Quadrante
    # 2145, # EP03-D - IMC
    # 2156, # EP03-E - Crédito bancário
    # 2157, # EP03-F - Calculadora simples
    # 2158, # EP03-G - Fornecimento de energia elétrica
    # 2173, # EP04-A - Índice de massa corporal (IMC)
    # 2174, # EP04-B - Óvos de Páscoa
    # 2175, # EP04-C - Consumo de Energia Elétrica
    # 2176, # EP04-D - Eleição
    # 2199, # EP05-A - Pesquisa no Bairro
    # 2200, # EP05-B - Hamburgueria
    # 2201, # EP05-C - Pet Shop
    # 2214, # EP05-D - Aproximação da Raiz Quadrada
    # 2209, # EP06-A - Decaimento Radioativo
    # 2210, # EP06-B - Cálculo do seno aproximado
    # 2211, # EP06-C - Números Amigos
    # 2115, # EP07-A - Sorteio
    # 2142, # EP07-B - Vendas online
    # 2217, # EP07-C - Campeonato Brasileiro
    # 2256, # EP08-C - Nível de senha
    # 2254, # EP08-A - Número por extenso
    # 2255, # EP08-B - Formatador de Referências
    # 2274, # EP09-A - Histórico de uso de aplicativos
    # 2276, # EP09-B - Pontuação do Texto
    # 2905, # EP09-C - Cifra Imperial
    # 3500, # EP09-D - Contagem da População IBGE 2022
    # 2284, # EP10-A - Data com mês por extenso
    # 2285, # EP10-B - Valor da prestação
    # 2286, # EP10-C - Correspondência de dígitos
    2319, # EP11-A - Tabuada
    # 2320, # EP11-B - Círculo circunscrito em um retângulo
    # 2321, # EP11-C - Cifra de César
    # 2338, # EP11-D - Código Morse
    # 2290, # EP13-A - Conjunto de inteiros
    # 2291, # EP13-B - Adição de Frações
    # 2292, # EP13-C - Flashcard
    # 2393, # EP14-A - Venda de ingressos online
    # 2394, # EP14-B - Recolhimento de imposto
    # 2395, # EP14-C - Cartões de mensagens
    # 2700, # EP14-D - Mês do Inventário UFRGS: A Batalha Final
    # 3654, # EP14-E - Sistema de Registro Acadêmico
    # 4077, # LAB09-D - Convertendo Valores (PISA 2022)
    # 4078, # LAB09-E - Inflação Mensal e Anual
    # 4158, # LAB13-E - Lista de Compras
    # 4159, # LAB13-D - Sistema de RH
]

OUTPUT_DIR = "./assignments_imported"

def sanitize_slug(text):
    """Converts 'EP01-X - Título do Enunciado' to 'ep01-x-titulo-do-enunciado'"""
    # Remove accents/special chars if needed, but for now simple lower/replace is robust
    text = text.lower()
    # Replace ' - ' with '-'
    text = text.replace(' - ', '-')
    # Replace common special chars (ã, é, ç, etc) with unaccented versions
    text = re.sub(r'[áàâãä]', 'a', text)
    text = re.sub(r'[éèêë]', 'e', text)
    text = re.sub(r'[íìîï]', 'i', text)
    text = re.sub(r'[óòôõö]', 'o', text)
    text = re.sub(r'[úùûü]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    text = re.sub(r'[^a-z0-9\s-]', '', text) # Remove other special chars
    text = re.sub(r'\s+', '-', text)         # Replace spaces with -
    return text.strip('-')

def parse_html(html_content, problem_id):
    soup = BeautifulSoup(html_content, 'html.parser')

    # --- 1. HEADER INFO ---
    header_div = soup.find('div', class_='header')
    
    # Title
    title = header_div.find('h1').get_text(strip=True)
    
    # Author (e.g., "Por Carine Beatrici, Brazil")
    author = "Unknown"
    author_p = header_div.find('p')
    if author_p:
        author_text = author_p.get_text().strip()
        # Regex to capture name between "Por" and the comma or end
        match = re.search(r'Por\s+(.*?)(?:,|$)', author_text, re.IGNORECASE)
        if match:
            author = match.group(1).strip()

    # Time Limit
    time_limit = 2.0
    limit_strong = header_div.find('strong')
    if limit_strong:
        # "Timelimit: 2" -> 2.0
        try:
            val = limit_strong.get_text().split(':')[-1].strip()
            time_limit = float(val)
        except:
            pass

    # --- 2. DESCRIPTION (Editor.js Parsing) ---
    description_md = ""
    editor_div = soup.find('div', class_='codex-editor__redactor')
    
    if editor_div:
        for block in editor_div.find_all('div', class_='ce-block'):
            content_div = block.find('div', class_='ce-block__content')
            if not content_div: continue
            
            # Case A: Headers (Entrada / Saída)
            header = content_div.find(['h2', 'h3'], class_='ce-header')
            if header:
                text = header.get_text(strip=True)
                description_md += f"\n## {text}\n\n"
                continue

            # Case B: Paragraphs
            paragraph = content_div.find('div', class_='ce-paragraph')
            if paragraph:
                # Get inner HTML to preserve bold/italic <b> <i>
                # We strip the wrapping div to just get content
                inner = "".join([str(x) for x in paragraph.contents])
                # Convert inner HTML tags to Markdown (**bold**, etc)
                converted_text = md(inner).strip()
                if converted_text:
                    description_md += f"\n{converted_text}\n\n"
                continue

            # Case C: Lists
            list_ul = content_div.find('ul', class_='cdx-list')
            if list_ul:
                # markdownify handles <ul><li> conversion well
                description_md += md(str(list_ul)) + "\n"

    # --- 3. SAMPLES (Tables) ---
    tests = []
    
    # Find all tables (Beecrowd often puts one sample row per table)
    tables = soup.find_all('table')
    sample_count = 1

    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                # Column 0: Input, Column 1: Output
                # We need TWO versions: 
                # 1. Raw text (for config.yaml)
                # 2. HTML text with <br> (for README.md table)
                
                # Helper to get text with newlines
                def get_clean_text(td):
                    # Replace <br> with \n
                    for br in td.find_all("br"):
                        br.replace_with("")
                    return td.get_text().strip()

                raw_input = get_clean_text(cols[0])
                raw_output = get_clean_text(cols[1])
                print("DEBUG", raw_input, raw_output)
                # Skip header rows
                if "Samples Input" in raw_input or "Entrada" in raw_input:
                    continue
                
                # Name the test case
                # If input is small (e.g. "2\n6"), name it "2-6"
                # If large, use "Sample X"
                first_lines = raw_input.split('\n')
                if len(first_lines) <= 2 and len(raw_input) < 15:
                    test_name = "-".join(first_lines).replace(' ', '')
                else:
                    test_name = f"Sample {sample_count}"

                tests.append({
                    "name": test_name,
                    "input": raw_input,
                    "output": raw_output
                })
                sample_count += 1

    return {
        "id": problem_id,
        "title": title,
        "author": author,
        "time_limit": int(time_limit),
        "description": description_md.strip(),
        "tests": tests
    }

def save_to_disk(data):
    # 1. Create Folder
    folder_slug = sanitize_slug(data['title'])
    folder_path = os.path.join(OUTPUT_DIR, folder_slug)
    os.makedirs(folder_path, exist_ok=True)
    
    print(f"   💾 Saving to: {folder_path}/")

    # 2. Create config.yaml
    config_data = {
        "title": data['title'],
        "time_limit": data['time_limit'],
        "memory_limit": 128, # Default
        "author": data['author'],
        "tests": data['tests']
    }
    
    # Custom Dumper to force Literal Block Scalars (|) for multiline strings
    class LiteralDumper(yaml.SafeDumper):
        def represent_scalar(self, tag, value, style=None):
            if '\n' in value:
                style = '|'
            return super().represent_scalar(tag, value, style)

    with open(os.path.join(folder_path, "config.yaml"), "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, Dumper=LiteralDumper, sort_keys=False, allow_unicode=True)

    # 3. Create README.md
    with open(os.path.join(folder_path, "README.md"), "w", encoding="utf-8") as f:
        # Header & Description
        f.write(f"# {data['title']}\n\n")
        f.write(data['description'])
        f.write("\n\n## Exemplos\n\n")
        
        # Build the Markdown Table manually to ensure <br/> formatting
        f.write("| Entrada | Saída |\n")
        f.write("| :--- | :--- |\n")
        
        for test in data['tests']:
            # Convert newlines to <br/> for the table cell
            inp_cell = test['input'].replace('\n', '<br/>')
            out_cell = test['output'].replace('\n', '<br/>')
            f.write(f"| {inp_cell} | {out_cell} |\n")

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
        driver.get("https://judge.beecrowd.com/pt/login")
        
        # INCREASED TIMEOUT: Wait for you to actually log in
        input("👉 Press ENTER in this terminal once you are logged in...")

        # 2. Scraping Phase
        for pid in PROBLEM_IDS:
            print(f"🔄 Processing ID: {pid}...")
            url = f"https://judge.beecrowd.com/pt/custom-problems/fullscreen/{pid}"
            driver.get(url)
            time.sleep(2) 
            
            html = driver.page_source
            data = parse_html(html, pid)
            save_to_disk(data)
            
    finally:
        driver.quit()
        print("✅ Migration Complete.")

if __name__ == "__main__":
    main()