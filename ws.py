import requests
from bs4 import BeautifulSoup
import csv
import re
import time
import urllib3
import logging
from datetime import datetime

def setup_logging():
    """
    Set up logging configuration
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def extract_car_details(car_div):
    """
    Extract details from a single car listing div with enhanced error handling
    """
    try:
        # Car Name (Full Name)
        car_name = car_div.find('h3', class_='lib-car')
        car_name = car_name.text.strip() if car_name else 'N/A'
        
        # Split car name into brand and model
        name_parts = car_name.split(' ', 1)
        brand = name_parts[0]
        model = name_parts[1] if len(name_parts) > 1 else 'N/A'
        
        # Price
        price_elem = car_div.find('div', class_='price')
        price = price_elem.text.strip().replace(' ', '').replace('DT', '') if price_elem else 'N/A'
        
        # Options extraction
        options = car_div.find_all('div', class_='options')
        if not options:
            return None
        
        option_divs = options[0].find_all('div')
        if len(option_divs) < 4:
            return None
        
        # Year
        year = option_divs[0].find('span')
        year = year.text.strip() if year else 'N/A'
        
        # Kilometers
        kilometers = option_divs[1].find('span')
        kilometers = kilometers.text.strip().replace(' Km', '').replace(' ', '') if kilometers else 'N/A'
        
        # Fuel Type
        fuel_type = option_divs[2].find('span')
        fuel_type = fuel_type.text.strip() if fuel_type else 'N/A'
        
        # Transmission
        transmission = option_divs[3].find('span')
        transmission = transmission.text.strip() if transmission else 'N/A'
        
        return {
            'Nom Total': car_name,
            'Marque': brand,
            'Modele': model,
            'Carburant': fuel_type,
            'Boite': transmission,
            'Prix': price,
            'Kilometrage': kilometers,
            'Annee': year
        }
    except Exception as e:
        logging.error(f"Error extracting car details: {e}")
        return None

def clean_and_format_data(cars):
    """
    Clean and standardize car data before saving
    """
    current_year = datetime.now().year
    cleaned_cars = []
    for car in cars:
        if car is None:
            continue
        
        # Clean year and calculate age
        year = re.sub(r'[^\d]', '', car['Annee']) if car['Annee'] != 'N/A' else 'N/A'
        age = 'N/A'
        if year != 'N/A':
            try:
                age = str(current_year - int(year))
            except ValueError:
                age = 'N/A'
        
        cleaned_car = {
            'Nom Total': car['Nom Total'],
            'Marque': car['Marque'],
            'Modele': car['Modele'],
            'Annee': year,
            'Age (Years)': age,
            'Kilometrage (Km)': re.sub(r'[^\d]', '', car['Kilometrage']) if car['Kilometrage'] != 'N/A' else 'N/A',
            'Carburant': car['Carburant'],
            'Boite': car['Boite'],
            'Prix (DT)': re.sub(r'[^\d]', '', car['Prix']) if car['Prix'] != 'N/A' else 'N/A',

        }
        cleaned_cars.append(cleaned_car)
    return cleaned_cars

def scrape_car_listings(base_url, max_pages=5):
    """
    Scrape car listings with pagination and enhanced error handling
    """
    # Disable SSL warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    all_cars = []
    
    for page in range(1, max_pages + 1):
        # Construct the URL for each page
        url = f"{base_url}&page={page}"
        
        try:
            # Send GET request with SSL verification disabled
            response = requests.get(url, verify=False, timeout=10)
            
            # Check if request was successful
            response.raise_for_status()
            
            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all car listing divs
            car_divs = soup.find_all('div', class_='box-product listing-item effect-item h-100')
            
            # Extract details for each car
            for car_div in car_divs:
                car_details = extract_car_details(car_div)
                if car_details:
                    all_cars.append(car_details)
            
            # Log progress
            logging.info(f"Scraped page {page}: {len(car_divs)} cars found")
            
            # Be nice to the server
            time.sleep(1)
        
        except requests.RequestException as e:
            logging.error(f"Error scraping page {page}: {e}")
    
    return all_cars

def save_to_csv(cars, filename='car_listings.csv'):
    """
    Save car listings to a CSV file with improved organization
    """
    if not cars:
        logging.warning("No data to save")
        return
    
    # Clean and standardize data
    cleaned_cars = clean_and_format_data(cars)
    
    # Define the order of the columns explicitly
    fieldnames = [
        'Nom Total', 
        'Marque', 
        'Modele', 
        'Annee', 
        'Age (Years)', 
        'Kilometrage (Km)', 
        'Carburant', 
        'Boite',
        'Prix (DT)' 
    ]
    
    # Write to CSV
    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write headers
            writer.writeheader()
            
            # Write car data
            for car in cleaned_cars:
                writer.writerow(car)
        
        logging.info(f"Data saved to {filename}")
    except IOError as e:
        logging.error(f"Error saving CSV: {e}")

def main():
    # Configure logging
    setup_logging()
    
    # Base URL of the search results page
    base_url = "https://www.sparkauto.tn/search-listing-result?_token=7qsMKlo8lUhwljXZuE3HBEoNTxz09039s95qQ76P&listing_min_model_year=2%E2%80%AF010&listing_max_model_year=2%E2%80%AF023&listing_price_min=28%E2%80%AF000&listing_price_max=460%E2%80%AF000&listing_mileage_min=11%E2%80%AF500&listing_mileage_max=228%E2%80%AF000"
    
    try:
        # Scrape car listings
        car_listings = scrape_car_listings(base_url)
        
        # Save to CSV
        save_to_csv(car_listings)
        
        logging.info(f"Total cars scraped: {len(car_listings)}")
    
    except Exception as e:
        logging.error(f"Unexpected error in main process: {e}")

if __name__ == "__main__":
    main()