"""H&M hesap oluşturma otomasyonu.

Bu modül, Selenium kullanarak H&M Türkiye sitesinde hesap oluşturup kampanya
kodlarını toplamayı amaçlar. Kod, dayanıklılık ve performans için
iyileştirilmiştir ve komut satırından yapılandırılabilir hale getirilmiştir.
"""

from __future__ import annotations

import argparse
import logging
import random
import re
import string
import sys
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Sequence, Tuple

from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    UnexpectedAlertPresentException,
    WebDriverException,
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

Locator = Tuple[str, str]
ConditionFactory = Callable[[Locator], Callable[[webdriver.Chrome], object]]

DEFAULT_LOGIN_URL = "https://www2.hm.com/tr_tr/login"
DEFAULT_CODE_FILE = Path("HM Kodlar.txt")
DEFAULT_WAIT_TIMEOUT = 20
DEFAULT_ACCOUNT_COUNT = 3
DEFAULT_EMAIL_DOMAIN = "fabricoak.com"
DEFAULT_PASSWORD_LENGTH = 12
CODE_REGEX = re.compile(r"\b[A-Z0-9]{6,}\b")


@dataclass(frozen=True)
class HMConfig:
    """Otomasyon için temel yapılandırma."""

    login_url: str = DEFAULT_LOGIN_URL
    code_file: Path = DEFAULT_CODE_FILE
    wait_timeout: int = DEFAULT_WAIT_TIMEOUT
    account_count: int = DEFAULT_ACCOUNT_COUNT
    headless: bool = False
    email_domain: str = DEFAULT_EMAIL_DOMAIN
    password_length: int = DEFAULT_PASSWORD_LENGTH


