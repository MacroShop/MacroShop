import time
import random
import string
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Telegram Bot Token ve Chat ID
TELEGRAM_BOT_TOKEN = '8201625011:AAE-VZuG35zPjBQl1QtH6zmdQ-WFMkH9Lrg'
TELEGRAM_CHAT_ID = '8299177286'

# Telegram'a mesaj gönderme fonksiyonu
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    response = requests.post(url, json=payload)
    return response.json()

# Chrome WebDriver'ı Otomatik Kur
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")  # Tarayıcıyı tam ekran aç
options.add_argument("--disable-blink-features=AutomationControlled")  # Bot tespitini önler
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Rastgele 9 harfli e-posta oluştur (küçük harfler)
def random_email():
    letters = string.ascii_lowercase
    random_part = ''.join(random.choices(letters, k=9))
    return f"{random_part}@macroshoptr.com.tr"

# Rastgele 9 karakterli şifre oluştur (En az bir büyük harf, bir küçük harf ve bir sayı içerir)
def random_password():
    # En az bir büyük harf, bir küçük harf ve bir sayı içeren 9 karakterli şifre oluştur
    uppercase = random.choice(string.ascii_uppercase)
    lowercase = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    remaining_chars = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    password = uppercase + lowercase + digit + remaining_chars
    # Şifreyi karıştır
    password_list = list(password)
    random.shuffle(password_list)
    return ''.join(password_list)

# Bitdefender Hesap Oluşturma Sayfasına Git
driver.get("https://login.bitdefender.com/central/signup.html?lang=tr_TR&redirect_url=https:%2F%2Fcentral.bitdefender.com%2Fdashboard%3Fservice%3Dadd_trial%26code%3D34291885-79d4-4ba6-bf01-30b0d6bdd0a1%26adobe_mc%3DMCMID%2525253D03619315198037007030084397437691590274%2525257CMCORGID%2525253D0E920C0F53DA9E9B0A490D45%2525252540AdobeOrg%2525257CTS%2525253D1698145840%26final_url%3D%2Fdevices")

# Sayfanın tam yüklenmesini bekle
time.sleep(1)

# Çerez reddetme pop-up'ını kapat
try:
    reject_cookies_button = driver.find_element(By.XPATH, '/html/body/div[6]//div/div/div[2]/div/div[2]/div/div[2]/div/div[1]/div/button[2]')
    reject_cookies_button.click()  # Çerezleri reddet
except Exception as e:
    print(f"Çerez reddetme butonu bulunamadı! Hata: {str(e)}")

# Form Alanlarını Doldur
# Tam İsim
driver.find_element(By.XPATH, '/html/body/ui-view/div/main/div/div[1]/ui-view/form/div[3]/div[1]/input').send_keys("MacroShop")

# E-posta
email = random_email()
driver.find_element(By.XPATH, '/html/body/ui-view/div/main/div/div[1]/ui-view/form/div[3]/div[2]/input').send_keys(email)

# Şifre
password = random_password()
driver.find_element(By.XPATH, '/html/body/ui-view/div/main/div/div[1]/ui-view/form/div[3]/div[3]/div[1]/input').send_keys(password)

# Kullanım Koşullarını Onayla
try:
    terms_checkbox = driver.find_element(By.XPATH, '/html/body/ui-view/div/main/div/div[1]/ui-view/form/div[3]/div[5]/div/input')
    driver.execute_script("arguments[0].click();", terms_checkbox)
except:
    print("Kullanım koşulları kutucuğu bulunamadı!")

# Hesap Oluştur Butonuna Tıkla
try:
    create_account_button = driver.find_element(By.XPATH, '/html/body/ui-view/div/main/div/div[1]/ui-view/form/div[4]/div/div[2]/button')
    driver.execute_script("arguments[0].click();", create_account_button)
except:
    print("'Hesap Oluştur' butonu bulunamadı!")

# Sayfanın tamamen yüklenmesini bekle
time.sleep(3)

# VPN Sayfasına Git
driver.get("https://central.bitdefender.com/vpn")

# Sayfanın tamamen yüklenmesini bekle
time.sleep(2)

# Hesap bilgilerini ekrana yazdır
print(f"Hesap oluşturuldu! E-posta: {email} | Şifre: {password}")

# E-posta ve şifreyi masaüstündeki dosyaya kaydet
file_path = r'C:\Users\EREN\Desktop\Bitdefender Hesap.txt'
with open(file_path, 'a') as file:
    file.write(f"{email} - {password}\n")
print(f"Hesap bilgileri '{file_path}' dosyasına kaydedildi.")

# Telegram'a mesaj gönder
current_date = time.strftime("%d/%m/%Y")
telegram_message = f"Bitdefender Hesap - [{current_date}]\n\nE-posta: {email} | Şifre: {password}"
send_telegram_message(telegram_message)
print("Hesap bilgileri Telegram'a gönderildi.")

# Tarayıcıyı kapat
driver.quit()
