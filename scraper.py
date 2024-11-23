import json
import re
import time
import unicodedata
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def setup_driver():
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in headless mode
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        service = Service()  # Specify the path to chromedriver if necessary
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except WebDriverException as e:
        logging.critical(f"WebDriver error during setup: {str(e)}")
        raise

def clean_text(text):
    # Remove unnecessary characters like '\n' and extra spaces
    text = text.replace('\n', ' ').replace('\\n', ' ').strip()
    # Replace common Unicode escape sequences with their corresponding characters
    text = text.replace('\u201c', '“').replace('\u201d', '”')
    text = text.replace('\u2018', '‘').replace('\u2019', '’')
    text = text.replace('\u2026', '…').replace('\u2013', '–')
    text = text.replace('\u2014', '—').replace('\u00a0', ' ')
    # Normalize the text to remove any remaining Unicode escape sequences
    text = unicodedata.normalize('NFKC', text)
    return text

def clean_text_aws(text):
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def scrape_react_docs(driver):
    react_docs = []
    try:
        react_url = "https://react.dev/learn"
        driver.get(react_url)
        time.sleep(3)  # Wait for the page to load

        sections = [
            "Installation",
            "Describing the UI",
            "Adding Interactivity",
            "Managing State",
            "Escape Hatches"
        ]

        for section in sections:
            try:
                element = driver.find_element(By.LINK_TEXT, section)
                element.click()
                time.sleep(2)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                article = soup.find('article')
                if article:
                    content = clean_text(article.get_text())
                    react_docs.append({
                        "title": section,
                        "source": "react",
                        "url": driver.current_url,
                        "sections": [content]
                    })
                else:
                    logging.warning(f"No article found for section {section}")
                driver.back()
                time.sleep(2)
            except NoSuchElementException as e:
                logging.error(f"Element not found for section {section}: {str(e)}")
            except Exception as e:
                logging.exception(f"Unexpected error in section {section}: {str(e)}")
    except Exception as e:
        logging.critical(f"Error in scrape_react_docs: {str(e)}")
    return react_docs

def scrape_aws_lambda_docs(driver):
    aws_docs = []
    try:
        aws_url = "https://docs.aws.amazon.com/lambda/latest/dg/welcome.html"
        driver.get(aws_url)
        time.sleep(5)  # Wait for the page to load

        aws_sections = [
            ("What is AWS Lambda?", "//a[@href='getting-started.html']"),
            ("Example apps", "//a[@href='example-apps.html']"),
            ("Building with TypeScript", "//a[@href='lambda-typescript.html']"),
            ("Integrating other services", "//a[@href='lambda-services.html']"),
            ("Code examples", "//a[@href='service_code_examples.html']")
        ]

        for section_title, xpath in aws_sections:
            try:
                # Wait for the element to be clickable
                element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )

                # Click to navigate to the section
                element.click()
                time.sleep(5)  # Wait for the new page to load

                # Parse the page content
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                content_div = soup.find('div', {'class': 'awsdocs-container'})

                if content_div:
                    content = clean_text(content_div.get_text())
                    if content:
                        aws_docs.append({
                            "title": section_title,
                            "source": "aws_lambda",
                            "url": driver.current_url,
                            "sections": [content]
                        })
                    else:
                        logging.warning(f"Empty content for section {section_title}")
                else:
                    logging.warning(f"No content found for section {section_title}")

                # Navigate back to the main page
                driver.back()
                time.sleep(2)

            except TimeoutException as e:
                logging.error(f"Timeout while scraping section {section_title}: {str(e)}")
            except NoSuchElementException as e:
                logging.error(f"Element not found in section {section_title}: {str(e)}")
            except Exception as e:
                logging.exception(f"Error scraping section {section_title}: {str(e)}")
    except Exception as e:
        logging.critical(f"Error in scrape_aws_lambda_docs: {str(e)}")
    return aws_docs

def main():
    logging.basicConfig(level=logging.INFO)
    try:
        driver = setup_driver()
        react_docs = scrape_react_docs(driver)
        aws_docs = scrape_aws_lambda_docs(driver)
        all_docs = react_docs + aws_docs

        with open('documentation.json', 'w') as f:
            json.dump(all_docs, f, indent=4)
    except Exception as e:
        logging.exception(f"An error occurred in main: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()