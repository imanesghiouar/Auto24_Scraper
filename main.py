# main.py
import os
import re
import csv
import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from tenacity import retry, stop_after_attempt, wait_fixed

def main():
    """Fonction principale pour exécuter le scraper complet."""
    print("🚗 Démarrage du scraper Auto24.ma...")
    
    # Étape 1 : Scraping des annonces de base
    print("\n📋 ÉTAPE 1 : Scraping des annonces principales...")
    try:
        basic_data = scrape_auto24(max_scrolls=5)
    except Exception as e:
        print(f"❌ Erreur critique lors du scraping : {str(e)[:100]}")
        return

    if not basic_data or len(basic_data) == 0:
        print("❌ Aucune donnée trouvée. Arrêt du programme.")
        return
    
    # Étape 2 : Sauvegarde des annonces de base
    basic_csv = save_to_csv(basic_data, "auto24_listings.csv")
    
    # Étape 3 : Scraping détaillé avec images
    print("\n🔍 ÉTAPE 2 : Scraping détaillé et téléchargement des images...")
    detailed_csv = os.path.join("data", "auto24_details.csv")
    process_csv(basic_csv, detailed_csv)
    
    print("\n✅ SCRAPING TERMINÉ AVEC SUCCÈS !")
    print(f"Annonces de base : {basic_csv}")
    print(f"Détails complets : {detailed_csv}")
    print(f"Images téléchargées : data/images/[dossiers_annonces]")

def init_auto24_driver(headless=True):
    """Initialise le driver Chrome avec les options personnalisées"""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def create_folder_name(title, idx):
    """Crée un nom de dossier valide pour stocker les images d'une annonce."""
    folder_name = re.sub(r'[^\w\s-]', '', title)
    folder_name = re.sub(r'\s+', '_', folder_name)[:50]
    return f"{idx}_{folder_name}"

def extract_feature(features, index, is_mileage=False):
    """Extrait une caractéristique spécifique"""
    try:
        if len(features) > index:
            text = features[index].text.strip()
            return text.split('\n')[-1].replace('RW', '').strip() if is_mileage else text.split('\n')[-1].strip()
        return "N/A"
    except:
        return "N/A"

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def extract_text_safe(parent, selector):
    """Extrait le texte d'un élément en toute sécurité"""
    try:
        element = WebDriverWait(parent, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
        return element.text.strip()
    except:
        return "N/A"

def scrape_auto24(max_scrolls=5):
    """Scrape les annonces de voitures sur Auto24.ma avec chargement infini"""
    driver = init_auto24_driver()
    data = []
    listing_id_counter = 1

    try:
        driver.get("https://auto24.ma/buy-cars")
        
        # Logique de scroll améliorée
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        
        while scroll_attempts < max_scrolls:
            driver.execute_script("window.scrollBy(0, window.innerHeight * 0.8)")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_attempts += 1

        listings = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.card-holder"))
        )
        
        print(f"✅ {len(listings)} annonces trouvées au total")

        for listing in listings:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'auto'});", listing)
                time.sleep(0.5)

                title = extract_text_safe(listing, "span.card-model")
                price = extract_text_safe(listing, "span.card-price")
                
                features = listing.find_elements(By.CSS_SELECTOR, "div.card-features > span.features-container")
                transmission = extract_feature(features, 0)
                fuel_type = extract_feature(features, 1)
                mileage = extract_feature(features, 2, True)
                
                seller_type = "Professionnel" if listing.find_elements(By.CSS_SELECTOR, "div.card-brand-logo") else "Particulier"
                
                try:
                    link_element = listing.find_element(By.CSS_SELECTOR, "a.card-link")
                    link = link_element.get_attribute("href")
                    vehicle_id = link.split("/")[-1]
                except Exception as e:
                    link = "N/A"

                folder_name = create_folder_name(title, listing_id_counter)
                
                data.append([
                    listing_id_counter,
                    title,
                    _clean_price(price),
                    transmission,
                    fuel_type,
                    mileage,
                    seller_type,
                    link,
                    folder_name
                ])
                
                listing_id_counter += 1
                print(f"✔ Annonce {listing_id_counter - 1} traitée")

            except Exception as e:
                print(f"⚠️ Erreur annonce {listing_id_counter}: {str(e)[:50]}...")
                continue

    except Exception as e:
        print(f"❌ Erreur critique : {str(e)[:50]}...")
    finally:
        driver.quit()
    
    return data

def _clean_price(price_str):
    """Nettoyage du prix"""
    try:
        return int(price_str.replace('DH', '').replace(' ', '').replace('\u202f', '').strip())
    except:
        return 0

