import requests
import logging
from typing import List, Dict, Optional, Tuple

# BPS API configuration
BPS_BASE_URL = "https://webapi.bps.go.id/v1/api"

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
            # Using BPS API to get province list
            # This endpoint gets province data for a specific year
            url = f"{BPS_BASE_URL}/list/model/data/lang/ind/domain/0000/var/0000/vervar/01/th/2023/key/020c95b2c238d613941e86cc42d5e6dd"

            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()

            if data.get("status") != "OK":
                logging.error(f"BPS API returned status: {data.get('status')}")
                return []

            provinces = []
            vervar_list = data.get("vervar", [])

            # Extract province information
            for province in vervar_list:
                if len(province.get("val", "")) == 2:  # Province codes are 2 digits
                    provinces.append({
                        "id": province.get("val"),
                        "name": province.get("label", "").strip()
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
            # Using BPS API to get regency data for a specific province
            url = f"{BPS_BASE_URL}/list/model/data/lang/ind/domain/0000/var/0000/vervar/{province_id}0/th/2023/key/020c95b2c238d613941e86cc42d5e6dd"

            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()

            if data.get("status") != "OK":
                logging.error(f"BPS API returned status: {data.get('status')}")
                return []

            regencies = []
            vervar_list = data.get("vervar", [])

            # Extract regency information
            for regency in vervar_list:
                regency_code = regency.get("val", "")
                # Regency codes are 4 digits (province code + 2 digits)
                if len(regency_code) == 4 and regency_code.startswith(province_id):
                    regencies.append({
                        "id": regency_code,
                        "name": regency.get("label", "").strip(),
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

# Utility functions for data processing
def clean_province_name(name: str) -> str:
    """Clean province name by removing extra spaces and standardizing format"""
    if not name:
        return ""

    # Remove extra spaces and standardize common abbreviations
    name = name.strip()
    name = name.replace("  ", " ")

    # Standardize some common province names
    name = name.replace("Daerah Istimewa", "DI")
    name = name.replace("Daerah Khusus Ibukota", "DKI")

    return name

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

    return provinces, regencies
