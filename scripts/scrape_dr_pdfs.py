import argparse
import base64
import csv
import json
import re
from pathlib import Path
from typing import Any

# import do playwright
from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright


START_URL = "https://diariodarepublica.pt/dr/legislacao-por-tema"
PDF_ENDPOINT_FRAGMENT = "ActionGetVersaoPDF"
DEFAULT_THEMES = ["Civil", "Trabalho"]

# responsavel por transformar o titulo do documento em um slug
def slugify(value: str, max_length: int = 120) -> str:
    value = value.lower()
    value = re.sub(r"[^\w\s.-]", "", value, flags=re.UNICODE)
    value = re.sub(r"\s+", "_", value.strip())
    value = re.sub(r"_+", "_", value)
    return value[:max_length].strip("._") or "documento"

# responsavel por encontrar o pdf no payload
def find_pdf_bytes(payload: Any) -> bytes | None:
    """Search common JSON shapes for a base64-encoded PDF."""
    if isinstance(payload, str):
        candidate = payload.strip()
        if candidate.startswith("data:application/pdf;base64,"):
            candidate = candidate.split(",", 1)[1]

        if candidate.startswith("JVBERi0"):
            try:
                return base64.b64decode(candidate)
            except Exception:
                return None

        return None

    if isinstance(payload, dict):
        for value in payload.values():
            found = find_pdf_bytes(value)
            if found:
                return found

    if isinstance(payload, list):
        for value in payload:
            found = find_pdf_bytes(value)
            if found:
                return found

    return None


def collect_result_links(page: Page) -> list[dict[str, str]]:
    links = page.locator("a").evaluate_all(
        """(elements) => elements.map((a) => ({
            title: (a.innerText || '').trim(),
            url: a.href,
            context: (() => {
                let node = a;
                for (let i = 0; i < 8 && node; i++) {
                    const text = node.innerText || '';
                    # responsavel por encontrar o texto "Em vigor" ou "Revogado"
                    if (text.includes('Em vigor') || text.includes('Revogado')) {
                        return text;
                    }
                    node = node.parentElement;
                }
                return '';
            })()
        }))"""
    )

    results: list[dict[str, str]] = []
    seen: set[str] = set()
    legal_act_pattern = re.compile(
        r"\b(Lei|Decreto-Lei|Decreto Regulamentar|Portaria|Resolução|Despacho)\b",
        re.IGNORECASE,
    )

    for link in links:
        title = " ".join(link["title"].split())
        url = link["url"]
        context = " ".join(link["context"].split())

        if not title or not url.startswith("https://diariodarepublica.pt/dr/"):
            continue
        if "Diário da República" not in title and "Diário do Governo" not in title:
            continue
        if not legal_act_pattern.search(title):
            continue
        if url in seen:
            continue

        legal_status = "unknown"
        if "Em vigor" in context:
            legal_status = "Em vigor"
        elif "Revogado" in context:
            legal_status = "Revogado"

        results.append({"title": title, "url": url, "legal_status": legal_status})
        seen.add(url)

    return results

def collect_all_result_links(page: Page, theme: str, max_pages: int) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    page_number = 1

    while True:
        page_results = collect_result_links(page)
        added = 0

        for result in page_results:
            if result["url"] in seen:
                continue

            results.append(result)
            seen.add(result["url"])
            added += 1

        print(
            f"[{theme}] page {page_number}: found {len(page_results)} result links "
            f"({added} new, {len(results)} total)"
        )

        if max_pages > 0 and page_number >= max_pages:
            break

        next_button = page.get_by_role("button", name=re.compile(r"página seguinte", re.IGNORECASE))
        if next_button.count() == 0 or next_button.first.is_disabled():
            break

        first_result_url = page_results[0]["url"] if page_results else ""

        try:
            next_button.first.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_function(
                """(previousUrl) => {
                    const links = Array.from(document.querySelectorAll('a'));
                    const hasPreviousResult = previousUrl
                        ? links.some((a) => a.href === previousUrl)
                        : false;
                    const hasNewLegalResults = links.some((a) => {
                        const text = (a.innerText || '').trim();
                        const isLegalAct = /\\b(Lei|Decreto-Lei|Decreto Regulamentar|Portaria|Resolução|Despacho)\\b/i
                            .test(text);
                        const hasDiaryReference = text.includes('Diário da República')
                            || text.includes('Diário do Governo');
                        return a.href
                            && a.href.startsWith('https://diariodarepublica.pt/dr/')
                            && isLegalAct
                            && hasDiaryReference
                            && a.href !== previousUrl;
                    });

                    return !hasPreviousResult && hasNewLegalResults;
                }""",
                arg=first_result_url,
                timeout=30_000,
            )
            page.wait_for_timeout(500)
        except PlaywrightTimeoutError:
            break

        page_number += 1

    return results


