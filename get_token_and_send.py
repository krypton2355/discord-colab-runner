import asyncio
import requests
import os
import json
import time
from playwright.async_api import async_playwright

DISCORD_URL = "https://discord.com/login"
DISCORD_APP_URL = "https://discord.com/channels/@me"
BACKEND_TOKEN_POST_URL = os.getenv("SERVER_URL", "http://localhost:8000/token")

# Store credentials securely - use environment variables
DISCORD_EMAIL = os.getenv("DISCORD_EMAIL")
DISCORD_PASSWORD = os.getenv("DISCORD_PASSWORD")
CAPTCHA_SOLVER_KEY = os.getenv("CAPTCHA_SOLVER_KEY")  # Optional: 2captcha or similar service

async def solve_hcaptcha(page, site_key):
    """Attempt to solve hCAPTCHA using various methods"""
    
    print("🤖 hCAPTCHA detected...")
    
    # Method 1: Try to solve with 2captcha service (if API key provided)
    if CAPTCHA_SOLVER_KEY:
        try:
            print("🔧 Attempting to solve captcha with 2captcha service...")
            
            # Submit captcha to 2captcha
            submit_url = "http://2captcha.com/in.php"
            submit_data = {
                'key': CAPTCHA_SOLVER_KEY,
                'method': 'hcaptcha',
                'sitekey': site_key,
                'pageurl': page.url
            }
            
            submit_response = requests.post(submit_url, data=submit_data, timeout=30)
            if submit_response.text.startswith('OK|'):
                captcha_id = submit_response.text.split('|')[1]
                print(f"✅ Captcha submitted, ID: {captcha_id}")
                
                # Poll for solution
                result_url = "http://2captcha.com/res.php"
                for attempt in range(30):  # Wait up to 5 minutes
                    await asyncio.sleep(10)
                    result_response = requests.get(f"{result_url}?key={CAPTCHA_SOLVER_KEY}&action=get&id={captcha_id}", timeout=10)
                    
                    if result_response.text.startswith('OK|'):
                        solution = result_response.text.split('|')[1]
                        print("✅ Captcha solved!")
                        
                        # Submit solution
                        await page.evaluate(f"""
                            () => {{
                                const textarea = document.querySelector('[name="h-captcha-response"]');
                                if (textarea) {{
                                    textarea.value = '{solution}';
                                    textarea.dispatchEvent(new Event('input'));
                                }}
                                
                                const callback = window.hcaptchaCallback;
                                if (callback) callback('{solution}');
                            }}
                        """)
                        
                        return True
                    elif result_response.text == 'CAPCHA_NOT_READY':
                        print(f"⏳ Captcha solving in progress... (attempt {attempt + 1}/30)")
                        continue
                    else:
                        print(f"❌ Captcha solving failed: {result_response.text}")
                        break
                        
            else:
                print(f"❌ Failed to submit captcha: {submit_response.text}")
                
        except Exception as e:
            print(f"❌ Captcha solver error: {e}")
    
    # Method 2: Try simple click method (sometimes works)
    try:
        print("🖱️ Attempting simple captcha click...")
        
        # Wait for captcha iframe
        captcha_frame = await page.wait_for_selector('iframe[src*="hcaptcha.com"]', timeout=10000)
        if captcha_frame:
            frame = await captcha_frame.content_frame()
            if frame:
                # Try to click the checkbox
                checkbox = await frame.wait_for_selector('.check', timeout=5000)
                if checkbox:
                    await checkbox.click()
                    print("✅ Captcha checkbox clicked")
                    await asyncio.sleep(3)
                    return True
                    
    except Exception as e:
        print(f"⚠️ Simple click method failed: {e}")
    
    return False

async def handle_cloudflare_challenge(page):
    """Handle Cloudflare challenge if present"""
    try:
        # Check for Cloudflare challenge
        cf_challenge = await page.wait_for_selector('#cf-challenge-running', timeout=5000)
        if cf_challenge:
            print("☁️ Cloudflare challenge detected, waiting...")
            
            # Wait for challenge to complete (up to 30 seconds)
            for i in range(30):
                try:
                    # Check if challenge is complete
                    await page.wait_for_selector('#cf-challenge-running', timeout=1000, state='detached')
                    print("✅ Cloudflare challenge completed")
                    return True
                except:
                    print(f"⏳ Waiting for Cloudflare... ({i+1}/30)")
                    await asyncio.sleep(1)
            
            print("❌ Cloudflare challenge timeout")
            return False
            
    except:
        # No Cloudflare challenge
        return True
    
    return True

