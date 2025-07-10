import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions

def test_login_sauce():
    load_dotenv()

    username = os.getenv("SAUCE_USERNAME")
    access_key = os.getenv("SAUCE_ACCESS_KEY")
    flask_url = "https://5cf2e82ed32a.ngrok-free.app/login"

    sauce_url = f"https://{username}:{access_key}@ondemand.us-west-1.saucelabs.com:443/wd/hub"
    
    options = EdgeOptions()
    options.set_capability("browserName", "MicrosoftEdge")
    options.set_capability("browserVersion", "latest")
    options.set_capability("sauce:options", {
        "platformName": "Windows 10",
        "build": "Login SauceLabs",
        "name": "Login Flask ngrok"
    })

    driver = webdriver.Remote(command_executor=sauce_url, options=options)

    try:
        print("Accediendo a:", flask_url)
        driver.get(flask_url)
        time.sleep(3)

        # Detectar iframe (advertencia ngrok)
        try:
            print("Buscando iframe...")
            iframe = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "iframe"))
            )
            driver.switch_to.frame(iframe)
            print("Iframe encontrado.")
        except:
            print("No se encontró iframe. Continuamos...")

        # Detectar botón Visit Site
        try:
            print("Buscando botón 'Visit Site'...")
            visit_button = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Visit Site')]"))
            )
            driver.execute_script("arguments[0].click();", visit_button)
            driver.switch_to.default_content()
            print("Botón clickeado.")
            time.sleep(2)
        except Exception as e:
            print("No se detectó el botón:", e)
            print("HTML parcial:", driver.page_source[:500])

        # Login
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        driver.find_element(By.ID, "username").send_keys("andre")
        driver.find_element(By.ID, "password").send_keys("123456789")
        driver.find_element(By.TAG_NAME, "button").click()
        time.sleep(2)

        # Validación del contenido post-login
        assert "Sistema de Facturación" in driver.page_source

        # Notificar a Sauce que pasó
        driver.execute_script('sauce:job-result=passed')

    except Exception as e:
        driver.execute_script('sauce:job-result=failed')
        raise e

    finally:
        driver.quit()