import asyncio
import requests
import os
from playwright.async_api import async_playwright

DISCORD_URL = "https://discord.com/channels/@me"
BACKEND_TOKEN_POST_URL = os.getenv("SERVER_URL", "http://localhost:8000/token")
PROFILE_DIR = "./discord_profile"

async def extract_token():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']  # For GitHub Actions
        )
        
        page = await browser.new_page()
        print("🔁 Opening Discord...")
        
        try:
            await page.goto(DISCORD_URL, timeout=60000)
            
            # Wait for Discord to load - look for a Discord-specific element
            print("⏳ Waiting for Discord to load...")
            await page.wait_for_selector('[data-list-id="guildsnav"]', timeout=30000)
            
            # Give it a bit more time to fully initialize
            await page.wait_for_timeout(3000)
            
            # Extract token using multiple methods
            token = None
            
            # Method 1: Direct localStorage access
            try:
                token = await page.evaluate("""
                    () => {
                        try {
                            return localStorage.getItem('token');
                        } catch (e) {
                            return null;
                        }
                    }
                """)
            except Exception as e:
                print(f"⚠️ Method 1 failed: {e}")
            
            # Method 2: Check webpackChunkdiscord_app for token
            if not token:
                try:
                    token = await page.evaluate("""
                        () => {
                            try {
                                const token = window.webpackChunkdiscord_app.push([
                                    [Math.random()], 
                                    {}, 
                                    req => {
                                        for (const m of Object.keys(req.c)
                                            .map(x => req.c[x].exports)
                                            .filter(x => x)) {
                                            if (m.default && m.default.getToken !== undefined) {
                                                return m.default.getToken()
                                            }
                                            if (m.getToken !== undefined) {
                                                return m.getToken()
                                            }
                                        }
                                    }
                                ]);
                                return token;
                            } catch (e) {
                                return null;
                            }
                        }
                    """)
                except Exception as e:
                    print(f"⚠️ Method 2 failed: {e}")
            
            # Method 3: Fallback - try to find token in any available storage
            if not token:
                try:
                    token = await page.evaluate("""
                        () => {
                            try {
                                // Check if localStorage is available
                                if (typeof localStorage !== 'undefined') {
                                    return localStorage.getItem('token');
                                }
                                return null;
                            } catch (e) {
                                return null;
                            }
                        }
                    """)
                except Exception as e:
                    print(f"⚠️ Method 3 failed: {e}")
            
            await browser.close()
            
            if token:
                return token.strip('"')
            else:
                print("❌ Could not extract token from any method")
                return None
                
        except Exception as e:
            print(f"❌ Error during token extraction: {e}")
            await browser.close()
            return None

def send_token_to_backend(token):
    print("📤 Sending token to backend...")
    try:
        res = requests.post(BACKEND_TOKEN_POST_URL, json={"token": token}, timeout=10)
        print("✅ Status:", res.status_code, res.text)
        return res.status_code == 200
    except Exception as e:
        print(f"❌ Failed to send token: {e}")
        return False

if __name__ == "__main__":
    token = asyncio.run(extract_token())
    if token:
        print("✅ Token extracted:", token[:20] + "..." if len(token) > 20 else token)
        success = send_token_to_backend(token)
        if success:
            print("✅ Token successfully sent to backend!")
        else:
            print("❌ Failed to send token to backend.")
    else:
        print("❌ Failed to extract token.")