def save_to_csv(data, filename):
    """Sauvegarde les données dans un fichier CSV."""
    output_folder = "data"
    os.makedirs(output_folder, exist_ok=True)
    output_file = os.path.join(output_folder, filename)

    with open(output_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter=';')
        writer.writerow([
            "ID", "Titre", "Prix", "Transmission", "Type de carburant", 
            "Kilométrage", "Créateur", "URL de l'annonce", "Dossier d'images"
        ])
        writer.writerows(data)

    print(f"✅ Données sauvegardées dans {output_file}")
    return output_file

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def download_image(driver, image_element, folder_path, image_name):
    """Télécharge une image depuis Auto24.ma avec la nouvelle structure"""
    try:
        # Faire défiler jusqu'à l'image pour activer le chargement
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", image_element)
        time.sleep(0.5)
        
        WebDriverWait(driver, 10).until(EC.visibility_of(image_element))
        image_url = image_element.get_attribute('src')
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': driver.current_url
        }

        response = requests.get(image_url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()
        
        # Détection de l'extension
        content_type = response.headers.get('Content-Type', '')
        extension = '.webp'
        if 'jpeg' in content_type:
            extension = '.jpg'
        elif 'png' in content_type:
            extension = '.png'
        
        image_path = os.path.join(folder_path, f"{image_name}{extension}")
        
        with open(image_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return os.path.basename(image_path)
        
    except Exception as e:
        print(f"❌ Erreur image {image_name} : {str(e)[:80]}")
        return None

def scrape_car_details(driver, url, folder_name):
    """Scrape les détails complets avec la nouvelle structure d'images"""
    if not url or url == "N/A":
        return ["N/A"] * 13
    
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.ant-col.content-container")))

    except:
        print(f"⚠️ Impossible de charger la page {url}")
        return ["N/A"] * 13

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
        # Téléchargement des images
        images_base_folder = os.path.join("data", "images")
        listing_folder = os.path.join(images_base_folder, folder_name)
        os.makedirs(listing_folder, exist_ok=True)
        
        try:
            # Nouveau sélecteur d'images
            images = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.carousel-image img")))

            for idx, img in enumerate(images[:10], 1):
                if img.get_attribute('src'):
                    download_image(driver, img, listing_folder, f"image_{idx}")
        except Exception as e:
            print(f"⚠️ Erreur téléchargement images: {str(e)[:50]}")

        # Extraction des détails
        try:
            details['prix'] = extract_text_safe(driver, "span.card-price")
        except:
            pass

        specs = driver.find_elements(By.CSS_SELECTOR, "div.specs-container div.spec-item")
        for spec in specs:
            try:
                label = extract_text_safe(spec, "span.spec-label")
                value = extract_text_safe(spec, "span.spec-value")
                
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
            except:
                continue

        try:
            features = driver.find_elements(By.CSS_SELECTOR, "div.features-container div.feature-item")
            details['equipements'] = [f.text.strip() for f in features if f.text.strip()]
        except:
            pass

    except Exception as e:
        print(f"Erreur lors du scraping de {url} : {str(e)[:50]}...")

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
        ", ".join(details['equipements']),
        details['prix']
    ]

def process_csv(input_csv, output_csv):
    """Lit le CSV principal et scrape les détails supplémentaires pour chaque annonce"""
    driver = init_auto24_driver()
    
    with open(input_csv, "r", encoding="utf-8") as file:
        reader = csv.reader(file, delimiter=';')
        headers = next(reader)
        listings = [row for row in reader]

    new_headers = [
        "ID", "Titre", "Prix", "Transmission", "Type de carburant", "Créateur", "URL de l'annonce",
        "Date mise circulation", "Kilométrage", "Places", "Carrosserie", "Nombre de clés",
        "Couleur extérieure", "Couleur intérieure", "Nombre propriétaires", "Condition", 
        "Équipements", "Prix Détaillé"
    ]

    detailed_data = [new_headers]

    for idx, row in enumerate(listings, start=1):
        try:
            url = row[7]
            folder_name = row[8]
            
            print(f"🔎 Traitement annonce {idx}/{len(listings)} : {url}")
            details = scrape_car_details(driver, url, folder_name)
            
            combined_data = row[:7] + details
            detailed_data.append(combined_data)
            
        except Exception as e:
            print(f"❌ Erreur avec l'annonce {idx} : {str(e)[:50]}...")
            continue

    driver.quit()

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter=';')
        writer.writerows(detailed_data)

    print(f"✅ Données enrichies sauvegardées dans {output_csv}")

if __name__ == "__main__":
    main()
