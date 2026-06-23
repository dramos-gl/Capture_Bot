"""Browser factory for Playwright setups."""

from typing import Dict, Any
from playwright.async_api import Playwright, Browser, BrowserContext

class BrowserFactory:
    """Factory to create and configure Playwright browser instances and contexts."""

    @staticmethod
    async def launch_browser(playwright: Playwright, headless: bool = True, browser_type: str = "chromium") -> Browser:
        """Launches a browser instance with stealth arguments."""
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-position=0,0",
            "--ignore-certificate-errors",
        ]
        
        options: Dict[str, Any] = {
            "headless": headless,
            "args": launch_args,
        }
        
        if browser_type == "firefox":
            return await playwright.firefox.launch(**options)
        elif browser_type == "webkit":
            return await playwright.webkit.launch(**options)
        else:
            return await playwright.chromium.launch(**options)

    @staticmethod
    async def create_context(
        browser: Browser,
        viewport_width: int = 1280,
        viewport_height: int = 800,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ) -> BrowserContext:
        """Creates a browser context with custom viewport, user agent, and downloads accepted."""
        context = await browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            user_agent=user_agent,
            accept_downloads=True,
            ignore_https_errors=True
        )
        # Avoid webdriver detection
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return context
