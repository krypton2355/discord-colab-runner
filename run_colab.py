import asyncio
from playwright.async_api import async_playwright

COLAB_URL = "https://colab.research.google.com/github/krypton2355/discord-colab-runner/blob/main/DiscoToken.ipynb"

async def main():
    print("🟢 Launching browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()

        print("🌐 Opening Colab notebook...")
        await page.goto(COLAB_URL, timeout=90000)
        await page.wait_for_timeout(8000)

        print("▶️ Step 1: Pressing Ctrl+F9 (Run all)")
        await page.keyboard.press('Control+F9')
        await page.wait_for_timeout(3000)

        print("🔁 Step 2: Tabbing to 'Run anyway'")
        await page.keyboard.press('Tab')
        await page.keyboard.press('Tab')
        await page.keyboard.press('Tab')
        await page.wait_for_timeout(1000)

        print("⏎ Step 3: Pressing Enter to confirm")
        await page.keyboard.press('Enter')

        print("⏳ Waiting 2 mins for execution to finish...")
        await page.wait_for_timeout(120000)

        await browser.close()
        print("✅ Notebook execution complete.")

asyncio.run(main())
