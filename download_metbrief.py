import os
import requests
from requests.auth import HTTPBasicAuth
import shutil
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
import datetime
from user_details_jk import *
from urllib.parse import urlparse


USER_AGENT = {'User-agent': 'Mozilla/5.0'}
LOC_COMP = 'tabor_24'

detail_comp = {'tabor_24': {'temp_loc_all': ['11520', '10771'],
                            'locations_sat': ['mitteleuropa', 'tschechische-republik'],
                            'loc_topmeteo': 'cz',
                            'locations_rad': ['tschechische-republik']}}


def main():

    # Copy template to daily directory and clean-up if needed
    today = datetime.date.today().strftime('%m%d')
    os.chdir(f'briefings/{LOC_COMP}')
    if not os.path.isdir(today):
        shutil.copytree(f'template_{LOC_COMP}', today)
        shutil.rmtree(f'{today}/charts')
        os.mkdir(f'{today}/charts')

    # Rename presentation
    os.chdir(f'{today}')
    pres_template_string = f'template_{LOC_COMP}.odp'
    pres_today_string = pres_template_string.replace('template', today)
    if os.path.exists(pres_template_string):
        os.rename(pres_template_string, pres_today_string)
    os.chdir('charts')

    # Download DWD charts
    if not os.path.isdir('gwl'):
        os.mkdir('gwl')
    for chart in ['bwk_bodendruck_na_ana', 'ico_500ht_na_ana']:
        file_url = f'https://www.dwd.de/DWD/wetter/wv_spez/hobbymet/wetterkarten/{chart}.png'
        request_download(file_url, opath='gwl/')

    # Download wetter3
    request_download('https://wetter3.de/Animation_00_UTC/12_10.gif', opath='gwl/')

    # Download flugwetter.de, change station identifiers in loop if needed
    if not os.path.isdir('sounding'):
        os.mkdir('sounding')
    for temp_loc in detail_comp[LOC_COMP]['temp_loc_all']:
        file_url = f'https://flugwetter.de/fw/scripts/getchart.php?src=nb_obs_tmp_{temp_loc}_lv_999999_p_000_0000.png'
        request_download(file_url, opath='sounding/', user=USERNAME_DWD, passwd=PASSWORD_DWD)

    # Get cookies for session to download images from kachelmannwetter.com
    options = Options()
    options.add_argument("--headless=new") # Run in headless mode (no GUI)
    driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
    driver.get('https://kachelmannwetter.com/')
    cookies = driver.get_cookies()
    driver.close()

    # Set cookie that has previously been fetched
    s = requests.Session()
    for cookie in cookies:
        s.cookies.set(cookie['name'], cookie['value'])

    # Download kachelmannwetter.com satellite images
    for loc in detail_comp[LOC_COMP]['locations_sat']:
        url = f'https://kachelmannwetter.com/de/sat/{loc}/satellit-hd-5min.html'
        download_kachelmann(s, url, loc, 'sat')

    # Download kachelmannwetter.com radar images
    for loc in detail_comp[LOC_COMP]['locations_rad']:
        url = f'https://kachelmannwetter.com/de/regenradar/{loc}'
        download_kachelmann(s, url, loc, 'radar')

    # Set variables that should be downloaded from topmeteo
    var_topmeteo = {'pfd': 28, 'thermik': 24, 'wolken': 26, 'wind_1500': 39}
    # Set date
    today = datetime.datetime.now()
    today = today.replace(hour=0, minute=0, second=0, microsecond=0)
    # Topmeteo chart download
    download_topmeteo(var_topmeteo, loc=detail_comp[LOC_COMP]['loc_topmeteo'],
                        day=0, today=today, user=USERNAME_TOPMETEO, passwd=PASSWORD_TOPMETEO)

    # Verify if command-line LibreOffice is available
    os.chdir('..')
    if shutil.which('soffice'):
        # Convert presentation to PDF
        os.system(f'soffice --headless --convert-to pdf {pres_today_string}')


