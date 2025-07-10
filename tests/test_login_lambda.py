import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
load_dotenv() 

def test_login_lambdatest():
    load_dotenv()
    username = os.getenv("LT_USERNAME")
    access_key = os.getenv("LT_ACCESS_KEY")
    flask_url = "https://5cf2e82ed32a.ngrok-free.app/login"

    LT_GRID_URL = f"https://{username}:{access_key}@hub.lambdatest.com/wd/hub"

    options = Options()
    options.set_capability("browserName", "MicrosoftEdge")
    options.set_capability("browserVersion", "latest")
    options.set_capability("LT:Options", {
        "platformName": "Windows 10",
        "build": "Login Tests",
        "name": "LambdaTest Login Test"
    })

    driver = webdriver.Remote(command_executor=LT_GRID_URL, options=options)

    try:
        print("Accediendo a:", flask_url)
        driver.get(flask_url)
        time.sleep(3)

        # Bypass advertencia de ngrok si aparece
        try:
            print("Buscando botón 'Visit Site'...")
            visit_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Visit Site')]"))
            )
            driver.execute_script("arguments[0].click();", visit_button)
            print("Advertencia ngrok saltada.")
            time.sleep(3)
        except:
            print("No se detectó advertencia de ngrok.")

        # Login
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        ).send_keys("andre")
        driver.find_element(By.ID, "password").send_keys("123456789")
        driver.find_element(By.TAG_NAME, "button").click()
        time.sleep(3)

        assert "Cerrar sesión" in driver.page_source
        print("Prueba pasada en LambdaTest.")
    finally:
        driver.quit()