async def smart_login_with_captcha_handling():
    """Enhanced login with comprehensive captcha and challenge handling"""
    
    if not DISCORD_EMAIL or not DISCORD_PASSWORD:
        print("❌ Missing DISCORD_EMAIL or DISCORD_PASSWORD environment variables")
        return None
    
    async with async_playwright() as p:
        # Use realistic browser settings to avoid detection
        browser = await p.chromium.launch(
            headless=os.getenv("HEADLESS", "true").lower() == "true",  # Can override with env var
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=VizDisplayCompositor',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        )
        
        try:
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = await context.new_page()
            
            # Add realistic headers
            await page.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none'
            })
            
            print("🔗 Navigating to Discord login...")
            await page.goto(DISCORD_URL, timeout=30000)
            
            # Handle Cloudflare if present
            await handle_cloudflare_challenge(page)
            
            # Wait for login form
            print("⏳ Waiting for login form...")
            await page.wait_for_selector('input[name="email"]', timeout=20000)
            
            # Human-like typing delays
            print("📝 Entering credentials with human-like timing...")
            await page.type('input[name="email"]', DISCORD_EMAIL, delay=50)
            await asyncio.sleep(1)
            await page.type('input[name="password"]', DISCORD_PASSWORD, delay=50)
            await asyncio.sleep(1)
            
            # Click login button
            print("🔐 Clicking login...")
            login_button = await page.wait_for_selector('button[type="submit"]', timeout=10000)
            await login_button.click()
            
            # Wait a bit for response
            await asyncio.sleep(3)
            
            # Check for various challenges/responses
            max_attempts = 3
            for attempt in range(max_attempts):
                print(f"🔍 Checking login status (attempt {attempt + 1}/{max_attempts})...")
                
                current_url = page.url
                print(f"📍 Current URL: {current_url}")
                
                # Success - redirected to main app
                if "/channels/@me" in current_url:
                    print("✅ Login successful!")
                    break
                
                # Check for hCAPTCHA
                try:
                    captcha_frame = await page.wait_for_selector('iframe[src*="hcaptcha.com"]', timeout=5000)
                    if captcha_frame:
                        print("🤖 hCAPTCHA detected!")
                        
                        # Get site key for captcha solving
                        site_key = await page.evaluate("""
                            () => {
                                const iframe = document.querySelector('iframe[src*="hcaptcha.com"]');
                                if (iframe) {
                                    const src = iframe.src;
                                    const match = src.match(/sitekey=([^&]+)/);
                                    return match ? match[1] : null;
                                }
                                return null;
                            }
                        """)
                        
                        print(f"🔑 Site key: {site_key}")
                        
                        # Attempt to solve captcha
                        if await solve_hcaptcha(page, site_key):
                            print("✅ Captcha solved, retrying login...")
                            
                            # Click login again after captcha
                            try:
                                login_btn = await page.wait_for_selector('button[type="submit"]', timeout=5000)
                                await login_btn.click()
                                await asyncio.sleep(5)
                            except:
                                pass
                        else:
                            print("❌ Failed to solve captcha")
                            if attempt == max_attempts - 1:
                                await browser.close()
                                return None
                            
                        continue
                        
                except:
                    pass
                
                # Check for 2FA
                try:
                    totp_input = await page.wait_for_selector('input[placeholder*="6-digit"]', timeout=5000)
                    if totp_input:
                        totp_secret = os.getenv("DISCORD_2FA_SECRET")
                        if totp_secret:
                            print("🔒 2FA required, generating code...")
                            try:
                                import pyotp
                                totp = pyotp.TOTP(totp_secret)
                                code = totp.now()
                                
                                await page.fill('input[placeholder*="6-digit"]', code)
                                submit_btn = await page.wait_for_selector('button[type="submit"]', timeout=5000)
                                await submit_btn.click()
                                await asyncio.sleep(5)
                                continue
                                
                            except ImportError:
                                print("❌ pyotp not installed for 2FA support")
                                await browser.close()
                                return None
                        else:
                            print("🔒 2FA required but no secret provided")
                            await browser.close()
                            return None
                            
                except:
                    pass
                
                # Check for login errors
                try:
                    error_elem = await page.wait_for_selector('.error-message, [class*="error"], [class*="notice"]', timeout=5000)
                    if error_elem:
                        error_text = await error_elem.text_content()
                        print(f"❌ Login error: {error_text}")
                        
                        if "captcha" in error_text.lower():
                            print("🤖 Captcha error detected, retrying...")
                            continue
                        else:
                            await browser.close()
                            return None
                except:
                    pass
                
                # If we're still on login page after delay, something's wrong
                if "/login" in current_url:
                    print("⚠️ Still on login page, waiting longer...")
                    await asyncio.sleep(10)
                    continue
                else:
                    # Try to navigate to main app
                    print("🔄 Attempting to navigate to Discord app...")
                    await page.goto(DISCORD_APP_URL, timeout=30000)
                    break
            
            # Final check - make sure we're logged in
            try:
                await page.wait_for_url("**/channels/@me", timeout=15000)
                print("✅ Successfully accessed Discord app!")
            except:
                print("❌ Failed to access Discord app")
                await browser.close()
                return None
            
            # Wait for Discord to fully load
            print("⏳ Waiting for Discord interface to load...")
            selectors_to_try = [
                '[class*="sidebar"]',
                '[data-list-id="guildsnav"]', 
                '[class*="guilds"]',
                '[class*="app"]'
            ]
            
            loaded = False
            for selector in selectors_to_try:
                try:
                    await page.wait_for_selector(selector, timeout=10000)
                    print(f"✅ Discord loaded (found: {selector})")
                    loaded = True
                    break
                except:
                    continue
            
            if not loaded:
                print("⚠️ Discord interface not fully loaded, but continuing...")
            
            # Give Discord time to initialize
            await asyncio.sleep(5)
            
            # Extract token using multiple methods
            token = None
            
            # Method 1: localStorage
            print("🔍 Extracting token from localStorage...")
            try:
                token = await page.evaluate("""
                    () => {
                        try {
                            const token = localStorage.getItem('token');
                            return token ? token.replace(/['"]/g, '') : null;
                        } catch (e) {
                            return null;
                        }
                    }
                """)
                if token and len(token) > 20:
                    print("✅ Token found in localStorage")
                else:
                    token = None
            except Exception as e:
                print(f"⚠️ localStorage method failed: {e}")
            
            # Method 2: Webpack injection
            if not token:
                print("🔍 Trying webpack method...")
                try:
                    token = await page.evaluate("""
                        () => {
                            try {
                                let foundToken = null;
                                if (window.webpackChunkdiscord_app) {
                                    window.webpackChunkdiscord_app.push([
                                        [Math.random()], 
                                        {}, 
                                        (req) => {
                                            for (const moduleId of Object.keys(req.c)) {
                                                const module = req.c[moduleId].exports;
                                                if (module && module.default && module.default.getToken) {
                                                    foundToken = module.default.getToken();
                                                    return;
                                                }
                                                if (module && module.getToken) {
                                                    foundToken = module.getToken();
                                                    return;
                                                }
                                            }
                                        }
                                    ]);
                                }
                                return foundToken;
                            } catch (e) {
                                return null;
                            }
                        }
                    """)
                    if token and len(token) > 20:
                        print("✅ Token found via webpack")
                    else:
                        token = None
                except Exception as e:
                    print(f"⚠️ Webpack method failed: {e}")
            
            # Method 3: Network request monitoring
            if not token:
                print("🔍 Monitoring network requests...")
                try:
                    captured_token = None
                    
                    def handle_request(request):
                        nonlocal captured_token
                        auth_header = request.headers.get('authorization')
                        if auth_header and len(auth_header) > 50:
                            captured_token = auth_header
                    
                    page.on('request', handle_request)
                    
                    # Trigger some network activity
                    await page.reload()
                    await asyncio.sleep(5)
                    
                    if captured_token:
                        token = captured_token
                        print("✅ Token captured from network requests")
                        
                except Exception as e:
                    print(f"⚠️ Network monitoring failed: {e}")
            
            await browser.close()
            
            if token and len(token) > 20:
                return token
            else:
                print("❌ No valid token extracted")
                return None
                
        except Exception as e:
            print(f"❌ Error during login process: {e}")
            await browser.close()
            return None

def send_token_to_backend(token):
    """Send token to backend"""
    print("📤 Sending token to backend...")
    try:
        res = requests.post(BACKEND_TOKEN_POST_URL, json={"token": token}, timeout=10)
        print("✅ Status:", res.status_code, res.text)
        return res.status_code == 200
    except Exception as e:
        print(f"❌ Failed to send token: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Discord login with captcha handling...")
    
    token = asyncio.run(smart_login_with_captcha_handling())
    
    if token:
        print("✅ Token extracted:", token[:20] + "..." if len(token) > 20 else token)
        
        # Send to backend
        success = send_token_to_backend(token)
        if success:
            print("✅ Token successfully sent to backend!")
        else:
            print("❌ Failed to send token to backend.")
    else:
        print("❌ Failed to extract token. This might be due to:")
        print("   • Captcha that couldn't be solved automatically")
        print("   • Rate limiting from Discord")
        print("   • Invalid credentials")
        print("   • 2FA required but not configured")
        print("   • Account locked or suspicious activity detected")
