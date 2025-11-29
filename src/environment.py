"""Playwright-based web environment for agent interaction"""

import re
from typing import List, Optional, Dict, Any
from playwright.sync_api import sync_playwright, Page, Browser, Playwright
from src.models import Action, PageState, InteractiveElement


class ElementNotFoundError(Exception):
    """Raised when an element cannot be found"""
    pass


class PageTimeoutError(Exception):
    """Raised when a page operation times out"""
    pass


class WebEnvironment:
    """Playwright-based web environment for agent interaction"""
    
    INTERACTIVE_ROLES = {
        "button", "textbox", "checkbox", "radio",
        "combobox", "link", "menuitem", "option",
        "searchbox", "slider", "spinbutton", "switch", "tab"
    }
    
    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = 5000,
        action_delay_ms: int = 300
    ):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.action_delay_ms = action_delay_ms
        
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    def start(self):
        """Initialize browser"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        self.page.set_default_timeout(self.timeout_ms)
    
    def stop(self):
        """Cleanup browser resources"""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def reset(self, url: str) -> PageState:
        """Navigate to URL and return initial state"""
        try:
            self.page.goto(url, wait_until="networkidle")
            self.page.wait_for_timeout(500)  # Extra settle time
            return self.get_state()
        except Exception as e:
            raise PageTimeoutError(f"Failed to load {url}: {e}")
    
    def step(self, action: Action) -> PageState:
        """Execute an action and return new state"""
        
        # Resolve element to selector
        try:
            selector = self._resolve_selector(action.element)
        except ElementNotFoundError:
            raise
        
        # Execute action
        try:
            if action.action == "click":
                self.page.click(selector)
            
            elif action.action == "type":
                self.page.fill(selector, action.value)
            
            elif action.action == "clear":
                self.page.fill(selector, "")
            
            elif action.action == "select":
                self.page.select_option(selector, action.value)
            
            elif action.action == "scroll":
                delta = 300 if action.value == "down" else -300
                self.page.mouse.wheel(0, delta)
            
            else:
                raise ValueError(f"Unknown action type: {action.action}")
            
            # Wait for page to settle
            self.page.wait_for_timeout(self.action_delay_ms)
            
            return self.get_state()
            
        except Exception as e:
            if "timeout" in str(e).lower():
                raise PageTimeoutError(f"Action timed out: {action}")
            raise
    
    def get_state(self) -> PageState:
        """Extract current page state"""
        
        # Get accessibility tree
        tree = self.page.accessibility.snapshot()
        interactive_elements = self._extract_interactive(tree) if tree else []
        
        # Get visible text
        try:
            visible_text = self.page.inner_text("body")
        except:
            visible_text = ""
        
        # Get errors
        errors = self._extract_errors()
        
        return PageState(
            url=self.page.url,
            title=self.page.title(),
            interactive_elements=interactive_elements,
            visible_text=visible_text,
            errors=errors
        )
    
    def _resolve_selector(self, element_name: str) -> str:
        """Convert element name to Playwright selector"""
        
        # Clean up element name - LLM might include role prefix or state suffix
        # e.g., "[checkbox] Email Notifications checked=true" -> "Email Notifications"
        clean_name = element_name
        
        # Remove role prefix like "[checkbox] " or "[button] "
        clean_name = re.sub(r'^\[[\w]+\]\s*', '', clean_name)
        
        # Remove state suffixes like " checked=true", " value="..."", " disabled"
        clean_name = re.sub(r'\s+(checked|disabled|value)=\S*', '', clean_name)
        clean_name = re.sub(r'\s+value="[^"]*"', '', clean_name)
        clean_name = clean_name.strip()
        
        # Try both original and cleaned names
        names_to_try = [clean_name]
        if clean_name != element_name:
            names_to_try.append(element_name)
        
        for name in names_to_try:
            strategies = [
                f"[aria-label='{name}']",
                f"button:has-text('{name}')",
                f"a:has-text('{name}')",
                f"input[placeholder='{name}']",
                f"label:has-text('{name}') >> input",
                f"label:has-text('{name}') >> select",
                f"label:has-text('{name}') >> textarea",
                f"label:has-text('{name}') >> .. >> input[type='checkbox']",
                f"text='{name}'",
            ]
            
            for selector in strategies:
                try:
                    locator = self.page.locator(selector)
                    if locator.count() > 0:
                        return selector
                except:
                    continue
        
        raise ElementNotFoundError(f"Could not find element: {element_name}")
    
    def _extract_interactive(
        self,
        node: Dict[str, Any],
        results: Optional[List[InteractiveElement]] = None
    ) -> List[InteractiveElement]:
        """Recursively extract interactive elements from accessibility tree"""
        
        if results is None:
            results = []
        
        if node is None:
            return results
        
        role = node.get("role", "")
        
        if role in self.INTERACTIVE_ROLES:
            results.append(InteractiveElement(
                role=role,
                name=node.get("name", ""),
                value=node.get("value", ""),
                checked=node.get("checked"),
                disabled=node.get("disabled", False)
            ))
        
        for child in node.get("children", []):
            self._extract_interactive(child, results)
        
        return results
    
    def _extract_errors(self) -> List[str]:
        """Extract error messages from page"""
        
        error_selectors = [
            ".error",
            ".error-message",
            "[role='alert']",
            ".invalid-feedback",
            ".form-error",
            ".validation-error"
        ]
        
        errors = []
        
        for selector in error_selectors:
            try:
                elements = self.page.locator(selector).all()
                for el in elements:
                    text = el.inner_text().strip()
                    if text and text not in errors:
                        errors.append(text)
            except:
                continue
        
        return errors
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

