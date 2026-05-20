import csv
import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


START_URL = "https://diariodarepublica.pt/dr/legislacao-por-tema"

OUTPUT_DIR = Path("dre_temas_output")
PDF_DIR = OUTPUT_DIR / "pdfs_em_vigor"
OUTPUT_DIR.mkdir(exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)

JSON_OUTPUT = OUTPUT_DIR / "links_por_tema_em_vigor.json"
CSV_OUTPUT = OUTPUT_DIR / "links_por_tema_em_vigor.csv"
FAILED_JSON = OUTPUT_DIR / "pdfs_falhados.json"

THEMES = [
    "Administração",
    "Administração Pública",
    "Agricultura",
    "Ambiente",
    "Animais",
    "Armas",
    "Arrendamento",
    "Atividade Empresarial",
    "Atividade Parlamentar",
    "Automóveis",
    "Banca",
    "Caça",
    "Cidadania",
    "Civil",
    "Comercial",
    "Comunicação Social",
    "Constitucional",
    "Consumo",
    "Contabilidade Financeira",
    "Contratação Pública",
    "Cultura",
    "Desporto",
    "Direito Marítimo",
    "Educação e Ensino",
    "Eleições",
    "Empresas",
    "Energia",
    "Estrangeiros",
    "Família e Menores",
    "Fiscal",
    "Igualdade de Género",
    "Justiça",
    "Mediação",
    "Medicina",
    "Ordens Profissionais",
    "Penal",
    "Pescas",
    "Propriedade Industrial e Intelectual",
    "Proteção Civil e Socorro",
    "Publicidade",
    "Registos e Notariado",
    "Relações Internacionais",
    "Saúde",
    "Segurança Alimentar",
    "Segurança Interna",
    "Segurança Rodoviária",
    "Segurança Social",
    "Seguros",
    "Serviços Públicos Essenciais",
]


def clean_text(text: str) -> str:
    text = text or ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_filename(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"[^\w\s\-\.]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "_", text)
    return text[:160]


def accept_cookies(page):
    selectors = [
        "button:has-text('Aceitar')",
        "button:has-text('Aceito')",
        "button:has-text('Concordo')",
        "button:has-text('Permitir')",
        "text=Aceitar",
        "text=Aceito",
    ]

    for selector in selectors:
        try:
            element = page.locator(selector).first
            if element.count() > 0:
                element.click(timeout=3000)
                page.wait_for_timeout(1000)
                return
        except Exception:
            pass


def open_start_page(page):
    page.goto(START_URL, wait_until="domcontentloaded", timeout=90000)
    accept_cookies(page)
    page.wait_for_selector("text=Administração", timeout=60000)
    page.wait_for_timeout(1500)


def click_theme(page, theme_name: str) -> bool:
    print(f"A clicar no tema: {theme_name}")

    try:
        page.get_by_text(theme_name, exact=True).first.click(timeout=10000)
        return True
    except Exception:
        pass

    try:
        clicked = page.evaluate(
            """
            (themeName) => {
                const normalize = (s) => (s || "").trim().replace(/\\s+/g, " ");

                const candidates = Array.from(
                    document.querySelectorAll("a, button, div, span")
                );

                for (const el of candidates) {
                    if (
                        el.closest("header") ||
                        el.closest("footer") ||
                        el.closest("nav")
                    ) {
                        continue;
                    }

                    if (normalize(el.innerText) === themeName) {
                        el.scrollIntoView({block: "center"});
                        el.click();
                        return true;
                    }
                }

                return false;
            }
            """,
            theme_name,
        )

        return bool(clicked)

    except Exception:
        return False


def wait_results_page(page):
    try:
        page.wait_for_load_state("networkidle", timeout=90000)
    except Exception:
        pass

    page.wait_for_timeout(3000)

    selectors = [
        "text=Ordenar por",
        "text=resultados",
        "text=Diário da República",
        "text=Em vigor",
        "text=Revogado",
    ]

    for selector in selectors:
        try:
            page.wait_for_selector(selector, timeout=15000)
            return True
        except Exception:
            continue

    return False


def scroll_until_all_loaded(page, max_scrolls: int = 20):
    print("A fazer scroll para carregar todos os resultados...")

    previous_text_length = 0
    stable_rounds = 0

    for i in range(max_scrolls):
        before = len(page.locator("body").inner_text(timeout=10000))

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1200)

        after = len(page.locator("body").inner_text(timeout=10000))

        print(f"  Scroll {i + 1}: text {before} -> {after}")

        if after == previous_text_length:
            stable_rounds += 1
        else:
            stable_rounds = 0

        previous_text_length = after

        if stable_rounds >= 2:
            break

    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(800)


