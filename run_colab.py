import asyncio
from playwright.async_api import async_playwright

# Replace this with your actual Colab notebook URL
COLAB_URL = "https://colab.research.google.com/github/krypton2355/discord-colab-runner/blob/main/DiscoToken.ipynb"

async def main():
    print("🟢 Launching browser...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()

        print("🌐 Opening Colab...")
        await page.goto(COLAB_URL, timeout=60000)

        # Wait for the 'Run all' button
        print("🔍 Waiting for 'Run all' button...")
        await page.wait_for_selector('text="Run all"', timeout=60000)
        await page.click('text="Run all"')
        print("▶️ Running notebook...")

        # Wait for some time to let the notebook execute
        await page.wait_for_timeout(120000)  # wait 2 minutes

        await browser.close()
        print("✅ Finished.")

asyncio.run(main())
