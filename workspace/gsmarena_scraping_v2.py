import requests
from bs4 import BeautifulSoup
import csv
import os
import time
import random
import pandas as pd

class Gsmarena:
    def __init__(self):
        self.phones = []
        self.features = ["Brand", "Model Name", "Model Image"]
        self.url = 'https://www.gsmarena.com/'
        self.new_folder_name = 'GSMArenaDataset'
        self.absolute_path = os.path.join(os.getcwd(), self.new_folder_name)

    def crawl_html_page(self, sub_url):
        url = self.url + sub_url
        headers = {"User-Agent": "your-user-agent"}
        retries = 5
        while retries > 0:
            try:
                time.sleep(random.uniform(5, 10))  # Random delay between 5 to 10 seconds
                page = requests.get(url, timeout=10, headers=headers)
                if page.status_code == 429:  # Too many requests
                    print("Too many requests. Retrying after a delay...")
                    time.sleep(60)  # Wait for 1 minute before retrying
                    retries -= 1
                    continue
                soup = BeautifulSoup(page.text, 'html.parser')
                return soup
            except requests.ConnectionError:
                print("Network error. Please check your connection and try again.")
                exit()
            except Exception as e:
                print(f"An error occurred: {e}")
                exit()
        return None

    def crawl_phone_brands(self):
        phones_brands = []
        soup = self.crawl_html_page('makers.php3')
        
        if soup is None:
            print("Failed to retrieve HTML content from the website.")
            return phones_brands
        
        container = soup.find('div', id='list-brands')
        if not container:
            print("No container found with phone brands.")
            return phones_brands
        
        print("Container found, attempting to parse links.")
        list_items = container.find_all('li')
        for item in list_items:
            a_tag = item.find('a')
            if a_tag:
                brand_name = a_tag.text.strip()
                brand_link = a_tag['href']
                temp = [brand_link.split('-')[0], brand_name, brand_link]
                phones_brands.append(temp)
        
        print(f"Found {len(phones_brands)} phone brands.")
        return phones_brands

    def crawl_phones_models(self, phone_brand_link):
        links = []
        nav_link = []
        soup = self.crawl_html_page(phone_brand_link)
        nav_data = soup.find(class_='nav-pages')
        if not nav_data:
            nav_link.append(phone_brand_link)
        else:
            nav_link = nav_data.findAll('a')
            nav_link = [link['href'] for link in nav_link]
            nav_link.append(phone_brand_link)
            nav_link.insert(0, nav_link.pop())
        for link in nav_link:
            soup = self.crawl_html_page(link)
            wrapper_brands = soup.find(id='wrapper-brands')
            if wrapper_brands:
                general_menu = wrapper_brands.find(class_='general-menu')
                if general_menu:
                    for line1 in general_menu.findAll('a'):
                        links.append(line1['href'])
                else:
                    print(f"No general-menu found for model page link: {link}")
            else:
                print(f"No wrapper-brands found for model page link: {link}")

        return links

    def crawl_phones_models_specification(self, link, phone_brand):
        phone_data = {}
        soup = self.crawl_html_page(link)
        if soup is None:
            print(f"Failed to retrieve HTML content for specification link: {link}")
            return phone_data
        
        model_name_tag = soup.find('h1', class_='section nobor')
        if model_name_tag:
            model_name = model_name_tag.text
        else:
            print(f"No model name found for specification link: {link}")
            with open(f"debug_model_name_{link.replace('/', '_')}.html", 'w', encoding='utf-8') as file:
                file.write(soup.prettify())
            return phone_data
        
        model_img_html = soup.find('div', class_='specs-cp-pic-rating')
        if model_img_html:
            img_tag = model_img_html.find('a')
            if img_tag:
                img_src = img_tag.find('img')
                if img_src:
                    model_img = img_src['src']
                else:
                    print(f"No img tag found within model image div for specification link: {link}")
                    model_img = 'N/A'
            else:
                print(f"No anchor tag found within model image div for specification link: {link}")
                model_img = 'N/A'
        else:
            print(f"No model image found for specification link: {link}")
            with open(f"debug_model_img_{link.replace('/', '_')}.html", 'w', encoding='utf-8') as file:
                file.write(soup.prettify())
            model_img = 'N/A'
        
        phone_data.update({"Brand": phone_brand})
        phone_data.update({"Model Name": model_name})
        phone_data.update({"Model Image": model_img})
        
        for table in soup.findAll('table'):
            for line in table.findAll('tr'):
                temp = []
                for l in line.findAll('td'):
                    text = l.getText().strip()
                    temp.append(text)
                if temp:
                    key = temp[0]
                    value = temp[1]
                    if key in phone_data:
                        key += '_1'
                    if key not in self.features:
                        self.features.append(key)
                    phone_data[key] = value
        
        return phone_data

    def create_folder(self):
        if not os.path.exists(self.new_folder_name):
            os.mkdir(self.new_folder_name)
            print(f"Creating {self.new_folder_name} folder...")
            time.sleep(2)
            print("Folder created.")
        else:
            print(f"{self.new_folder_name} directory already exists.")

    def check_file_exists(self):
        return os.listdir(self.absolute_path)

    def save_specifications_to_file(self):
        phone_brands = self.crawl_phone_brands()
        self.create_folder()
        files_list = self.check_file_exists()
        for brand in phone_brands:
            phones_data = []
            if (brand[0].title() + '.csv') not in files_list:
                links = self.crawl_phones_models(brand[2])[:100]  # Limit to first 100 models
                print(f"Working on {brand[0].title()} brand.")
                for idx, value in enumerate(links):
                    print(f"Fetching data for model {idx + 1} of {brand[0].title()}.")
                    datum = self.crawl_phones_models_specification(value, brand[0])
                    datum = {k: v.replace('\n', ' ').replace('\r', ' ') for k, v in datum.items()}
                    phones_data.append(datum)
                    print(f"Completed {idx + 1}/{len(links)}")
                with open(os.path.join(self.absolute_path, brand[0].title() + ".csv"), "w", newline='', encoding='utf-8') as file:
                    dict_writer = csv.DictWriter(file, fieldnames=self.features)
                    dict_writer.writeheader()
                    dict_writer.writerows(phones_data)
                print(f"Data for {brand[0].title()} saved in the file.")
            else:
                print(f"{brand[0].title()}.csv file already in your directory.")
        
        # Merge all individual CSV files into one
        self.merge_csv_files()

    def merge_csv_files(self):
        all_files = os.listdir(self.absolute_path)
        csv_files = [f for f in all_files if f.endswith('.csv')]
        merged_data = []

        for file in csv_files:
            file_path = os.path.join(self.absolute_path, file)
            with open(file_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    merged_data.append(row)
        
        # Save merged data to a single CSV file
        merged_file_path = os.path.join(self.absolute_path, 'merged_GSMArenaDataset.csv')
        with open(merged_file_path, 'w', newline='', encoding='utf-8') as file:
            dict_writer = csv.DictWriter(file, fieldnames=self.features)
            dict_writer.writeheader()
            dict_writer.writerows(merged_data)
        print(f"All data merged into {merged_file_path}")

if __name__ == "__main__":
    try:
        gsmarena = Gsmarena()
        gsmarena.save_specifications_to_file()
    except KeyboardInterrupt:
        print("File has been stopped due to keyboard interruption.")
