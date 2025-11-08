import requests
import logging
from typing import List, Dict, Optional, Tuple
from models import db, Province, Regency
from datetime import datetime

# BPS API configuration
BPS_BASE_URL = "https://sig.bps.go.id/rest-bridging"

class ProvincesRegenciesScraper:
    def __init__(self):
        self.session = requests.Session()
        # Set a timeout for requests
        self.session.timeout = 30

    def get_provinces_data(self) -> List[Dict]:
        """
        Fetch all provinces data from BPS API
        Returns list of provinces with their codes and names
        """
        try:
            # Using correct BPS API endpoint for provinces
            url = f"{BPS_BASE_URL}/getwilayah?level=provinsi&parent=0"

            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()

            provinces = []
            for province in data:
                provinces.append({
                    "id": province.get("kode_bps"),
                    "name": province.get("nama_bps", "").strip()
                })

            return provinces

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching provinces data: {str(e)}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in get_provinces_data: {str(e)}")
            return []

    def get_regencies_data(self, province_id: str) -> List[Dict]:
        """
        Fetch regencies data for a specific province from BPS API
        Args:
            province_id: Province code (2 digits)
        Returns list of regencies with their codes and names
        """
        try:
            # Using correct BPS API endpoint for regencies
            url = f"{BPS_BASE_URL}/getwilayah?level=kabupaten&parent={province_id}"

            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()

            regencies = []
            for regency in data:
                regencies.append({
                    "id": regency.get("kode_bps"),
                    "name": regency.get("nama_bps", "").strip(),
                    "province_id": province_id
                })

            return regencies

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching regencies data for province {province_id}: {str(e)}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in get_regencies_data: {str(e)}")
            return []

    def get_all_provinces_with_regencies(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Fetch all provinces and their regencies data
        Returns tuple of (provinces_list, regencies_list)
        """
        logging.info("Starting to fetch provinces and regencies data...")

        # Get all provinces
        provinces = self.get_provinces_data()

        if not provinces:
            logging.error("Failed to fetch provinces data")
            return [], []

        logging.info(f"Found {len(provinces)} provinces")

        all_regencies = []

        # Get regencies for each province
        for province in provinces:
            province_id = province["id"]
            logging.info(f"Fetching regencies for province: {province['name']} ({province_id})")

            regencies = self.get_regencies_data(province_id)

            if regencies:
                all_regencies.extend(regencies)
                logging.info(f"Found {len(regencies)} regencies for province {province['name']}")
            else:
                logging.warning(f"No regencies found for province {province['name']}")

        logging.info(f"Total provinces: {len(provinces)}, Total regencies: {len(all_regencies)}")
        return provinces, all_regencies

    def validate_data(self, provinces: List[Dict], regencies: List[Dict]) -> bool:
        """
        Validate the fetched data
        Returns True if data is valid, False otherwise
        """
        if not provinces:
            logging.error("No provinces data found")
            return False

        if not regencies:
            logging.error("No regencies data found")
            return False

        # Check for required fields
        for province in provinces:
            if not province.get("id") or not province.get("name"):
                logging.error(f"Invalid province data: {province}")
                return False

        for regency in regencies:
            if not regency.get("id") or not regency.get("name") or not regency.get("province_id"):
                logging.error(f"Invalid regency data: {regency}")
                return False

        # Check if all regencies have corresponding provinces
        province_ids = {p["id"] for p in provinces}
        for regency in regencies:
            if regency["province_id"] not in province_ids:
                logging.error(f"Regency {regency['id']} has invalid province_id: {regency['province_id']}")
                return False

        logging.info("Data validation passed")
        return True

    def save_to_database(self, provinces: List[Dict], regencies: List[Dict]) -> bool:
        """Save provinces and regencies data to database"""
        try:
            logging.info("Starting to save provinces and regencies to database...")

            # Clear existing data
            db.session.query(Regency).delete()
            db.session.query(Province).delete()
            db.session.commit()

            # Save provinces
            for province_data in provinces:
                province = Province(
                    id=province_data["id"],
                    name=province_data["name"],
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.session.add(province)

            # Save regencies
            for regency_data in regencies:
                regency = Regency(
                    id=regency_data["id"],
                    name=regency_data["name"],
                    province_id=regency_data["province_id"],
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.session.add(regency)

            db.session.commit()
            logging.info(f"Successfully saved {len(provinces)} provinces and {len(regencies)} regencies to database")
            return True

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error saving data to database: {str(e)}")
            return False


def clean_regency_name(name: str) -> str:
    """Clean regency name by removing extra spaces and standardizing format"""
    if not name:
        return ""

    # Remove extra spaces
    name = name.strip()
    name = name.replace("  ", " ")

    # Remove common prefixes that might be redundant
    prefixes_to_remove = ["Kabupaten ", "Kota ", "Kota Administrasi "]
    for prefix in prefixes_to_remove:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break

    return name

def clean_province_name(name: str) -> str:
    """Clean province name by removing extra spaces and standardizing format"""
    if not name:
        return ""

    # Remove extra spaces
    name = name.strip()
    name = name.replace("  ", " ")

    return name

def get_latest_provinces_regencies_data() -> Tuple[List[Dict], List[Dict]]:
    """
    Main function to get the latest provinces and regencies data
    Returns tuple of (provinces_list, regencies_list)
    """
    scraper = ProvincesRegenciesScraper()

    # Fetch data
    provinces, regencies = scraper.get_all_provinces_with_regencies()

    if not scraper.validate_data(provinces, regencies):
        logging.error("Data validation failed")
        return [], []

    # Clean the data
    for province in provinces:
        province["name"] = clean_province_name(province["name"])

    for regency in regencies:
        regency["name"] = clean_regency_name(regency["name"])

    # Save to database
    scraper.save_to_database(provinces, regencies)

    return provinces, regencies



def get_provinces_from_db() -> List[Dict]:
    """Get provinces data from database"""
    try:
        provinces = Province.query.all()
        result = []

        for province in provinces:
            province_data = {
                "id": province.id,
                "name": province.name,
                "created_at": province.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": province.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            }
            result.append(province_data)

        return result

    except Exception as e:
        logging.error(f"Error fetching provinces from database: {str(e)}")
        return []



def get_regencies_from_db(province_id: str = None) -> List[Dict]:
    """Get regencies data from database"""
    try:
        query = Regency.query
        
        if province_id:
            query = query.filter_by(province_id=province_id)
        
        regencies = query.all()
        result = []
        
        for regency in regencies:
            regency_data = {
                "id": regency.id,
                "name": regency.name,
                "province_id": regency.province_id,
                "province_name": regency.province.name if regency.province else None,
                "created_at": regency.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": regency.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            }
            result.append(regency_data)
        
        return result
        
    except Exception as e:
        logging.error(f"Error fetching regencies from database: {str(e)}")
        return []
