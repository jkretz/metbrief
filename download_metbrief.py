import os
import requests
import datetime
import shutil
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

USER_AGENT = {'User-agent': 'Mozilla/5.0'}


def main():

    # Copy template to daily directory and clean-up if needed
    today = datetime.date.today().strftime('%m%d')
    if not os.path.isdir(today):
        shutil.copytree('template', today)
        os.system(f'rm -r {today}/charts/*')
    os.chdir(f'{today}/charts')

    # Download DWD charts
    for chart in ['bwk_bodendruck_na_ana', 'ico_500ht_na_ana']:
        file_url = f'https://www.dwd.de/DWD/wetter/wv_spez/hobbymet/wetterkarten/{chart}.png'
        wget_download(file_url)
        
    exit()

    # Download wetter3
    wget_download('https://wetter3.de/Animation_00_UTC/12_10.gif')

    # Download flugwetter.de
    for temp_loc in ['11520', '10771']:
        file_url = f'https://flugwetter.de/fw/scripts/getchart.php?src=nb_obs_tmp_{temp_loc}_lv_999999_p_000_0000.png'
        wget_download(file_url, user=USERNAME_DWD, passwd=PASSWORD_DWD)

    # Get cookies for session
    driver = webdriver.Firefox()
    driver.get('https://kachelmannwetter.com/')
    cookies = driver.get_cookies()
    driver.close()

    s = requests.Session()
    for cookie in cookies:
        s.cookies.set(cookie['name'], cookie['value'])

    # Satellite
    locations = ['tschechische-republik', 'mitteleuropa']
    for loc in locations:
        url = f'https://kachelmannwetter.com/de/sat/{loc}/satellit-hd-5min.html'
        download_kachelmann(s, url, loc, 'sat')

    # Radar
    loc = 'tschechische-republik'
    url = f'https://kachelmannwetter.com/de/regenradar/{loc}'
    download_kachelmann(s, url, loc, 'radar')

    var_topmeteo = {'pfd': 28, 'thermik': 24, 'wolken': 26, 'wind_1500': 39}
    today = datetime.datetime.now()
    today = today.replace(hour=0, minute=0, second=0, microsecond=0)
    download_topmeteo(var_topmeteo, loc='de', day=0, today=today)


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
    os.symlink(download_url.split("/")[-1], link_filename)


def wget_download(url_in, user=None, passwd=None):
    filename = url_in.split('/')[-1]
    if not os.path.isfile(filename):
        if user and passwd:
            os.system(f'wget --user {user} --password {passwd} --user-agent="Mozilla/5.0" {url_in}')
        else:
            os.system(f'wget --user-agent="Mozilla/5.0" {url_in}')


if __name__ == "__main__":
    main()
