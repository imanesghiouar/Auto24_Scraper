from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import csv
from datetime import datetime
import os
import time

def init_auto24_driver(headless=True):
    """Initialise le driver Chrome avec les options personnalisées"""
    options = Options()
    options.add_argument("--headless=new" if headless else "--start-maximized")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def scrape_car_details(driver, url):
    """Scrape les détails complets d'une annonce Auto24.ma"""
    driver.get(url)
    details = {
        'date_mise_circulation': 'N/A',
        'kilometrage': 0,
        'carburant': 'N/A',
        'transmission': 'N/A',
        'places': 'N/A',
        'carrosserie': 'N/A',
        'nb_cles': 'N/A',
        'couleur_ext': 'N/A',
        'couleur_int': 'N/A',
        'nb_proprietaires': 'N/A',
        'condition': 'N/A',
        'equipements': [],
        'prix': 'N/A'
    }

    try:
        # Wait for main content container
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.ant-col.content-container"))
        )

        # Prix détaillé
        try:
            details['prix'] = driver.find_element(By.CSS_SELECTOR, "span.card-price").text.strip()
        except Exception as e:
            print(f"Erreur prix: {str(e)[:50]}")

        # Section Spécifications Techniques
        try:
            specs = driver.find_elements(By.CSS_SELECTOR, "div.specs-container div.spec-item")
            for spec in specs:
                try:
                    label = spec.find_element(By.CSS_SELECTOR, "span.spec-label").text.strip()
                    value = spec.find_element(By.CSS_SELECTOR, "span.spec-value").text.strip()
                    
                    if "Année" in label:
                        details['date_mise_circulation'] = value
                    elif "Kilométrage" in label:
                        details['kilometrage'] = int(value.replace('KM', '').replace(' ', '').strip())
                    elif "Carburant" in label:
                        details['carburant'] = value
                    elif "Boîte de vitesses" in label:
                        details['transmission'] = value
                    elif "Places" in label:
                        details['places'] = value
                    elif "Carrosserie" in label:
                        details['carrosserie'] = value
                    elif "Nombre de clés" in label:
                        details['nb_cles'] = value
                    elif "Couleur extérieure" in label:
                        details['couleur_ext'] = value
                    elif "Couleur intérieure" in label:
                        details['couleur_int'] = value
                    elif "Nombre de propriétaires" in label:
                        details['nb_proprietaires'] = value
                    elif "État" in label:
                        details['condition'] = value
                except:
                    continue
        except Exception as e:
            print(f"Erreur spécifications: {str(e)[:50]}")

        # Section Équipements
        try:
            features = driver.find_elements(By.CSS_SELECTOR, "div.features-container div.feature-item")
            details['equipements'] = [f.text.strip() for f in features if f.text.strip()]
        except Exception as e:
            print(f"Erreur équipements: {str(e)[:50]}")

    except Exception as e:
        print(f"Erreur globale: {str(e)[:50]}...")

    return [
        details['date_mise_circulation'],
        details['kilometrage'],
        details['carburant'],
        details['transmission'],
        details['places'],
        details['carrosserie'],
        details['nb_cles'],
        details['couleur_ext'],
        details['couleur_int'],
        details['nb_proprietaires'],
        details['condition'],
        " | ".join(details['equipements']),
        details['prix']
    ]

def process_csv(input_csv, output_csv):
    """Lit le CSV principal et scrape les détails supplémentaires pour chaque annonce"""
    driver = init_auto24_driver()
    
    # Lire les URLs depuis le CSV
    with open(input_csv, "r", encoding="utf-8") as file:
        reader = csv.reader(file, delimiter=';')
        headers = next(reader)
        listings = [row for row in reader]

    # Nouveaux en-têtes pour Auto24
    new_headers = [
        "ID", "Titre", "Prix (DH)", "Transmission", "Type de carburant", 
        "Vendeur", "URL", "Date mise circulation", "Kilométrage", 
        "Places", "Carrosserie", "Nombre de clés", "Couleur extérieure",
        "Couleur intérieure", "Nombre propriétaires", "Condition", 
        "Équipements", "Prix détaillé"
    ]

    detailed_data = [new_headers]

    for idx, row in enumerate(listings, start=1):
        try:
            if len(row) < 8:
                print(f"❌ Ligne {idx} invalide: {row}")
                continue
                
            url = row[7]  # Correction: URL à l'index 7
            print(f"🔎 Traitement annonce {idx}/{len(listings)} : {url}")
            
            details = scrape_car_details(driver, url)
            
            # Combiner données originales + détails
            combined_data = row + details  # Conserver toutes les colonnes originales
            detailed_data.append(combined_data)
            
            # Pause anti-bot
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Erreur avec l'annonce {idx} : {str(e)[:50]}...")
            continue

    driver.quit()

    # Sauvegarder les résultats
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter=';')
        writer.writerows(detailed_data)

    print(f"✅ Données enrichies sauvegardées dans {output_csv}")

if __name__ == "__main__":
    process_csv("data/auto24_listings.csv", "data/auto24_details.csv")