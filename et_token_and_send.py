# get_token_and_send.py

import asyncio
import requests
from playwright.async_api import async_playwright

DISCORD_URL = "https://discord.com/channels/@me"
BACKEND_TOKEN_POST_URL = "http://127.0.0.1:8000/"  # Change this to Render or localhost
PROFILE_DIR = "./discord_profile"  # must be zipped & uploaded in repo

async def extract_token():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=True,
        )
        page = await browser.new_page()
        print("🔁 Opening Discord...")
        await page.goto(DISCORD_URL, timeout=60000)

        # Wait for page to load and extract token
        token = await page.evaluate("() => localStorage.getItem('token')")
        await browser.close()
        return token.strip('"')

def send_token_to_backend(token):
    print("📤 Sending token to backend...")
    res = requests.post(BACKEND_TOKEN_POST_URL, json={"token": token})
    print("✅ Status:", res.status_code, res.text)

if __name__ == "__main__":
    token = asyncio.run(extract_token())
    if token:
        print("✅ Token extracted:", token[:10], "...")
        send_token_to_backend(token)
    else:
        print("❌ Failed to extract token.")
