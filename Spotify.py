import random
import re
import string
from pathlib import Path
from typing import Optional, Sequence, Tuple

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

LOGIN_URL = "https://www2.hm.com/tr_tr/login"
CODE_FILE = Path("HM Kodlar.txt")
DEFAULT_WAIT = 20
ACCOUNT_CREATION_COUNT = 3
CODE_PATTERN = re.compile(r"[A-Z0-9]{6,}")

Locator = Tuple[str, str]
LocatorList = Sequence[Locator]

EMAIL_INPUT_LOCATORS: LocatorList = (
    (By.CSS_SELECTOR, "main form input[type='email']"),
    (By.CSS_SELECTOR, "main form input[name*='mail']"),
    (By.CSS_SELECTOR, "form input[id*='mail']"),
)

CONTINUE_BUTTON_LOCATORS: LocatorList = (
    (By.CSS_SELECTOR, "main form button[type='submit']"),
    (By.CSS_SELECTOR, "form button[id*='continue']"),
    (By.CSS_SELECTOR, "form button[name*='continue']"),
)

PASSWORD_INPUT_LOCATORS: LocatorList = (
    (By.CSS_SELECTOR, "main form input[type='password']"),
    (By.CSS_SELECTOR, "main form input[name*='password']"),
    (By.CSS_SELECTOR, "form input[id*='password']"),
)

BIRTH_DAY_INPUT_LOCATORS: LocatorList = (
    (By.CSS_SELECTOR, "main form input[name*='day']"),
    (By.CSS_SELECTOR, "main form input[id*='day']"),
)

BIRTH_MONTH_INPUT_LOCATORS: LocatorList = (
    (By.CSS_SELECTOR, "main form input[name*='month']"),
    (By.CSS_SELECTOR, "main form input[id*='month']"),
)

BIRTH_YEAR_INPUT_LOCATORS: LocatorList = (
    (By.CSS_SELECTOR, "main form input[name*='year']"),
    (By.CSS_SELECTOR, "main form input[id*='year']"),
)

REGISTER_BUTTON_LOCATORS: LocatorList = (
    (By.CSS_SELECTOR, "main form button[type='submit']"),
    (By.CSS_SELECTOR, "form button[id*='register']"),
    (By.CSS_SELECTOR, "form button[name*='register']"),
)

OFFER_BUTTON_LOCATORS: LocatorList = (
    (By.CSS_SELECTOR, "ul li button[data-testid*='voucher']"),
    (By.CSS_SELECTOR, "ul li button[aria-label*='kod']"),
    (By.CSS_SELECTOR, "button[data-testid*='voucher']"),
    (By.CSS_SELECTOR, "button[data-testid*='offer']"),
    (By.CSS_SELECTOR, "button[aria-label*='Voucher']"),
    (By.CSS_SELECTOR, "button[aria-label*='Fırsat']"),
    (By.CSS_SELECTOR, "ul li:nth-child(3) button"),
)

CODE_TEXT_LOCATORS: LocatorList = (
    (By.CSS_SELECTOR, "div[data-testid*='voucher'] p"),
    (By.CSS_SELECTOR, "div p[data-testid*='code']"),
    (By.CSS_SELECTOR, "p[data-testid*='voucher']"),
    (By.CSS_SELECTOR, "main div p"),
)


def setup_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)
    options.page_load_strategy = "eager"

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(40)
    driver.implicitly_wait(0)
    return driver


def _wait_for_condition(
    driver: webdriver.Chrome,
    locators: LocatorList,
    condition_builder,
    timeout: int,
):
    last_exc: Optional[Exception] = None
    for locator in locators:
        try:
            return WebDriverWait(driver, timeout).until(condition_builder(locator))
        except TimeoutException as exc:
            last_exc = exc
        except WebDriverException as exc:
            last_exc = exc
    if isinstance(last_exc, TimeoutException):
        raise last_exc
    if last_exc:
        raise TimeoutException("Beklenen element bulunamadı.") from last_exc
    raise TimeoutException("Beklenen element bulunamadı.")


def wait_for_clickable(driver: webdriver.Chrome, locators: LocatorList, timeout: int = DEFAULT_WAIT):
    return _wait_for_condition(driver, locators, EC.element_to_be_clickable, timeout)


def wait_for_presence(driver: webdriver.Chrome, locators: LocatorList, timeout: int = DEFAULT_WAIT):
    return _wait_for_condition(driver, locators, EC.presence_of_element_located, timeout)