@dataclass(frozen=True)
class HMSelectors:
    """Sayfa öğeleri için birden fazla yedek lokatör içerir."""

    email_inputs: Sequence[Locator] = (
        (By.CSS_SELECTOR, "input[name='email']"),
        (By.CSS_SELECTOR, "form input[type='email']"),
        (By.XPATH, "//input[@type='email']"),
        (By.XPATH, "/html/body/div/main/div/form/div[1]/div[1]/input"),
    )
    continue_buttons: Sequence[Locator] = (
        (By.CSS_SELECTOR, "form button[type='submit']"),
        (By.XPATH, "//button[contains(@type,'submit')]") ,
        (By.XPATH, "//button[contains(., 'Devam') or contains(., 'Continue')]") ,
        (By.XPATH, "/html/body/div/main/div/form/div[2]/button"),
    )
    password_inputs: Sequence[Locator] = (
        (By.CSS_SELECTOR, "input[name='password']"),
        (By.CSS_SELECTOR, "form input[type='password']"),
        (By.XPATH, "//input[@type='password']"),
        (By.XPATH, "/html/body/div/main/div/form/div[1]/div[1]/input"),
    )
    birth_day_inputs: Sequence[Locator] = (
        (By.CSS_SELECTOR, "input[name='day']"),
        (By.XPATH, "//input[@placeholder='GG' or @aria-label='Gün']"),
        (By.XPATH, "/html/body/div/main/div/form/div[3]/div[1]/div/input[1]"),
    )
    birth_month_inputs: Sequence[Locator] = (
        (By.CSS_SELECTOR, "input[name='month']"),
        (By.XPATH, "//input[@placeholder='AA' or @aria-label='Ay']"),
        (By.XPATH, "/html/body/div/main/div/form/div[3]/div[1]/div/input[2]"),
    )
    birth_year_inputs: Sequence[Locator] = (
        (By.CSS_SELECTOR, "input[name='year']"),
        (By.XPATH, "//input[@placeholder='YYYY' or @aria-label='Yıl']"),
        (By.XPATH, "/html/body/div/main/div/form/div[3]/div[1]/div/input[3]"),
    )
    register_buttons: Sequence[Locator] = (
        (By.CSS_SELECTOR, "form button[type='submit']"),
        (By.XPATH, "//button[contains(., 'Kaydol') or contains(., 'Üye ol') or contains(., 'Join')]") ,
        (By.XPATH, "/html/body/div/main/div/form/button[1]"),
    )
    offer_buttons: Sequence[Locator] = (
        (By.XPATH, "//button[.//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZÇĞİÖŞÜ', 'abcdefghijklmnopqrstuvwxyzçğiöşü'), 'fırsat')]]"),
        (By.XPATH, "//button[contains(., '150') or contains(., 'Hediye') or contains(., 'Offer')]") ,
        (By.XPATH, "/html/body/div/div/div/div/main/div/ul/li[8]/button"),
    )
    code_texts: Sequence[Locator] = (
        (By.CSS_SELECTOR, "[data-testid='voucher-code'], label[data-testid='code']"),
        (By.XPATH, "//label[contains(@class,'code') or contains(@data-testid,'code')]") ,
        (By.XPATH, "/html/body/div/div/div/div/main/div/div[2]/div/div[3]/label"),
    )
    cookie_accept_buttons: Sequence[Locator] = (
        (By.ID, "onetrust-accept-btn-handler"),
        (By.CSS_SELECTOR, "button[title*='kabul'], button[title*='accept']"),
        (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZÇĞİÖŞÜ', 'abcdefghijklmnopqrstuvwxyzçğiöşü'), 'tümünü kabul')]"),
        (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZÇĞİÖŞÜ', 'abcdefghijklmnopqrstuvwxyzçğiöşü'), 'kabul')]"),
    )
    cookie_iframes: Sequence[Locator] = (
        (By.CSS_SELECTOR, "iframe[id*='onetrust'], iframe[src*='consent']"),
    )


@dataclass
class HMAccountResult:
    """Oluşturulan hesapla ilgili bilgi ve durum."""

    email: str
    password: str
    code: Optional[str] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.code is not None and self.error is None


def configure_logging(verbose: bool) -> None:
    """Logging seviyesini kullanıcı tercihine göre ayarlar."""

    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


def random_email(prefix_length: int, domain: str) -> str:
    """Belirtilen uzunlukta rastgele e-posta üretir."""

    if prefix_length < 3:
        raise ValueError("E-posta yerel kısmı en az 3 karakter olmalıdır.")

    alphabet = string.ascii_lowercase + string.digits
    local_part = "".join(random.choices(alphabet, k=prefix_length))
    return f"{local_part}@{domain}"


def random_password(length: int) -> str:
    """Büyük, küçük harf ve rakam içeren rastgele parola üretir."""

    if length < 3:
        raise ValueError("Şifre uzunluğu en az 3 olmalıdır.")

    characters = string.ascii_letters + string.digits
    password = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
    ]
    password.extend(random.choices(characters, k=length - len(password)))
    random.shuffle(password)
    return "".join(password)


def generate_birthdate() -> Tuple[str, str, str]:
    """1-28 gün, 1-12 ay ve 1980-2003 arası yıl döndürür."""

    day = random.randint(1, 28)
    month = random.randint(1, 12)
    year = random.randint(1980, 2003)
    return f"{day:02d}", f"{month:02d}", str(year)


def parse_offer_code(raw_text: str) -> Optional[str]:
    """Ham metinden olası kampanya kodunu ayıklar."""

    if not raw_text:
        return None

    candidates = CODE_REGEX.findall(raw_text.upper())
    if not candidates:
        return None
    return candidates[-1]


def _normalize_locators(locators: Sequence[Locator] | Locator) -> Sequence[Locator]:
    if isinstance(locators, tuple) and len(locators) == 2 and all(isinstance(item, str) for item in locators):
        return (locators,)  # type: ignore[return-value]
    return tuple(locators)  # type: ignore[arg-type]


def wait_for_element(
    driver: webdriver.Chrome,
    locators: Sequence[Locator] | Locator,
    condition_factory: ConditionFactory,
    timeout: int,
) -> Any:
    """Birden fazla lokatör kullanarak koşulu sağlayan değeri döndürür."""

    normalized = _normalize_locators(locators)
    deadline = time.monotonic() + timeout
    last_error: Optional[Exception] = None

    for locator in normalized:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        try:
            wait = WebDriverWait(driver, remaining)
            condition = condition_factory(locator)
            element = wait.until(condition)
            return element
        except TimeoutException as exc:
            last_error = exc
            continue

    message = f"Öğe bulunamadı: {normalized!r}"
    raise TimeoutException(message) from last_error


def wait_for_optional(
    driver: webdriver.Chrome,
    locators: Sequence[Locator] | Locator,
    condition_factory: ConditionFactory,
    timeout: int,
) -> Optional[Any]:
    try:
        return wait_for_element(driver, locators, condition_factory, timeout)
    except TimeoutException:
        return None


def safe_clear(driver: webdriver.Chrome, element: WebElement) -> None:
    with suppress(WebDriverException):
        element.clear()
        if element.get_attribute("value"):
            raise WebDriverException("Alan temizlenmedi")

    with suppress(WebDriverException):
        driver.execute_script("arguments[0].value = '';", element)
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
            element,
        )


def safe_click(driver: webdriver.Chrome, element: WebElement) -> None:
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    with suppress(WebDriverException):
        element.click()
        return
    driver.execute_script("arguments[0].click();", element)


