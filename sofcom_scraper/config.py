from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(slots=True)
class AppConfig:
    base_url: str
    login_url: str
    tracking_url: str
    username: str
    password: str
    output_dir: Path
    headless: bool
    timezone: str
    schedule_hour: int
    schedule_minute: int
    max_login_attempts: int
    max_pages: int
    username_selector: str
    password_selector: str
    captcha_input_selector: str
    captcha_image_selector: str
    login_button_selector: str
    action_select_selector: str
    action_search_button_selector: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        base_url = os.getenv("SOFCOM_BASE_URL", "https://sofcom.nraposoft.com").rstrip("/")
        login_url = os.getenv("SOFCOM_LOGIN_URL", f"{base_url}/Default")
        tracking_url = os.getenv(
            "SOFCOM_TRACKING_URL",
            f"{base_url}/Pages/Tracking/TrackingForm",
        )
        output_dir = Path(os.getenv("SOFCOM_OUTPUT_DIR", "output")).expanduser().resolve()

        return cls(
            base_url=base_url,
            login_url=login_url,
            tracking_url=tracking_url,
            username=os.getenv("SOFCOM_USERNAME", "").strip(),
            password=os.getenv("SOFCOM_PASSWORD", "").strip(),
            output_dir=output_dir,
            headless=_env_bool("SOFCOM_HEADLESS", True),
            timezone=os.getenv("SOFCOM_TIMEZONE", "Europe/Sofia"),
            schedule_hour=_env_int("SOFCOM_SCHEDULE_HOUR", 19),
            schedule_minute=_env_int("SOFCOM_SCHEDULE_MINUTE", 0),
            max_login_attempts=_env_int("SOFCOM_MAX_LOGIN_ATTEMPTS", 6),
            max_pages=_env_int("SOFCOM_MAX_PAGES", 50),
            username_selector=os.getenv("SOFCOM_USERNAME_SELECTOR", "#txtUser"),
            password_selector=os.getenv("SOFCOM_PASSWORD_SELECTOR", "#txtPassword"),
            captcha_input_selector=os.getenv(
                "SOFCOM_CAPTCHA_INPUT_SELECTOR",
                "#Captcha1_CaptchaTextBox",
            ),
            captcha_image_selector=os.getenv(
                "SOFCOM_CAPTCHA_IMAGE_SELECTOR",
                "#Captcha1_CaptchaImage",
            ),
            login_button_selector=os.getenv("SOFCOM_LOGIN_BUTTON_SELECTOR", "#btnLogIna"),
            action_select_selector=os.getenv("SOFCOM_ACTION_SELECT_SELECTOR", ""),
            action_search_button_selector=os.getenv("SOFCOM_ACTION_SEARCH_BUTTON_SELECTOR", ""),
        )
