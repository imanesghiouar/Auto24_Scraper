from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
from datetime import datetime

def init_auto24_driver(headless=True):
    """Initialise le driver Chrome avec les options personnalisées"""
    options = Options()
    
    # Configuration de base
    options.add_argument("--headless=new" if headless else "--start-maximized")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Mesures anti-détection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-direct-composition")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def scrape_auto24():
    """Scrape les annonces de voitures sur Auto24.ma"""
    driver = init_auto24_driver()
    driver.get("https://auto24.ma/buy-cars")
    
    data = []
    
    try:
        # Attente du chargement des annonces
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='card-holder']"))
        )

        listings = driver.find_elements(By.CSS_SELECTOR, "div.card-holder:not(.lds-roller)")
        
        if not listings:
            print("❌ Aucune annonce trouvée !")
            return

        print(f"✅ {len(listings)} annonces trouvées !")

        for idx, listing in enumerate(listings, start=1):
            try:
                # Scroll vers l'élément
                ActionChains(driver).move_to_element(listing).perform()
                
                # Extraction des données de base
                title = WebDriverWait(listing, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span.card-model"))
                ).text.strip()

                price = WebDriverWait(listing, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span.card-price:not(.card-old-price)"))
                ).text.strip()

                # Extraction des caractéristiques
                features = WebDriverWait(listing, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.card-features > span.features-container"))
                )
                transmission = features[0].text.split('\n')[-1].strip() if len(features) > 0 else "N/A"
                fuel_type = features[1].text.split('\n')[-1].strip() if len(features) > 1 else "N/A"
                mileage = features[2].text.split('\n')[-1].replace('KM', '').strip() if len(features) > 2 else "N/A"

                # Détection vendeur pro
                seller_type = "Professionnel" if listing.find_elements(By.CSS_SELECTOR, "div.card-brand-logo") else "Particulier"

                # Récupération du lien via JavaScript
                link = driver.execute_script(
                    "return arguments[0].querySelector('a').getAttribute('href');", 
                    listing
                )

                data.append([
                    idx,
                    title,
                    _clean_price(price),
                    transmission,
                    fuel_type,
                    mileage,
                    seller_type,
                    link
                ])

                print(f"✔ Annonce {idx} traitée")

            except Exception as e:
                print(f"⚠ Erreur avec l'annonce {idx}: {str(e)[:50]}...")
                continue

    finally:
        driver.quit()
        save_to_csv(data)

def _clean_price(price_str):
    """Nettoyage du prix"""
    try:
        return int(price_str.replace('DH', '')
                   .replace(' ', '')
                   .replace('\u202f', '')
                   .strip())
    except:
        return 0

def save_to_csv(data):
    """Sauvegarde des données"""
    columns = [
        "ID", 
        "Titre", 
        "Prix (DH)", 
        "Transmission", 
        "Type de carburant", 
        "Kilométrage", 
        "Vendeur", 
        "URL"
    ]
    
    filename = f"auto24_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(columns)
        writer.writerows(data)
    
    print(f"\n✅ Fichier {filename} généré avec {len(data)} annonces")

if __name__ == "__main__":
    scrape_auto24()