def extract_active_result_cards(page, theme_name: str) -> list[dict]:
    results = page.evaluate(
        """
        (themeName) => {
            const normalize = (s) => (s || "").trim().replace(/\\s+/g, " ");

            function looksLikeDiplomaTitle(text) {
                if (!text) return false;

                const hasDR =
                    text.includes("Diário da República n.º") ||
                    text.includes("Diário da República n.") ||
                    text.includes("Diário da República nº");

                const hasLegalType =
                    /\\b(Lei|Decreto-Lei|Portaria|Despacho|Regulamento|Resolução|Aviso|Decreto Regulamentar|Declaração|Acórdão)\\b/.test(text);

                return hasDR && hasLegalType;
            }

            function getStatusFromText(text) {
                if (text.includes("Em vigor")) return "Em vigor";
                if (text.includes("Revogado")) return "Revogado";
                if (text.includes("Caducado")) return "Caducado";
                return "Desconhecido";
            }

            function findCard(el, title) {
                let current = el;
                let best = el;
                let bestScore = -1;

                for (let i = 0; i < 18; i++) {
                    if (!current) break;

                    const text = normalize(current.innerText);
                    const rect = current.getBoundingClientRect();

                    if (!text || rect.width <= 0 || rect.height <= 0) {
                        current = current.parentElement;
                        continue;
                    }

                    let score = 0;

                    if (text.includes(title)) score += 4;
                    if (text.includes("Série:")) score += 3;
                    if (text.includes("Emitente:")) score += 3;
                    if (text.includes("Em vigor")) score += 5;
                    if (text.includes("Revogado")) score += 5;
                    if (text.includes("Caducado")) score += 5;

                    if (rect.width > 600) score += 1;
                    if (rect.height > 80) score += 1;
                    if (rect.height > 700) score -= 5;

                    if (score > bestScore) {
                        bestScore = score;
                        best = current;
                    }

                    current = current.parentElement;
                }

                return best;
            }

            function extractSummary(raw, title) {
                let text = normalize(raw.replace(title, ""));

                const statusWords = ["Em vigor", "Revogado", "Caducado"];

                for (const status of statusWords) {
                    text = normalize(text.replace(status, ""));
                }

                const serieIndex = text.indexOf("Série:");
                if (serieIndex >= 0) {
                    return normalize(text.slice(0, serieIndex));
                }

                return text;
            }

            function extractSeries(raw) {
                const match = raw.match(/Série:\\s*([^\\-]+)\\s*-\\s*Emitente:/);
                return match ? normalize(match[1]) : "";
            }

            function extractIssuer(raw) {
                const match = raw.match(/Emitente:\\s*(.*?)(Em vigor|Revogado|Caducado|$)/);
                return match ? normalize(match[1]) : "";
            }

            const anchors = Array.from(document.querySelectorAll("a[href]"));
            const out = [];

            for (const a of anchors) {
                if (
                    a.closest("header") ||
                    a.closest("footer") ||
                    a.closest("nav")
                ) {
                    continue;
                }

                const title = normalize(a.innerText);
                const href = a.href || a.getAttribute("href");

                if (!looksLikeDiplomaTitle(title)) {
                    continue;
                }

                const card = findCard(a, title);
                const cardText = normalize(card.innerText);
                const status = getStatusFromText(cardText);

                if (status !== "Em vigor") {
                    continue;
                }

                out.push({
                    theme: themeName,
                    title,
                    url: href,
                    status,
                    summary: extractSummary(cardText, title),
                    series: extractSeries(cardText),
                    issuer: extractIssuer(cardText)
                });
            }

            return out;
        }
        """,
        theme_name,
    )

    return deduplicate_by_url(results)


