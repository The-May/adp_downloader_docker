import sys
import configparser
from playwright.sync_api import sync_playwright, TimeoutError

CONFIG_FILE = "config.ini"


def load_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    username = config["credentials"]["username"]
    password = config["credentials"]["password"]

    return config, username, password


def save_cookie(config, emeas_value):
    config["credentials"]["cookie"] = emeas_value

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        config.write(f)


config, USERNAME, PASSWORD = load_config()

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir="adp_profile",
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox"],
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    page = browser.new_page()

    try:
        page.goto("https://adpworld.adp.com/", timeout=60000)

        # username
        page.wait_for_selector("#login-form_username input", timeout=30000)
        page.locator("#login-form_username input").fill(USERNAME)
        page.locator("#verifUseridBtn").click()

        # password
        page.wait_for_selector("#login-form_password input", timeout=30000)
        page.locator("#login-form_password input").fill(PASSWORD)
        page.locator("#signBtn").click()

        page.wait_for_load_state("networkidle", timeout=60000)

        # extract cookie
        cookies = browser.cookies()
        emeas_cookie = None

        for c in cookies:
            if c["name"] == "EMEASMSESSION":
                emeas_cookie = c["value"]
                break

        # success only if cookie exists
        if emeas_cookie:
            save_cookie(config, emeas_cookie)
            print("Login successful.")
            print("EMEASMSESSION saved to config.ini")
            browser.close()
            sys.exit(0)

        else:
            print("Login failed: EMEASMSESSION not found.")
            browser.close()
            sys.exit(1)

    except TimeoutError:
        print("Login failed: timeout.")
        browser.close()
        sys.exit(1)

    except Exception as e:
        print("Login failed:", str(e))
        browser.close()
        sys.exit(1)
