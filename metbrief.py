import os
import requests
from requests.auth import HTTPBasicAuth
import shutil
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import datetime
from user_details import *
from urllib.parse import urlparse
import time


LOC_COMP = 'prievidza_25'

detail_comp = {'prievidza_25':
                    {'sounding_dict': {'11952': '961', '12575': '961', '11747': '961', '12843': '961'},
                     'locations_sat': ['mitteleuropa', 'slowakei'],
                     'loc_topmeteo': 'cz',
                     'locations_rad': ['slowakei'],
                     'model_info':
                         {'model_list': ['deu-hd', 'euro', 'swisshd-nowcast'],
                          'var_model_list':
                              ['bewoelkungsgrad', 'bedeckungsgrad-low-clouds', 'bedeckungsgrad-mid-clouds'],
                          'loc_model': 'slowakei', 'init_hour': '00',
                          'today_model': datetime.date.today().strftime('%Y%m%d'),
                          'hour_model_list': [str(i).zfill(2) for i in range(8, 18, 2)],
                          }},
               }


def main():

    # Check for available browsers
    browser_list = ['Firefox', 'Chrome']
    driver_avail = {}
    for browser in browser_list:
        if browser == 'Chrome':
            driver_avail[browser] = initialize_chrome_driver()
        elif browser == 'Firefox':
            driver_avail[browser] = initialize_firefox_driver()

    if len(driver_avail) == 0:
        raise Exception(f'Installed browsers not in {browser_list}')

    nd = 0
    driver, cookies = None, None

    for key, driver in driver_avail.items():
        # Try to get cookies for session
        driver.get('https://kachelmannwetter.com/')
        cookies = driver.get_cookies()

        if len(cookies) == 0:
            print(f'Cookies not found for {key}')
            nd += 1
            if nd == len(driver_avail):
                raise Exception(f'Cookie download failed for all drivers in: {list(driver_avail.keys())}')
            continue  # Try the next driver
        else:
            print(f'Cookies successfully retrieved using driver: {key}')
            break  # Exit loop if cookies are successfully retrieved

    user_agent = {'User-agent': driver.execute_script("return navigator.userAgent")}

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
        request_download(file_url, user_agent, opath='gwl/')

    # Set cookie that has previously been fetched
    s = requests.Session()
    for cookie in cookies:
        s.cookies.set(cookie['name'], cookie['value'])

    model_info = detail_comp[LOC_COMP]['model_info']
    for model_use in model_info['model_list']:
        for var_model in model_info['var_model_list']:
            for hour_model in model_info['hour_model_list']:
                url = (f'https://kachelmannwetter.com/de/modellkarten/{model_use}/'
                       f'{model_info["today_model"]}{model_info["init_hour"]}/{model_info["loc_model"]}/'
                       f'{var_model}/{model_info["today_model"]}-{hour_model}00z.html')
                download_kachelmann(s, url, user_agent, type_data='model', loc_in=None,
                                    model=model_use, model_var=var_model)

    # Download kachelmannwetter.com soundings images
    today_sounding = datetime.date.today().strftime('%Y%m%d')
    for station, area_id_sounding in detail_comp[LOC_COMP]['sounding_dict'].items():
        url = (f'https://kachelmannwetter.com/de/ajax/obsdetail?station_id=R{station}&timestamp={today_sounding}0000'
               f'&param_id=1&model=obsradio&area_id={area_id_sounding}&counter=true&lang=DE')
        download_kachelmann(s, url, user_agent, 'sounding')

    # Download kachelmannwetter.com satellite images
    for loc in detail_comp[LOC_COMP]['locations_sat']:
        url = f'https://kachelmannwetter.com/de/sat/{loc}/satellit-satellit-hd-10m-superhd.html'
        download_kachelmann(s, url, user_agent, type_data='sat', loc_in=loc, )

    # Download kachelmannwetter.com radar images
    for loc in detail_comp[LOC_COMP]['locations_rad']:
        url = f'https://kachelmannwetter.com/de/regenradar/{loc}'
        download_kachelmann(s, url, user_agent, type_data='radar', loc_in=loc)

    # Set variables that should be downloaded from topmeteo
    var_topmeteo = {'pfd': 28, 'thermik': 24, 'wolken': 26, 'wind_1500': 39}
    # Set date
    today = datetime.datetime.now()
    today = today.replace(hour=0, minute=0, second=0, microsecond=0)

    # Topmeteo chart download
    download_topmeteo(driver, var_topmeteo, user_agent, loc=detail_comp[LOC_COMP]['loc_topmeteo'],
                      day=0, today=today, user=USERNAME_TOPMETEO, passwd=PASSWORD_TOPMETEO)

    # Download wetter3
    request_download('https://wetter3.de/Animation_00_UTC/12_10.gif', user_agent, opath='gwl/')

    # Verify if command-line LibreOffice is available
    os.chdir('..')
    if shutil.which('soffice'):
        # Convert presentation to PDF
        os.system(f'soffice --headless --convert-to pdf {pres_today_string}')

    # Clean up
    for key, item in driver_avail.items():
        driver_avail[key].close()