def wait_and_send_keys(
    driver: webdriver.Chrome,
    locators: Sequence[Locator] | Locator,
    value: str,
    timeout: int,
    *,
    clear: bool = True,
) -> WebElement:
    element_obj = wait_for_element(driver, locators, EC.element_to_be_clickable, timeout)
    if not isinstance(element_obj, WebElement):
        raise TypeError("Beklenen WebElement, farklı tür döndü")

    if clear:
        safe_clear(driver, element_obj)
    element_obj.send_keys(value)
    return element_obj


def wait_and_click(
    driver: webdriver.Chrome,
    locators: Sequence[Locator] | Locator,
    timeout: int,
) -> WebElement:
    element_obj = wait_for_element(driver, locators, EC.element_to_be_clickable, timeout)
    if not isinstance(element_obj, WebElement):
        raise TypeError("Beklenen WebElement, farklı tür döndü")
    safe_click(driver, element_obj)
    return element_obj


def wait_for_visibility(
    driver: webdriver.Chrome,
    locators: Sequence[Locator] | Locator,
    timeout: int,
) -> Optional[WebElement]:
    element_obj = wait_for_optional(driver, locators, EC.visibility_of_element_located, timeout)
    return element_obj if isinstance(element_obj, WebElement) else None


class HMAutomation:
    """H&M hesap oluşturma sürecini yöneten sınıf."""

    def __init__(self, config: HMConfig, selectors: Optional[HMSelectors] = None) -> None:
        self.config = config
        self.selectors = selectors or HMSelectors()
        self.driver = self._setup_driver()

    def _setup_driver(self) -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-notifications")
        options.add_argument("--window-size=1280,900")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option("useAutomationExtension", False)
        options.page_load_strategy = "eager"

        if self.config.headless:
            options.add_argument("--headless=new")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(40)
        driver.implicitly_wait(0)
        return driver

    def __enter__(self) -> "HMAutomation":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if getattr(self, "driver", None) is None:
            return
        with suppress(WebDriverException):
            self.driver.quit()
        self.driver = None  # type: ignore[assignment]

    def wait_for_document_ready(self, timeout: int = 15) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self.driver.execute_script("return document.readyState")
            if state == "complete":
                return
            time.sleep(0.1)

    def reset_session(self) -> None:
        if getattr(self, "driver", None) is None:
            return
        with suppress(WebDriverException):
            self.driver.delete_all_cookies()
        with suppress(WebDriverException):
            self.driver.execute_script(
                "window.localStorage.clear(); window.sessionStorage.clear();"
            )

    def accept_cookies_if_present(self) -> bool:
        driver = self.driver
        button_obj = wait_for_optional(driver, self.selectors.cookie_accept_buttons, EC.element_to_be_clickable, 5)
        if isinstance(button_obj, WebElement):
            logging.debug("Çerez bildirimi bulundu, kabul ediliyor.")
            safe_click(driver, button_obj)
            return True

        # Çerez bildirimi iframe içinde olabilir
        for iframe_locator in self.selectors.cookie_iframes:
            with suppress(TimeoutException):
                frame_ready = wait_for_optional(driver, iframe_locator, EC.frame_to_be_available_and_switch_to_it, 3)
                if not frame_ready:
                    continue
                button_obj = wait_for_optional(driver, self.selectors.cookie_accept_buttons, EC.element_to_be_clickable, 3)
                if isinstance(button_obj, WebElement):
                    logging.debug("Çerez bildirimi iframe içinde bulundu, kabul ediliyor.")
                    safe_click(driver, button_obj)
                    driver.switch_to.default_content()
                    return True
        with suppress(WebDriverException):
            driver.switch_to.default_content()
        return False

    def create_account(self) -> HMAccountResult:
        email = random_email(prefix_length=9, domain=self.config.email_domain)
        password = random_password(self.config.password_length)

        try:
            self.reset_session()
            self.driver.get(self.config.login_url)
            self.wait_for_document_ready()
            self.accept_cookies_if_present()

            wait_and_send_keys(self.driver, self.selectors.email_inputs, email, self.config.wait_timeout)
            wait_and_click(self.driver, self.selectors.continue_buttons, self.config.wait_timeout)

            wait_and_send_keys(self.driver, self.selectors.password_inputs, password, self.config.wait_timeout)
            day, month, year = generate_birthdate()
            wait_and_send_keys(self.driver, self.selectors.birth_day_inputs, day, self.config.wait_timeout)
            wait_and_send_keys(self.driver, self.selectors.birth_month_inputs, month, self.config.wait_timeout)
            wait_and_send_keys(self.driver, self.selectors.birth_year_inputs, year, self.config.wait_timeout)

            wait_and_click(self.driver, self.selectors.register_buttons, self.config.wait_timeout)

            offer_button_obj = wait_for_optional(
                self.driver,
                self.selectors.offer_buttons,
                EC.element_to_be_clickable,
                timeout=15,
            )
            if not isinstance(offer_button_obj, WebElement):
                logging.warning("Fırsat kodu butonu bulunamadı.")
                return HMAccountResult(email=email, password=password, code=None, error="Fırsat kodu butonu bulunamadı")

            safe_click(self.driver, offer_button_obj)

            code_element = wait_for_visibility(
                self.driver,
                self.selectors.code_texts,
                timeout=15,
            )
            if code_element is None:
                logging.warning("Fırsat kodu metni görülemedi.")
                return HMAccountResult(email=email, password=password, code=None, error="Fırsat kodu metni bulunamadı")

            code = parse_offer_code(code_element.text)
            if code is None:
                logging.warning("Metinden kod ayıklanamadı: %s", code_element.text)
                return HMAccountResult(email=email, password=password, code=None, error="Kod ayıklanamadı")

            logging.info("Hesap oluşturuldu: %s", email)
            return HMAccountResult(email=email, password=password, code=code)

        except UnexpectedAlertPresentException as exc:
            logging.error("Beklenmedik uyarı alındı: %s", exc)
            with suppress(WebDriverException):
                alert = self.driver.switch_to.alert
                alert.accept()
            return HMAccountResult(email=email, password=password, code=None, error=str(exc))
        except TimeoutException as exc:
            logging.error("Zaman aşımı: %s", exc)
            return HMAccountResult(email=email, password=password, code=None, error=str(exc))
        except WebDriverException as exc:
            logging.error("Selenium hatası: %s", exc)
            return HMAccountResult(email=email, password=password, code=None, error=str(exc))
        except Exception as exc:  # noqa: BLE001 - beklenmeyen hata yakalanıyor
            logging.exception("Beklenmedik hata")
            return HMAccountResult(email=email, password=password, code=None, error=str(exc))