def deduplicate_by_url(items: list[dict]) -> list[dict]:
    seen = set()
    unique = []

    for item in items:
        url = item.get("url")

        if not url:
            continue

        if url in seen:
            continue

        seen.add(url)
        unique.append(item)

    return unique


def build_pdf_path(item: dict) -> Path:
    theme = safe_filename(item.get("theme", "sem_tema"))
    title = safe_filename(item.get("title", "sem_titulo"))

    theme_dir = PDF_DIR / theme
    theme_dir.mkdir(parents=True, exist_ok=True)

    return theme_dir / f"{title}.pdf"


def try_click_pdf_with_download(page, output_path: Path) -> bool:
    selectors = [
        "a:has-text('PDF')",
        "button:has-text('PDF')",
        "text=PDF",
        "[aria-label*='PDF']",
        "[title*='PDF']",
    ]

    for selector in selectors:
        try:
            locator = page.locator(selector).first

            if locator.count() == 0:
                continue

            with page.expect_download(timeout=90000) as download_info:
                locator.click(timeout=15000)

            download = download_info.value
            download.save_as(str(output_path))

            return True

        except Exception:
            continue

    return False


def try_find_pdf_url_and_download(page, output_path: Path) -> bool:
    pdf_urls = page.evaluate(
        """
        () => {
            const urls = new Set();

            for (const a of Array.from(document.querySelectorAll("a[href]"))) {
                const href = a.href || "";

                if (
                    href.toLowerCase().includes(".pdf") ||
                    href.toLowerCase().includes("pdf")
                ) {
                    urls.add(href);
                }
            }

            return Array.from(urls);
        }
        """
    )

    for pdf_url in pdf_urls:
        try:
            response = page.request.get(pdf_url, timeout=90000)

            if not response.ok:
                continue

            body = response.body()

            if not body.startswith(b"%PDF"):
                continue

            output_path.write_bytes(body)
            return True

        except Exception:
            continue

    return False


def try_click_pdf_icon_by_position(page, output_path: Path) -> bool:
    candidates = page.evaluate(
        """
        () => {
            const elements = Array.from(document.querySelectorAll("a, button, div, span"));

            return elements.map((el, index) => {
                const rect = el.getBoundingClientRect();
                const text = (el.innerText || "").trim().replace(/\\s+/g, " ");
                const aria = el.getAttribute("aria-label") || "";
                const title = el.getAttribute("title") || "";
                const cls = el.className ? String(el.className) : "";

                const joined = `${text} ${aria} ${title} ${cls}`.toLowerCase();

                return {
                    index,
                    joined,
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height
                };
            }).filter(item => {
                if (item.y > 160) return false;
                if (item.x < window.innerWidth * 0.60) return false;

                return item.joined.includes("pdf");
            });
        }
        """
    )

    for candidate in candidates:
        try:
            with page.expect_download(timeout=90000) as download_info:
                page.evaluate(
                    """
                    (index) => {
                        const elements = Array.from(document.querySelectorAll("a, button, div, span"));
                        const el = elements[index];

                        if (!el) return false;

                        const clickable =
                            el.closest("a") ||
                            el.closest("button") ||
                            el.closest("[role='button']") ||
                            el;

                        clickable.click();
                        return true;
                    }
                    """,
                    candidate["index"],
                )

            download = download_info.value
            download.save_as(str(output_path))

            return True

        except Exception:
            continue

    return False