def save_pdf_response(page: Page, trigger: Locator, output_path: Path) -> bool:
    try:
        with page.expect_response(
            lambda response: PDF_ENDPOINT_FRAGMENT in response.url,
            timeout=30_000,
        ) as response_info:
            trigger.click()

        response = response_info.value
        body = response.body()

        if body.startswith(b"%PDF"):
            output_path.write_bytes(body)
            return True

        try:
            payload = response.json()
        except Exception:
            payload = json.loads(body.decode("utf-8", errors="ignore"))

        pdf_bytes = find_pdf_bytes(payload)
        if pdf_bytes and pdf_bytes.startswith(b"%PDF"):
            output_path.write_bytes(pdf_bytes)
            return True
    except Exception:
        return False

    return False


def download_pdf_from_detail_page(page: Page, output_path: Path) -> bool:
    pdf_link = page.get_by_role("link", name=re.compile(r"PDF", re.IGNORECASE))

    if pdf_link.count() == 0:
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if save_pdf_response(page, pdf_link.first, output_path):
        return True

    date_link = page.get_by_role("link", name=re.compile(r"\d{4}-\d{2}-\d{2}"))
    if date_link.count() > 0 and save_pdf_response(page, date_link.first, output_path):
        return True

    try:
        with page.expect_download(timeout=20_000) as download_info:
            pdf_link.first.click()

        download = download_info.value
        download.save_as(str(output_path))
        return True
    except PlaywrightTimeoutError:
        return False

    return False


def scrape_theme(
    page: Page,
    theme: str,
    limit: int,
    max_pages: int,
    output_dir: Path,
    include_revoked: bool,
) -> list[dict[str, str]]:
    page.goto(START_URL, wait_until="networkidle")
    page.get_by_role("button", name=theme, exact=True).click()
    page.wait_for_load_state("networkidle")
    page.wait_for_function(
        """() => document.body.innerText.includes('resultados')
            || document.body.innerText.includes('resultado')""",
        timeout=20_000,
    )

    results = collect_all_result_links(page, theme, max_pages)
    print(f"[{theme}] found {len(results)} result links across all visited pages")

    rows: list[dict[str, str]] = []
    downloaded_count = 0

    for index, result in enumerate(results, start=1):
        if not include_revoked and result["legal_status"] != "Em vigor":
            rows.append(
                {
                    "theme": theme,
                    "title": result["title"],
                    "legal_status": result["legal_status"],
                    "page_url": result["url"],
                    "pdf_path": "",
                    "status": "skipped_not_in_force",
                }
            )
            print(
                f"[{theme}] {index}/{len(results)} skipped_not_in_force "
                f"({result['legal_status']}): {result['title']}"
            )
            continue

        page.goto(result["url"], wait_until="networkidle")

        theme_dir = output_dir / slugify(theme)
        filename = f"{index:02d}_{slugify(result['title'])}.pdf"
        output_path = theme_dir / filename
        downloaded = download_pdf_from_detail_page(page, output_path)

        rows.append(
            {
                "theme": theme,
                "title": result["title"],
                "legal_status": result["legal_status"],
                "page_url": result["url"],
                "pdf_path": str(output_path) if downloaded else "",
                "status": "downloaded" if downloaded else "no_pdf_found",
            }
        )

        print(f"[{theme}] {index}/{len(results)} {rows[-1]['status']}: {result['title']}")

        if downloaded:
            downloaded_count += 1
            if 0 < limit <= downloaded_count:
                break

    return rows


def write_metadata(rows: list[dict[str, str]], metadata_path: Path) -> None:
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    with metadata_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["theme", "title", "legal_status", "page_url", "pdf_path", "status"],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape Diário da República legislation PDFs by theme using Playwright."
    )
    parser.add_argument(
        "--themes",
        nargs="+",
        default=DEFAULT_THEMES,
        help="Themes to scrape, for example: Civil Trabalho",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of PDFs to download per theme. Use 0 for all matching results.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Maximum number of result pages to visit per theme. Use 0 for all pages.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw_pdfs"),
        help="Folder where PDFs will be saved.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("data/metadata/dr_pdf_downloads.csv"),
        help="CSV file where scrape metadata will be saved.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser without showing the UI.",
    )
    parser.add_argument(
        "--include-revoked",
        action="store_true",
        help="Also download documents marked as revoked. By default only 'Em vigor' documents are downloaded.",
    )
    args = parser.parse_args()

    all_rows: list[dict[str, str]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=args.headless)
        page = browser.new_page(accept_downloads=True)

        for theme in args.themes:
            all_rows.extend(
                scrape_theme(
                    page,
                    theme,
                    args.limit,
                    args.max_pages,
                    args.output_dir,
                    include_revoked=args.include_revoked,
                )
            )

        browser.close()

    write_metadata(all_rows, args.metadata)
    print(f"\nMetadata saved to {args.metadata}")


if __name__ == "__main__":
    main()
