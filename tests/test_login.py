import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions

def test_login_browserstack():
    load_dotenv()

    username = os.getenv("BROWSERSTACK_USERNAME")
    access_key = os.getenv("BROWSERSTACK_ACCESS_KEY")
    flask_url = "https://5cf2e82ed32a.ngrok-free.app/login"  # Cambia si regeneras el túnel

    # Configuración de Edge para BrowserStack
    edge_options = EdgeOptions()
    edge_options.set_capability("browserName", "Edge")
    edge_options.set_capability("browserVersion", "latest")
    edge_options.set_capability("bstack:options", {
        "os": "Windows",
        "osVersion": "10",
        "sessionName": "Login Flask ngrok",
        "buildName": "Build Final",
        "userName": username,
        "accessKey": access_key
    })

    driver = webdriver.Remote(
        command_executor="https://hub-cloud.browserstack.com/wd/hub",
        options=edge_options
    )

    try:
        print("Accediendo a:", flask_url)
        driver.get(flask_url)
        time.sleep(3)

        # Intentar detectar iframe (por si el botón está allí)
        try:
            print("Buscando iframe...")
            iframe = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "iframe"))
            )
            driver.switch_to.frame(iframe)
            print("Iframe detectado.")
        except:
            print("No se encontró iframe.")

        # Buscar y hacer clic en el botón 'Visit Site'
        try:
            print("Buscando botón 'Visit Site'...")
            visit_button = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Visit Site')]"))
            )
            driver.execute_script("arguments[0].click();", visit_button)
            print("Botón clickeado.")
            driver.switch_to.default_content()
            time.sleep(3)
        except Exception as e:
            print("Botón no detectado:", e)
            print("HTML parcial:\n", driver.page_source[:500])

        # Interactuar con el formulario de login
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        driver.find_element(By.ID, "username").send_keys("andre")
        driver.find_element(By.ID, "password").send_keys("123456789")
        driver.find_element(By.TAG_NAME, "button").click()
        time.sleep(2)

        # Validar resultado de login
        assert "Sistema de Facturación" in driver.page_source

        # Marcar la prueba como exitosa en BrowserStack
        driver.execute_script(
            'browserstack_executor: {"action": "setSessionStatus", "arguments": '
            '{"status":"passed","reason": "Login exitoso y redirigido correctamente"}}'
        )

    except Exception as e:
        # Marcar como fallida
        driver.execute_script(
            'browserstack_executor: {"action": "setSessionStatus", "arguments": '
            f'{{"status":"failed","reason": "{str(e)}"}}}}'
        )
        raise

    finally:
        driver.quit()