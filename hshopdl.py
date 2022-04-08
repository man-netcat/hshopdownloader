import argparse
import time
from os.path import exists

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm
from webdriver_manager.microsoft import EdgeChromiumDriverManager


def filesafe_name(filename):
    keepcharacters = (' ', '.', '_')
    return "".join(c for c in filename if c.isalnum() or c in keepcharacters).rstrip()


def load_page(url, wait_for_element):
    driver.get(url)
    try:
        element_present = EC.presence_of_element_located(
            (By.CLASS_NAME, wait_for_element))
        wait.until(element_present)
    except TimeoutException:
        print("Timed out waiting for page to load")
        exit(1)


def download_rom(filename, rom_url):
    dest = f"{config['dest']}/{filename}"
    if exists(dest):
        print("File already exists, skipping.")
        return
    with requests.get(rom_url, stream=True) as r:
        r.raise_for_status()
        field_size_limit = int(r.headers.get('content-length', 0))
        progress_bar = tqdm(total=field_size_limit, unit='iB', unit_scale=True)
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                progress_bar.update(len(chunk))
        progress_bar.close()


def process_game(game, subcat):
    print(f"Processing Game Title: {game.text}")
    game_url = base_url + game['href']
    load_page(game_url, 'btn')
    time.sleep(1)
    driver.find_element(
        by=By.XPATH, value='//*[@id="content-get"]/button').click()
    try:
        element_present = EC.presence_of_element_located(
            (By.CLASS_NAME, 'link'))
        link = wait.until(element_present)
    except TimeoutException:
        print("Timed out waiting for link to load")
        exit(1)
    linksoup = BeautifulSoup(link.get_attribute('outerHTML'), 'lxml')
    rom_url = linksoup.find(class_='link')['href']
    filename = f"{subcat} - {filesafe_name(game.text)}.cia"
    download_rom(filename, rom_url)


def process(search_query, categories, region):
    # Make driver and wait for page to fully load

    for subcat in categories:
        print(f"Processing Category: {subcat}")
        url = query_url % (base_url, search_query, subcat, region)

        load_page(url, 'content')

        # Extract game list
        soup = BeautifulSoup(driver.page_source, 'lxml')
        list = soup.find(class_='content-list')
        cs = list.find_all(class_='content')

        for c in cs:
            game = c.find('a')
            process_game(game, subcat)


def main():
    process(config['query'], categories, config['region'])


if __name__ == '__main__':
    base_url = 'https://hshop.erista.me/'
    query_url = "%s/search?q=%s&c=%s&sc=%s"

    # Command line arguments
    parser = argparse.ArgumentParser(description="HShop Downloader",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("query", help="Search Query")
    parser.add_argument("-r", "--region", help="Region", default='na')
    parser.add_argument("-c", "--cats", help="Categories",
                        default='games updates dlc')
    parser.add_argument(
        "-d", "--dest", help="Download Destination Location", default='.')
    args = parser.parse_args()
    config = vars(args)
    categories = config['cats'].split(' ')

    executable_path = EdgeChromiumDriverManager().install()

    # Set Options
    options = Options()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument("--test-type")
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')

    # Service
    service = Service(executable_path=executable_path)

    # Init Webdriver
    driver = webdriver.Edge(service=service, options=options)
    wait = WebDriverWait(driver, 3)

    main()