def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="H&M hesap oluşturma otomasyonu")
    parser.add_argument(
        "-n",
        "--accounts",
        type=int,
        default=DEFAULT_ACCOUNT_COUNT,
        help="Oluşturulacak hesap sayısı",
    )
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=DEFAULT_WAIT_TIMEOUT,
        help="Öğe bekleme zaman aşımı (saniye)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_CODE_FILE),
        help="Kodların kaydedileceği dosya yolu",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Tarayıcıyı başlıksız (headless) çalıştır",
    )
    parser.add_argument(
        "--email-domain",
        type=str,
        default=DEFAULT_EMAIL_DOMAIN,
        help="Rastgele e-posta için kullanılacak domain",
    )
    parser.add_argument(
        "--password-length",
        type=int,
        default=DEFAULT_PASSWORD_LENGTH,
        help="Oluşturulacak şifre uzunluğu",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Ayrıntılı log çıktısı üret",
    )
    return parser.parse_args(argv)


def build_config(args: argparse.Namespace) -> HMConfig:
    code_file = Path(args.output).expanduser()
    code_file.parent.mkdir(parents=True, exist_ok=True)
    code_file.touch(exist_ok=True)

    if args.accounts <= 0:
        raise ValueError("Hesap sayısı 0'dan büyük olmalıdır.")
    if args.wait_timeout <= 0:
        raise ValueError("Bekleme süresi 0'dan büyük olmalıdır.")
    if args.password_length < 3:
        raise ValueError("Şifre uzunluğu en az 3 olmalıdır.")

    return HMConfig(
        account_count=args.accounts,
        wait_timeout=args.wait_timeout,
        code_file=code_file,
        headless=args.headless,
        email_domain=args.email_domain,
        password_length=args.password_length,
    )


def write_code(code_file: Path, code: str) -> None:
    with code_file.open("a", encoding="utf-8") as file:
        file.write(f"{code}\n")


def run(args: argparse.Namespace) -> int:
    configure_logging(args.verbose)
    try:
        config = build_config(args)
    except ValueError as exc:
        logging.error("Geçersiz parametre: %s", exc)
        return 1

    successes = 0
    failures = 0

    with HMAutomation(config) as automation:
        for index in range(1, config.account_count + 1):
            logging.info("%d/%d hesap oluşturuluyor...", index, config.account_count)
            result = automation.create_account()

            if result.success and result.code:
                write_code(config.code_file, result.code)
                successes += 1
                print(
                    f"{index}. hesap başarıyla oluşturuldu (email: {result.email}) | Kod: {result.code}"
                )
            else:
                failures += 1
                reason = result.error or "Bilinmeyen hata"
                print(
                    f"{index}. hesap için kod alınamadı (email: {result.email}). Sebep: {reason}"
                )

    logging.info("Toplam başarı: %d, başarısızlık: %d", successes, failures)
    print("İşlem tamamlandı!")
    return 0 if failures == 0 else 2


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_arguments(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
