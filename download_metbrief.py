import os
import requests
from requests.auth import HTTPBasicAuth
import datetime
import shutil
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from user_details import *

USER_AGENT = {'User-agent': 'Mozilla/5.0'}
LOC_COMP = 'tabor_24'

detail_comp = {'tabor_24': {'temp_loc_all': ['11520', '10771'],
                            'locations_sat': ['mitteleuropa', 'tschechische-republik'],
                            'loc_topmeteo': 'cz',
                            'locations_rad': ['tschechische-republik']}}


def main():

    # Copy template to daily directory and clean-up if needed
    today = datetime.date.today().strftime('%m%d')
    os.chdir(f'{LOC_COMP}')
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

    # Get cookies for session
    driver = webdriver.Firefox()
    driver.get('https://kachelmannwetter.com/')
    cookies = driver.get_cookies()
    driver.close()

    s = requests.Session()
    for cookie in cookies:
        s.cookies.set(cookie['name'], cookie['value'])

    # Satellite
    for loc in detail_comp[LOC_COMP]['locations_sat']:
        url = f'https://kachelmannwetter.com/de/sat/{loc}/satellit-hd-5min.html'
        download_kachelmann(s, url, loc, 'sat')

    # Radar
    for loc in detail_comp[LOC_COMP]['locations_rad']:
        url = f'https://kachelmannwetter.com/de/regenradar/{loc}'
        download_kachelmann(s, url, loc, 'radar')

    # Topmeteo
    var_topmeteo = {'pfd': 28, 'thermik': 24, 'wolken': 26, 'wind_1500': 39}
    today = datetime.datetime.now()
    today = today.replace(hour=0, minute=0, second=0, microsecond=0)
    download_topmeteo(var_topmeteo, loc=detail_comp[LOC_COMP]['loc_topmeteo'], day=0, today=today)

    os.chdir('..')
    os.system(f'soffice --headless --convert-to pdf {pres_today_string}')


def download_topmeteo(var_dict, loc='de', day=0, today=None):

    # Create topmeteo directory in charts
    if not os.path.isdir('topmeteo'):
        os.mkdir('topmeteo')

    # Login
    driver = webdriver.Firefox()
    driver.get('https://vfr.topmeteo.eu/de/')
    driver.find_element(By.NAME, "username").send_keys(USERNAME_TOPMETEO)
    driver.find_element(By.NAME, "password").send_keys(PASSWORD_TOPMETEO)
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
                open(f'{var_path}/{filename}', 'wb').write((s.get(download_url, headers=USER_AGENT)).content)
    driver.close()


def download_kachelmann(session, url_in, loc_in, type_data):
    if not os.path.isdir(type_data):
        os.mkdir(type_data)

    req = requests.get(url_in, headers=USER_AGENT)
    soup = BeautifulSoup(req.text, "lxml")
    download_url = soup.find('meta', property='og:image').attrs['content']
    filename = f'{type_data}/{download_url.split("/")[-1]}'
    if not os.path.isfile(filename):
        open(filename, 'wb').write((session.get(download_url, headers=USER_AGENT)).content)
    link_filename = f'{type_data}/{type_data}_{loc_in}_latest.png'
    if os.path.isfile(link_filename):
        os.remove(link_filename)
    if type_data in ['sat', 'radar']:
        shutil.copyfile(f'{type_data}/{download_url.split("/")[-1]}', link_filename)


def request_download(url_in, opath='', user=None, passwd=None):
    filename = url_in.split('/')[-1]
    s = requests.Session()
    if not os.path.isfile(filename):
        if user and passwd:
            open(f'{opath}{filename}', 'wb').write((s.get(url_in, headers=USER_AGENT,
                                                          auth=HTTPBasicAuth(user, passwd))).content)
        else:
            open(f'{opath}{filename}', 'wb').write((s.get(url_in, headers=USER_AGENT)).content)


def wget_download(url_in, user=None, passwd=None):
    filename = url_in.split('/')[-1]
    if not os.path.isfile(filename):
        if user and passwd:
            os.system(f'wget --user {user} --password {passwd} --user-agent="Mozilla/5.0" {url_in}')
        else:
            os.system(f'wget --user-agent="Mozilla/5.0" {url_in}')


if __name__ == "__main__":
    main()
