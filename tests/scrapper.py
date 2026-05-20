import os
from playwright.sync_api import sync_playwright

PASTA_BASE = "Arquivos"
TEMAS = ["Agricultura"] # Eu manualmente deixei apenas agricultura para um teste

def executar_scrapper():
    os.makedirs(PASTA_BASE, exist_ok=True)

    with sync_playwright() as p:
        # slow_mo=500 é vital em sites React/OutSystems. Obriga o robô a abrandar
        # meio segundo por cada ação, dando tempo ao site para "respirar".
        navegador = p.chromium.launch(headless=False, slow_mo=500)
        contexto = navegador.new_context(accept_downloads=True)
        pagina = contexto.new_page()

        for tema in TEMAS:
            print(f"\n--- 🔍 A explorar o tema: {tema} ---")
            pasta_tema = os.path.join(PASTA_BASE, tema.lower())
            os.makedirs(pasta_tema, exist_ok=True)

            try:
                # 1. Carregar a página principal
                print("   [+] A aceder à página principal de Temas...")
                pagina.goto("https://diariodarepublica.pt/dr/legislacao-por-tema", wait_until="domcontentloaded", timeout=60000)
                
                # Em vez de testar logo se existe, MANDAMOS o Playwright esperar ativamente pelo botão!
                seletor_botao = f"button[title='{tema}']"
                print(f"   [+] À espera que o botão '{tema}' seja renderizado pelo Governo...")
                pagina.wait_for_selector(seletor_botao, state="visible", timeout=30000)

                # Scroll até ao botão para garantir que não está escondido e clicar
                botao_tema = pagina.locator(seletor_botao)
                botao_tema.scroll_into_view_if_needed()
                
                print(f"   [+] A clicar no botão '{tema}'...")
                botao_tema.click()

                # 2. Esperar que a página mude para os resultados de pesquisa
                print("   [+] À espera que a pesquisa carregue a lista de leis...")
                # Esperamos especificamente que o primeiro link de uma lei apareça no ecrã
                seletor_lei = "a[href*='/dr/detalhe/'], a[href*='/dr/legislacao-consolidada/']"
                pagina.wait_for_selector(seletor_lei, state="visible", timeout=30000)
                
                # Pequeno scroll e pausa natural para garantir que as listas terminam de carregar
                pagina.mouse.wheel(0, 1000)
                pagina.wait_for_timeout(3000)

                # 3. Extrair os links das leis
                elementos_a = pagina.locator(seletor_lei).element_handles()
                links_das_leis = []
                for a in elementos_a:
                    href = a.get_attribute("href")
                    if href:
                        link_completo = f"https://diariodarepublica.pt{href}" if href.startswith("/") else href
                        if link_completo not in links_das_leis:
                            links_das_leis.append(link_completo)

                print(f"   [+] Sucesso! Encontradas {len(links_das_leis)} leis.")

                # 4. Entrar em cada lei e baixar
                for i, link_lei in enumerate(links_das_leis[:10]): # Lembrete: tira o [:10] se quiseres todas!
                    try:
                        print(f"\n       -> A abrir a lei {i+1}: {link_lei}")
                        pagina.goto(link_lei, wait_until="domcontentloaded", timeout=60000)
                        
                        # Esperar ativamente pelo botão de PDF em vez de apenas ver se ele existe
                        seletor_pdf = 'a[title="Versão PDF"]'
                        
                        try:
                            # Dá até 15 segundos para o botão do PDF carregar na página da lei
                            pagina.wait_for_selector(seletor_pdf, state="attached", timeout=15000)
                            botao_pdf = pagina.locator(seletor_pdf).first
                            
                            # O nosso Truque Mágico: Remover o target="_blank"
                            botao_pdf.evaluate("node => node.removeAttribute('target')")
                            
                            print("          [Download] Botão PDF encontrado! A iniciar transferência...")
                            with pagina.expect_download(timeout=30000) as download_info:
                                botao_pdf.click(force=True)

                            download = download_info.value
                            caminho_ficheiro = os.path.join(pasta_tema, download.suggested_filename)
                            download.save_as(caminho_ficheiro)

                            print(f"          ✅ PDF Guardado: {download.suggested_filename}")
                        except Exception:
                            print("          ⚠️ Botão 'Versão PDF' não apareceu no ecrã (Pode não existir ficheiro para esta lei).")

                    except Exception as e_lei:
                        print(f"          ❌ Erro ao processar a lei {i+1}: {e_lei}")

            except Exception as e_tema:
                print(f"   ❌ Erro crítico ao processar o tema {tema}: {e_tema}")

        navegador.close()
        print("\n🎉 Extração concluída!")

if __name__ == "__main__":
    executar_scrapper()