# Initialize Chrome driver with specific options (https://github.com/SeleniumHQ/selenium/issues/13095 means
# there is a bug in ChromeDriver that prevents it from running in detached mode)
def initialize_chrome_driver():
    from selenium.webdriver.chrome.service import Service as ChromeService
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.options import Options
    driver = None
    try:
        options_chrome = Options()
        options_chrome.add_argument("--headless")
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options_chrome)
    finally:
        return driver


def initialize_firefox_driver():
    from selenium.webdriver.firefox.service import Service as FirefoxService
    from webdriver_manager.firefox import GeckoDriverManager
    from selenium.webdriver.firefox.options import Options
    driver = None
    try:
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
    finally:
        return driver


def download_topmeteo(driver, var_dict, user_agent, loc='de', day=0, today=None, user=None, passwd=None):
    """
    Downloads weather charts from TopMeteo by automating login and fetching images.

    Parameters:
    - var_dict (dict): Dictionary of variables to download (e.g., {"pfd": "param1", "clouds": "param2"}).
    - loc (str, optional): Location code (default: 'de').
    - day (int, optional): Forecast day (0 = today, 1 = tomorrow, etc.).
    - today (datetime, optional): Reference datetime object for time calculation.
    - user (str, optional): Username for authentication (default: None).
    - passwd (str, optional): Password for authentication (default: None).

    Notes:
    - Creates a 'topmeteo' directory if it doesn't exist.
    - Logs in using Selenium and saves cookies for authentication.
    - Downloads images for specified weather parameters.
    """

    # Create topmeteo directory in charts
    if not os.path.isdir('topmeteo'):
        os.mkdir('topmeteo')

    # Login
    driver.get('https://vfr.topmeteo.eu/de/')
    driver.find_element(By.NAME, "username").send_keys(user)
    driver.find_element(By.NAME, "password").send_keys(passwd)
    driver.find_element(By.NAME, "password").send_keys(Keys.ENTER)
    time.sleep(3)

    for key, var in var_dict.items():
        if key == 'pfd':
            time_steps = [0]
        else:
            time_steps = range(8, 17)

        var_path = f'topmeteo/{key}'
        if not os.path.isdir(var_path):
            os.mkdir(var_path)

        for time_data in time_steps:
            filename = f'{key}_{day}_{time_data}.png'
            if os.path.isfile(f'{var_path}/{filename}'):
                continue
            else:
                time_step = today.replace(hour=time_data).strftime("%Y-%m-%dT%H:%M:%SZ")
                download_url = f'https://vfr.topmeteo.eu/de/{loc}/map/{var}/{day}/{time_data}/image?{time_step}'
                driver.get(download_url)
                cookies = driver.get_cookies()
                s = requests.Session()
                for cookie in cookies:
                    s.cookies.set(cookie['name'], cookie['value'])
                open(f'{var_path}/{filename}', 'wb').write((s.get(download_url, headers=user_agent)).content)


def download_kachelmann(session, url_in, user_agent, type_data=None, loc_in=None, model=None, model_var=None):
    """
    Downloads the latest satellite, radar, model, or sounding images from Kachelmannwetter.

    Parameters:
    - session (requests.Session): Active session with shared cookies and headers.
    - url_in (str): The URL of the webpage containing the image.
    - user_agent (dict): Headers to use in HTTP requests, e.g., {'User-Agent': '...'}.
    - type_data (str): Type of data ('sat', 'radar', 'model', 'sounding').
    - loc_in (str): Location identifier
    - model (str, optional): Model name for structured output (used with 'model' type).
    - model_var (str, optional): Model variable for structured output (used with 'model' type).

    Returns:
    - str: The full path of the downloaded image file, or None if download failed.
    """

    # Ensure output directory exists
    if model:
        opath = os.path.join(type_data, model, model_var)
    else:
        opath = type_data
    os.makedirs(opath, exist_ok=True)

    try:
        # Fetch webpage content using the provided session
        response = session.get(url_in, headers=user_agent)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        # Parse HTML to find the image URL
        download_url, filename = None, None

        if type_data in ['sat', 'radar', 'model']:
            meta_tag = soup.find('meta', property='og:image')
            if not meta_tag or 'content' not in meta_tag.attrs:
                print("Error: Image URL not found in meta tag.")
                return None
            download_url = meta_tag['content']
            if type_data == 'model':
                filename_split = os.path.basename(download_url).split('_')
                filename_split.pop(3)
                filename = os.path.join(opath, '_'.join(filename_split))
            else:
                filename = os.path.join(opath, os.path.basename(download_url))

        elif type_data == 'sounding':
            for img in soup.find_all('img'):
                for attr in ['data-src']:
                    url = img.get(attr)
                    if url and url.lower().endswith('.png'):
                        download_url = url
                    else:
                        print("Error: Image URL not found")
                        return None

            # Split on underscores and remove the last part before .png and rejoin all except the last part before .png
            filename_split = os.path.basename(download_url).split('_')
            filename = os.path.join(opath, '_'.join(filename_split[:-2]) + '.png')

        # Download image if it doesn't exist
        if not os.path.isfile(filename):
            img_response = session.get(download_url, headers=user_agent, stream=True)
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


def request_download(url_in, user_agent, opath='', user=None, passwd=None):
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

    if 'flugwetter' not in url_in:
        filename = os.path.basename(parsed_url.path) or "downloaded_file"
    else:
        filename = url_in.split('=')[-1]

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
        response = session.get(url_in, headers=user_agent, auth=auth, stream=True)
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