def wait_for_visibility(driver: webdriver.Chrome, locators: LocatorList, timeout: int = DEFAULT_WAIT):
    return _wait_for_condition(driver, locators, EC.visibility_of_element_located, timeout)


def wait_and_send_keys(
    driver: webdriver.Chrome,
    locators: LocatorList,
    value: str,
    *,
    timeout: int = DEFAULT_WAIT,
    clear: bool = True,
):
    element = wait_for_clickable(driver, locators, timeout)
    if clear:
        element.clear()
    element.send_keys(value)
    return element


def wait_and_click(driver: webdriver.Chrome, locators: LocatorList, timeout: int = DEFAULT_WAIT):
    element = wait_for_clickable(driver, locators, timeout)
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    try:
        element.click()
    except WebDriverException:
        driver.execute_script("arguments[0].click();", element)
    return element


def random_email(prefix_length: int = 9) -> str:
    local_part = "".join(random.choices(string.ascii_lowercase + string.digits, k=prefix_length))
    return f"{local_part}@fabricoak.com"


def random_password(length: int = 12) -> str:
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


def parse_offer_code(raw_text: str) -> Optional[str]:
    if not raw_text:
        return None
    candidates = CODE_PATTERN.findall(raw_text.upper())
    return candidates[-1] if candidates else None


def create_hm_account(driver: webdriver.Chrome) -> Tuple[Optional[str], Optional[str]]:
    email = random_email()
    password = random_password()

    try:
        wait_and_send_keys(driver, EMAIL_INPUT_LOCATORS, email)
        wait_and_click(driver, CONTINUE_BUTTON_LOCATORS)

        wait_and_send_keys(driver, PASSWORD_INPUT_LOCATORS, password)

        for locators, value in (
            (BIRTH_DAY_INPUT_LOCATORS, "30"),
            (BIRTH_MONTH_INPUT_LOCATORS, "03"),
            (BIRTH_YEAR_INPUT_LOCATORS, "2000"),
        ):
            wait_and_send_keys(driver, locators, value)

        wait_and_click(driver, REGISTER_BUTTON_LOCATORS)

        try:
            wait_and_click(driver, OFFER_BUTTON_LOCATORS, timeout=15)
        except TimeoutException:
            print("Fırsat kodu butonu görüntülenemedi.")
            return email, None

        try:
            code_element = wait_for_visibility(driver, CODE_TEXT_LOCATORS, timeout=15)
        except TimeoutException:
            print("Fırsat kodu metni yüklenmedi.")
            return email, None

        code = parse_offer_code(code_element.text)
        if not code:
            print(f"Fırsat kodu metninden kod ayrıştırılamadı: {code_element.text!r}")
            return email, None

        return email, code

    except TimeoutException as exc:
        print(f"Zaman aşımına uğradı: {exc}")
    except WebDriverException as exc:
        print(f"Selenium hatası: {exc}")
    except Exception as exc:
        print(f"Beklenmedik hata oluştu: {exc}")

    return email, None


def reset_session(driver: webdriver.Chrome) -> None:
    driver.delete_all_cookies()
    try:
        driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
    except WebDriverException:
        pass


def main() -> None:
    driver = setup_driver()
    CODE_FILE.touch(exist_ok=True)

    try:
        for index in range(ACCOUNT_CREATION_COUNT):
            print(f"\n--- {index + 1}. Hesap oluşturuluyor ---")

            try:
                driver.get(LOGIN_URL)
            except WebDriverException as exc:
                print(f"Giriş sayfası yüklenemedi: {exc}")
                break

            try:
                wait_for_presence(driver, EMAIL_INPUT_LOCATORS)
            except TimeoutException:
                print("Giriş sayfası zaman aşımına uğradı.")
                break

            email, code = create_hm_account(driver)

            if code:
                print(f"{index + 1}. hesap başarıyla oluşturuldu (email: {email})")
                with CODE_FILE.open("a", encoding="utf-8") as file:
                    file.write(f"{code}\n")
                print("Fırsat kodu kaydedildi.")
            else:
                print(f"{index + 1}. hesap için fırsat kodu alınamadı (email: {email or 'bilinmiyor'})")

            reset_session(driver)

    finally:
        driver.quit()
        print("\nİşlem tamamlandı!")


if __name__ == "__main__":
    main()