def download_pdf_for_item(page, item: dict) -> bool:
    output_path = build_pdf_path(item)

    if output_path.exists() and output_path.stat().st_size > 1000:
        print(f"[SKIP] PDF já existe: {output_path}")
        return True

    print(f"A abrir diploma: {item['title']}")
    print(item["url"])

    try:
        page.goto(item["url"], wait_until="domcontentloaded", timeout=90000)
        accept_cookies(page)

        try:
            page.wait_for_load_state("networkidle", timeout=90000)
        except Exception:
            pass

        page.wait_for_timeout(2500)

        body_text = page.locator("body").inner_text(timeout=15000)

        if "Em vigor" not in body_text:
            print("[IGNORADO] Página já não parece estar Em vigor.")
            return False

        if try_click_pdf_with_download(page, output_path):
            print(f"[OK] PDF guardado: {output_path}")
            return True

        if try_find_pdf_url_and_download(page, output_path):
            print(f"[OK] PDF guardado via URL direta: {output_path}")
            return True

        if try_click_pdf_icon_by_position(page, output_path):
            print(f"[OK] PDF guardado via ícone: {output_path}")
            return True

        print("[ERRO] Não consegui encontrar o PDF.")
        return False

    except Exception as e:
        print(f"[ERRO] Falhou download: {e}")
        return False


def scrape_theme_and_download_pdfs(page, theme_name: str) -> tuple[list[dict], list[dict]]:
    print("\n==============================")
    print(f"A processar tema: {theme_name}")
    print("==============================")

    open_start_page(page)

    clicked = click_theme(page, theme_name)

    if not clicked:
        print(f"[ERRO] Não consegui clicar no tema: {theme_name}")
        return [], []

    ok = wait_results_page(page)

    print(f"URL atual: {page.url}")

    if not ok:
        print(f"[AVISO] Não confirmei resultados visíveis para: {theme_name}")
        return [], []

    scroll_until_all_loaded(page)

    active_links = extract_active_result_cards(page, theme_name)

    print(f"Resultados em vigor encontrados: {len(active_links)}")

    failed = []

    for item in active_links:
        print(f"\n- [Em vigor] {item['title']}")

        ok = download_pdf_for_item(page, item)

        if not ok:
            failed.append(item)

        time.sleep(1.5)

        # voltar à página do tema para continuar, se necessário
        # como abrimos cada diploma na mesma tab, precisamos voltar à pesquisa
        try:
            page.go_back(wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1000)
        except Exception:
            pass

    return active_links, failed


def save_outputs(all_links: list[dict], failed: list[dict]):
    all_links = deduplicate_by_url(all_links)
    failed = deduplicate_by_url(failed)

    JSON_OUTPUT.write_text(
        json.dumps(all_links, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    FAILED_JSON.write_text(
        json.dumps(failed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fieldnames = [
        "theme",
        "title",
        "url",
        "status",
        "summary",
        "series",
        "issuer",
    ]

    with CSV_OUTPUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(all_links)


def main():
    all_links = []
    all_failed = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=100,
        )

        context = browser.new_context(
            accept_downloads=True,
            viewport={"width": 1800, "height": 1100},
            locale="pt-PT",
            user_agent="Law-Agent-Student-Project/0.1",
        )

        page = context.new_page()

        # Para testar só um:
        # themes_to_scrape = ["Administração"]

        # Para todos:
        themes_to_scrape = THEMES

        for theme in themes_to_scrape:
            links, failed = scrape_theme_and_download_pdfs(page, theme)
            all_links.extend(links)
            all_failed.extend(failed)

            save_outputs(all_links, all_failed)

            time.sleep(2)

        browser.close()

    print("\nConcluído.")
    print(f"Links em vigor encontrados: {len(deduplicate_by_url(all_links))}")
    print(f"PDFs falhados: {len(deduplicate_by_url(all_failed))}")
    print(f"PDFs guardados em: {PDF_DIR}")
    print(f"JSON: {JSON_OUTPUT}")
    print(f"CSV: {CSV_OUTPUT}")
    print(f"Falhados: {FAILED_JSON}")


if __name__ == "__main__":
    main()