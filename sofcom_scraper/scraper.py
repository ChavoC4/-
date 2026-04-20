from __future__ import annotations

import hashlib
from typing import Iterable

from playwright.sync_api import Page, TimeoutError, sync_playwright

from .captcha import CaptchaSolver
from .config import AppConfig
from .models import ScrapedAction
from .normalize import normalize_spaces
from .parser import parse_actions_from_records

_ACTION_TOKENS = ("продаж", "презалаган", "прекрат", "нов договор")
_MATERIAL_TOKENS = ("жълт метал", "злато", "сребро", "техника")
_NEXT_PAGE_SELECTORS = (
    "a.rgPageNext",
    "button.rgPageNext",
    "a[title='Next Page']",
    "a[title='Следваща страница']",
)


class SofcomScraper:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._captcha_solver = CaptchaSolver()

    def scrape_tracking_actions(self) -> list[ScrapedAction]:
        if not self.config.username or not self.config.password:
            raise RuntimeError(
                "Missing credentials. Set SOFCOM_USERNAME and SOFCOM_PASSWORD in your .env file."
            )

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.config.headless)
            context = browser.new_context(locale="bg-BG", timezone_id=self.config.timezone)
            page = context.new_page()
            try:
                self._login(page)
                page.goto(self.config.tracking_url, wait_until="networkidle")
                if "SessionOutForm" in page.url:
                    raise RuntimeError("Login succeeded but tracking page requires an active session.")
                records = self._collect_all_action_rows(page)
            finally:
                context.close()
                browser.close()

        return parse_actions_from_records(records, source=self.config.tracking_url)

    def _collect_all_action_rows(self, page: Page) -> list[dict[str, str]]:
        action_options = self._discover_action_options(page)
        if not action_options:
            return self._collect_rows(page)

        all_rows: list[dict[str, str]] = []
        seen: set[str] = set()
        for option in action_options:
            self._apply_action_filter(page, option)
            filtered_rows = self._collect_rows(page)
            for row in filtered_rows:
                row["selected_action_filter"] = option
                row_hash = hashlib.sha1(repr(sorted(row.items())).encode("utf-8")).hexdigest()
                if row_hash in seen:
                    continue
                seen.add(row_hash)
                all_rows.append(row)
        return all_rows

    def _login(self, page: Page) -> None:
        for attempt in range(1, self.config.max_login_attempts + 1):
            page.goto(self.config.login_url, wait_until="networkidle")
            page.fill(self.config.username_selector, self.config.username)
            page.fill(self.config.password_selector, self.config.password)

            captcha_image = page.locator(self.config.captcha_image_selector).first
            captcha_input = page.locator(self.config.captcha_input_selector).first
            if captcha_image.count() == 0 or captcha_input.count() == 0:
                raise RuntimeError("Could not locate captcha controls on the login form.")

            captcha_png = captcha_image.screenshot()
            captcha_code = self._captcha_solver.solve(captcha_png)
            captcha_input.fill(captcha_code)
            page.click(self.config.login_button_selector)

            try:
                page.wait_for_load_state("networkidle", timeout=10_000)
            except TimeoutError:
                page.wait_for_timeout(1000)

            if not self._is_login_page(page):
                return

            error_text = normalize_spaces(page.inner_text("body"))
            if "грешен код" in error_text.lower():
                continue
            if attempt == self.config.max_login_attempts:
                break

        raise RuntimeError(
            f"Unable to log in after {self.config.max_login_attempts} attempts. "
            "Check credentials and captcha selector settings."
        )

    def _is_login_page(self, page: Page) -> bool:
        return bool(page.locator(self.config.username_selector).count()) and bool(
            page.locator(self.config.password_selector).count()
        )

    def _collect_rows(self, page: Page) -> list[dict[str, str]]:
        page.wait_for_selector("body", timeout=15_000)
        all_rows: list[dict[str, str]] = []
        seen_pages: set[str] = set()
        seen_rows: set[str] = set()

        for _ in range(self.config.max_pages):
            page.wait_for_timeout(400)
            current_rows = self._extract_current_page_rows(page)
            signature = self._page_signature(current_rows)
            if signature in seen_pages:
                break
            seen_pages.add(signature)

            for row in current_rows:
                row_hash = hashlib.sha1(repr(sorted(row.items())).encode("utf-8")).hexdigest()
                if row_hash in seen_rows:
                    continue
                seen_rows.add(row_hash)
                all_rows.append(row)

            if not self._go_next_page(page):
                break

        return all_rows

    def _discover_action_options(self, page: Page) -> list[str]:
        selector = self.config.action_select_selector.strip()
        if not selector:
            return []
        dropdown = page.locator(selector).first
        if dropdown.count() == 0:
            return []
        options = dropdown.locator("option")
        discovered: list[str] = []
        for idx in range(options.count()):
            value = normalize_spaces(options.nth(idx).get_attribute("value") or "")
            label = normalize_spaces(options.nth(idx).inner_text())
            token = value or label
            lowered = token.lower()
            if not token or lowered in {"", "0", "all", "всички"}:
                continue
            discovered.append(token)
        return discovered

    def _apply_action_filter(self, page: Page, option: str) -> None:
        selector = self.config.action_select_selector.strip()
        if not selector:
            return
        dropdown = page.locator(selector).first
        if dropdown.count() == 0:
            return

        option_values = dropdown.locator("option").evaluate_all(
            "options => options.map(o => ({ value: o.value, label: o.textContent }))"
        )
        chosen_value = ""
        for entry in option_values:
            value = normalize_spaces(str(entry.get("value", "")))
            label = normalize_spaces(str(entry.get("label", "")))
            if option == value or option == label:
                chosen_value = value or label
                break
        if not chosen_value:
            chosen_value = option

        if dropdown.evaluate("el => el.tagName").lower() == "select":
            dropdown.select_option(value=chosen_value)
        else:
            dropdown.click()
            page.keyboard.type(option)
            page.keyboard.press("Enter")

        if self.config.action_search_button_selector.strip():
            button = page.locator(self.config.action_search_button_selector).first
            if button.count():
                button.click()

        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except TimeoutError:
            page.wait_for_timeout(700)

    def _extract_current_page_rows(self, page: Page) -> list[dict[str, str]]:
        telerik_records = self._extract_telerik_grid_records(page)
        if telerik_records:
            return telerik_records
        return self._extract_generic_table_records(page)

    def _extract_telerik_grid_records(self, page: Page) -> list[dict[str, str]]:
        headers = [
            normalize_spaces(text)
            for text in page.locator(".rgMasterTable thead tr th").all_inner_texts()
            if normalize_spaces(text)
        ]
        row_locator = page.locator(".rgMasterTable tbody tr.rgRow, .rgMasterTable tbody tr.rgAltRow")
        records: list[dict[str, str]] = []
        for idx in range(row_locator.count()):
            cells = [
                normalize_spaces(text)
                for text in row_locator.nth(idx).locator("td").all_inner_texts()
                if normalize_spaces(text)
            ]
            if not self._looks_like_action_row(cells):
                continue
            records.append(self._cells_to_record(cells, headers))
        return records

    def _extract_generic_table_records(self, page: Page) -> list[dict[str, str]]:
        records: list[dict[str, str]] = []
        table_locator = page.locator("table")
        for table_idx in range(table_locator.count()):
            table = table_locator.nth(table_idx)
            headers = [
                normalize_spaces(text)
                for text in table.locator("thead tr th").all_inner_texts()
                if normalize_spaces(text)
            ]
            rows = table.locator("tbody tr")
            if rows.count() == 0:
                rows = table.locator("tr")
            for row_idx in range(rows.count()):
                row = rows.nth(row_idx)
                cells = [
                    normalize_spaces(text)
                    for text in row.locator("th, td").all_inner_texts()
                    if normalize_spaces(text)
                ]
                if not self._looks_like_action_row(cells):
                    continue
                records.append(self._cells_to_record(cells, headers))
        return records

    def _cells_to_record(self, cells: Iterable[str], headers: list[str]) -> dict[str, str]:
        values = list(cells)
        record: dict[str, str] = {"row_text": " | ".join(values)}
        if headers and len(headers) >= len(values):
            for idx, value in enumerate(values):
                record[headers[idx]] = value
            return record
        for idx, value in enumerate(values, start=1):
            record[f"col_{idx}"] = value
        return record

    def _looks_like_action_row(self, cells: list[str]) -> bool:
        if len(cells) < 2:
            return False
        full = normalize_spaces(" ".join(cells)).lower()
        if any(token in full for token in _ACTION_TOKENS):
            return True
        if any(token in full for token in _MATERIAL_TOKENS):
            return True
        numeric_count = sum(1 for cell in cells if any(ch.isdigit() for ch in cell))
        return numeric_count >= 3 and ("брой" in full or "сума" in full or "тегло" in full)

    def _go_next_page(self, page: Page) -> bool:
        for selector in _NEXT_PAGE_SELECTORS:
            control = page.locator(selector).first
            if control.count() == 0:
                continue
            classes = (control.get_attribute("class") or "").lower()
            aria_disabled = (control.get_attribute("aria-disabled") or "").lower()
            if "disabled" in classes or aria_disabled == "true":
                continue
            previous_html = page.content()
            control.click()
            try:
                page.wait_for_load_state("networkidle", timeout=10_000)
            except TimeoutError:
                page.wait_for_timeout(800)
            if page.content() != previous_html:
                return True
        return False

    @staticmethod
    def _page_signature(records: list[dict[str, str]]) -> str:
        payload = "\n".join(sorted(record.get("row_text", "") for record in records))
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()
