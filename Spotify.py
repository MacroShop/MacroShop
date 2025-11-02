import time
import random
import string
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def random_email():
    return f"{''.join(random.choices(string.ascii_lowercase, k=9))}@fabricoak.com"

def random_password():
    upper = random.choice(string.ascii_uppercase)
    lower = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    remaining = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    password = list(upper + lower + digit + remaining)
    random.shuffle(password)
    return ''.join(password)[:25]

def create_hm_account(driver):
    try:
        # E-posta oluştur
        email = random_email()
        password = random_password()

        # E-posta alanını doldur
        driver.find_element(By.XPATH, '/html/body/div/main/div/form/div[1]/div/input').send_keys(email)
        time.sleep(0.5)
        
        # Devam butonuna tıkla
        driver.find_element(By.XPATH, '/html/body/div/main/div/form/button').click()
        time.sleep(1)
        
        # Şifre alanını doldur
        driver.find_element(By.XPATH, '/html/body/div/main/div/form/div[1]/div/input').send_keys(password)
        time.sleep(0.5)
        
        # Doğum tarihi
        driver.find_element(By.XPATH, '/html/body/div/main/div/form/div[3]/div/div/input[1]').send_keys("30")
        driver.find_element(By.XPATH, '/html/body/div/main/div/form/div[3]/div/div/input[2]').send_keys("03")
        driver.find_element(By.XPATH, '/html/body/div/main/div/form/div[3]/div/div/input[3]').send_keys("2000")
        time.sleep(0.5)
        
        # Üye ol butonuna tıkla
        driver.find_element(By.XPATH, '/html/body/div/main/div/form/button[1]').click()
        time.sleep(1)  # Kayıt olduktan sonra 1 saniye bekle
        
        # Fırsat kodunu almak için elementin görünmesini bekle (maksimum 10 saniye)
        try:
            offer_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '/html/body/div/div[2]/div/div/main/div/ul/li[3]/button/article/div[1]/span/img'))
            )
            offer_button.click()
            time.sleep(2)
            
            code_element = driver.find_element(By.XPATH, '/html/body/div/div[2]/div/div/main/div/div[2]/div/div[3]/p')
            code = code_element.text.split()[-1]
            
            # Sadece kodu dosyaya kaydet
            with open('HM Kodlar.txt', 'a') as f:
                f.write(f"{code}\n")
            
            return True
            
        except Exception as e:
            print(f"Fırsat kodu elementi görüntülenemedi: {e}")
            return False
        
    except Exception as e:
        print(f"Hata oluştu: {e}")
        return False

def main():
    driver = setup_driver()
    
    try:
        for i in range(3):  # 3 hesap oluştur
            print(f"\n--- {i+1}. Hesap Oluşturuluyor ---")
            driver.get("https://www2.hm.com/tr_tr/login")
            time.sleep(2)
            
            if create_hm_account(driver):
                print(f"{i+1}. hesap başarıyla oluşturuldu ve fırsat kodu alındı!")
            else:
                print(f"{i+1}. hesap oluşturuldu ancak fırsat kodu alınamadı")
            
            # Çerezleri temizle
            driver.delete_all_cookies()
            time.sleep(1)
            
    finally:
        driver.quit()
        print("\nİşlem tamamlandı!")

if __name__ == "__main__":
    main()