def download_topmeteo(var_dict, loc='de', day=0, today=None, user=None, passwd=None):
    """
    Downloads weather charts from TopMeteo by automating login and fetching images.

    Parameters:
    - var_dict (dict): Dictionary of variables to download (e.g., {"pfd": "param1", "clouds": "param2"}).
    - loc (str, optional): Location code (default: 'de').
    - day (int, optional): Forecast day (0 = today, 1 = tomorrow, etc.).
    - today (datetime, optional): Reference datetime object for time calculation.

    Notes:
    - Creates a 'topmeteo' directory if it doesn't exist.
    - Logs in using Selenium and saves cookies for authentication.
    - Downloads images for specified weather parameters.
    """

    # Ensure 'topmeteo' directory exists
    os.makedirs("topmeteo", exist_ok=True)

    if not user or not passwd:
        print("Error: TopMeteo credentials not set in environment variables.")
        return

    # Configure Selenium WebDriver
    options = Options()
    options.add_argument("--headless=new") # Run in headless mode (no GUI)
    driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)

    try:
        # Open login page
        driver.get("https://vfr.topmeteo.eu/de/")

        # Wait until the username field is present
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "username")))

        # Enter credentials and login
        driver.find_element(By.NAME, "username").send_keys(user)
        driver.find_element(By.NAME, "password").send_keys(passwd)
        driver.find_element(By.NAME, "password").send_keys(Keys.ENTER)

        # Wait for login to complete
        WebDriverWait(driver, 10).until(EC.url_contains("vfr.topmeteo.eu"))

        # Get cookies after login
        cookies = driver.get_cookies()

        # Start a session and set cookies
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie["name"], cookie["value"])

        # Download images
        for key, var in var_dict.items():
            time_steps = [0] if key == "pfd" else range(8, 17)

            var_path = f"topmeteo/{key}"
            os.makedirs(var_path, exist_ok=True)

            for time_data in time_steps:
                filename = f"{key}_{day}_{time_data}.png"
                file_path = os.path.join(var_path, filename)

                # Skip if file already exists
                if os.path.isfile(file_path):
                    continue

                # Construct the timestamp
                if today is None:
                    today = datetime.utcnow()
                time_step = today.replace(hour=time_data).strftime("%Y-%m-%dT%H:%M:%SZ")

                # Construct the download URL
                download_url = f"https://vfr.topmeteo.eu/de/{loc}/map/{var}/{day}/{time_data}/image?{time_step}"

                try:
                    # Request image
                    response = session.get(download_url, headers=USER_AGENT, stream=True)
                    response.raise_for_status()  # Raise an error if request failed

                    # Save the image
                    with open(file_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                except requests.exceptions.RequestException as e:
                    print(f"Error downloading {filename}: {e}")

    except Exception as e:
        print(f"Error during Selenium login: {e}")

    finally:
        # Close the Selenium driver
        driver.quit()

def download_kachelmann(session, url_in, loc_in, type_data):
    """
    Downloads the latest satellite or radar image from Kachelmannwetter.

    Parameters:
    - session (requests.Session): An active session to reuse cookies and headers.
    - url_in (str): The webpage URL containing the image.
    - loc_in (str): Location identifier for the saved file.
    - type_data (str): Type of data to download ('sat' or 'radar').

    Returns:
    - str: The filename of the downloaded image if successful, None otherwise.

    Notes:
    - Saves the downloaded image in the `type_data` folder.
    - Creates a symbolic link for easy access to the latest image.
    """

    # Ensure output directory exists
    os.makedirs(type_data, exist_ok=True)

    try:
        # Fetch webpage content using the provided session
        response = session.get(url_in, headers=USER_AGENT)
        response.raise_for_status()

        # Parse HTML to find the image URL
        soup = BeautifulSoup(response.text, "lxml")
        meta_tag = soup.find('meta', property='og:image')

        if not meta_tag or 'content' not in meta_tag.attrs:
            print("Error: Image URL not found in meta tag.")
            return None

        download_url = meta_tag['content']
        filename = os.path.join(type_data, os.path.basename(download_url))

        # Download image if it doesn't exist
        if not os.path.isfile(filename):
            img_response = session.get(download_url, headers=USER_AGENT, stream=True)
            img_response.raise_for_status()  # Ensure we got a successful response

            with open(filename, 'wb') as file:
                for chunk in img_response.iter_content(8192):
                    file.write(chunk)

        # Create a symbolic link to the latest image
        link_filename = os.path.join(type_data, f"{type_data}_{loc_in}_latest.png")

        if os.path.isfile(link_filename):
            os.remove(link_filename)

        if type_data in ['sat', 'radar']:
            shutil.copyfile(filename, link_filename)

        return filename

    except requests.exceptions.RequestException as e:
        print(f"Error during download: {e}")
        return None


def request_download(url_in, opath='', user=None, passwd=None):
    """
    Downloads a file using Python's requests module with optional authentication.

    Parameters:
    - url_in (str): The URL of the file to be downloaded.
    - opath (str, optional): Output directory where the file will be saved (default: current directory).
    - user (str, optional): Username for authentication (default: None).
    - passwd (str, optional): Password for authentication (default: None).

    Returns:
    - str: The full path of the downloaded file if successful, None otherwise.

    Notes:
    - If the filename cannot be determined from the URL, it defaults to "downloaded_file".
    - Uses "Mozilla/5.0" as the user-agent to mimic a web browser.
    - Ensures proper file handling using a context manager.
    """
    # Extract filename safely
    parsed_url = urlparse(url_in)
    filename = os.path.basename(parsed_url.path) or "downloaded_file"

    # Ensure output directory exists
    if opath and not os.path.exists(opath):
        os.makedirs(opath)

    file_path = os.path.join(opath, filename)

    # Check if file already exists
    if os.path.isfile(file_path):
        return file_path

    # Start session and download file
    session = requests.Session()
    auth = HTTPBasicAuth(user, passwd) if user and passwd else None

    try:
        response = session.get(url_in, headers=USER_AGENT, auth=auth, stream=True)
        response.raise_for_status()  # Raise an error for HTTP issues

        # Write content to file
        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        return file_path

    except requests.exceptions.RequestException as e:
        print(f"Error during download: {e}")
        return None


if __name__ == "__main__":
    main()
