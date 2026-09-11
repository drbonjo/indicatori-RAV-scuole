from playwright.sync_api import sync_playwright


SCHOOL_CODE = "APPSZ65005"

START_URL = (
    "https://snv.pubblica.istruzione.it/"
    "SistemaNazionaleValutazione/"
    "scuolaInChiaro.do"
    f"?dispatch=indicatori&scuolainserita={SCHOOL_CODE}"
)


def main():

    p = sync_playwright().start()

    browser = p.chromium.launch(
        headless=False
    )

    context = browser.new_context()
    page = context.new_page()

    discovered_urls = set()

    def register_request(request):

        if "/loadDsc/" in request.url:

            if request.url not in discovered_urls:

                discovered_urls.add(request.url)

                print()
                print("LOAD DSC:")
                print(request.url)

    page.on("request", register_request)

    print("Apro la pagina...")

    page.goto(
        START_URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(1500)

    # =========================================================
    # 1. APRI SOLO LE MACROSEZIONI
    # =========================================================

    sliders = page.locator(
        '[onclick*="apriSlider"]'
    )

    print()
    print(
        "Macro-slider trovati:",
        sliders.count()
    )

    for i in range(sliders.count()):

        el = sliders.nth(i)

        try:

            onclick = el.get_attribute(
                "onclick"
            )

            print()
            print(
                "APRO:",
                onclick
            )

            el.click(
                force=True,
                timeout=2000
            )

            page.wait_for_timeout(500)

        except Exception as exc:

            print(
                "ERRORE:",
                type(exc).__name__,
                exc
            )

    # =========================================================
    # 2. ORA CENSISCI TUTTI GLI ONCLICK PRESENTI
    # =========================================================

    print()
    print("=" * 80)
    print("ONCLICK PRESENTI DOPO APERTURA")
    print("=" * 80)

    elements = page.locator("[onclick]")

    found = set()

    for i in range(elements.count()):

        try:

            el = elements.nth(i)

            onclick = el.get_attribute(
                "onclick"
            )

            if not onclick:
                continue

            if onclick in found:
                continue

            found.add(onclick)

            print()
            print(onclick)

        except Exception:
            pass

    print()
    print("=" * 80)
    print(
        "ONCLICK DISTINTI:",
        len(found)
    )
    print("=" * 80)

    print()
    print(
        "Browser lasciato aperto."
    )
    print(
        "Premi INVIO per terminare."
    )

    input()

    browser.close()
    p.stop()


main()