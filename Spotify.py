import random
import string
import time
from pathlib import Path
from typing import Optional, Tuple

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

EMAIL_INPUT = (By.XPATH, "/html/body/div/main/div/form/div[1]/div/input")
CONTINUE_BUTTON = (By.XPATH, "/html/body/div/main/div/form/button")
PASSWORD_INPUT = (By.XPATH, "/html/body/div/main/div/form/div[1]/div/input")
BIRTH_DAY_INPUT = (By.XPATH, "/html/body/div/main/div/form/div[3]/div/div/input[1]")
BIRTH_MONTH_INPUT = (By.XPATH, "/html/body/div/main/div/form/div[3]/div/div/input[2]")
BIRTH_YEAR_INPUT = (By.XPATH, "/html/body/div/main/div/form/div[3]/div/div/input[3]")
REGISTER_BUTTON = (By.XPATH, "/html/body/div/main/div/form/button[1]")
OFFER_BUTTON = (By.XPATH, "/html/body/div/div[2]/div/div/main/div/ul/li[3]/button/article/div[1]/span/img")
CODE_TEXT = (By.XPATH, "/html/body/div/div[2]/div/div/main/div/div[2]/div/div[3]/p")


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


def wait_for_clickable(driver: webdriver.Chrome, locator: Tuple[str, str], timeout: int = DEFAULT_WAIT):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))


def wait_and_send_keys(
    driver: webdriver.Chrome,
    locator: Tuple[str, str],
    value: str,
    *,
    timeout: int = DEFAULT_WAIT,
    clear: bool = True,
):
    element = wait_for_clickable(driver, locator, timeout)
    if clear:
        element.clear()
    element.send_keys(value)
    return element


def wait_and_click(
    driver: webdriver.Chrome,
    locator: Tuple[str, str],
    timeout: int = DEFAULT_WAIT,
    *,
    delay_before_click: float = 0.0,
    delay_after_click: float = 0.0,
):
    element = wait_for_clickable(driver, locator, timeout)
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    if delay_before_click > 0:
        time.sleep(delay_before_click)
    try:
        element.click()
    except WebDriverException:
        driver.execute_script("arguments[0].click();", element)
    if delay_after_click > 0:
        time.sleep(delay_after_click)
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
    parts = raw_text.strip().split()
    return parts[-1] if parts else None


def create_hm_account(driver: webdriver.Chrome) -> Tuple[Optional[str], Optional[str]]:
    email = random_email()
    password = random_password()

    try:
        wait_and_send_keys(driver, EMAIL_INPUT, email)
        wait_and_click(driver, CONTINUE_BUTTON, delay_before_click=2)

        wait_and_send_keys(driver, PASSWORD_INPUT, password)

        for locator, value in (
            (BIRTH_DAY_INPUT, "30"),
            (BIRTH_MONTH_INPUT, "03"),
            (BIRTH_YEAR_INPUT, "2000"),
        ):
            wait_and_send_keys(driver, locator, value)

        wait_and_click(driver, REGISTER_BUTTON, delay_before_click=2)

        try:
            wait_and_click(driver, OFFER_BUTTON, timeout=15)
        except TimeoutException:
            print("Fırsat kodu butonu görüntülenemedi.")
            return email, None

        try:
            code_element = WebDriverWait(driver, 15).until(EC.visibility_of_element_located(CODE_TEXT))
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
                WebDriverWait(driver, DEFAULT_WAIT).until(EC.presence_of_element_located(EMAIL_INPUT))
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
