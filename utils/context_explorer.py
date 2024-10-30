import os
from dotenv import load_dotenv
import streamlit as st
from datetime import datetime
import logging
import time
import requests
from requests.auth import HTTPBasicAuth
import json
import re
from bs4 import BeautifulSoup
from openai import AzureOpenAI
from functools import lru_cache

load_dotenv()
email = os.getenv("EMAIL")
confluence_token = os.getenv("CONFLUENCE_TOKEN")

logging.basicConfig(level=logging.INFO)

@lru_cache(maxsize=128)
def extract_confluence_page_id(url):
    logging.info(f"Extracting confluence page ID from {url}")
    try:
        pattern = r"https://elsevier\.atlassian\.net/wiki/spaces/\w+/pages/(\d+)/?.*"
        alt_pattern = r"https://elsevier\.atlassian\.net/wiki/viewpage.action\?pageId=(\d+)/?.*"
        if match := re.match(pattern, url):
            logging.info(f"Page ID extracted: {match.group(1)}")
            return match.group(1)
        if match := re.match(alt_pattern, url):
            logging.info(f"Page ID extracted: {match.group(1)}")
            return match.group(1)
        logging.info("Page ID not found")
        return None
    except Exception as e:
        st.error(f"Error occurred while extracting the page ID: {e}")

def get_url_context(url):
    if page_id := extract_confluence_page_id(url):
        return extract_confluence_intel(page_id, email, confluence_token)
    text = extract_text_from_non_confluence_url(url)
    return {
        "confluence_id": None,
        "title": url,
        "text_preview": f"{text[:100]}..." if text else "(No text retrieved)",
        "text": text or None,
    }

@lru_cache(maxsize=128)
def extract_text_from_url(url):
    logging.info(f"Extracting text from {url}")
    try:
        if page_id := extract_confluence_page_id(url):
            logging.info(f"Page ID found: {page_id}")
            return extract_confluence_intel(page_id, email, confluence_token)["text"]
        logging.info("Page ID not found")
        return extract_text_from_non_confluence_url(url)
    except requests.RequestException as e:
        logging.error(f"Error occurred while scraping the URL: {e}")
        return None

@lru_cache(maxsize=128)
def extract_text_from_non_confluence_url(url):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            logging.error(f"Error occurred while scraping the URL: {response.text}")
            return None
        soup = BeautifulSoup(response.content, "html.parser")
        text_content = " ".join([p.get_text() for p in soup.find_all("p")])
        return text_content
    except requests.RequestException as e:
        logging.error(f"Error occurred while scraping the URL: {e}")
        return None

@lru_cache(maxsize=128)
def get_confluence_content(page_id, email, confluence_token):
    logging.info(f"Getting confluence content for {page_id}")
    url = f"https://elsevier.atlassian.net/wiki/api/v2/pages/{page_id}?body-format=export_view"
    auth = HTTPBasicAuth(email, confluence_token)
    headers = {
      "Accept": "application/json"
    }
    response = requests.request(
       "GET",
       url,
       headers=headers,
       auth=auth,
       verify=False
    )
    # If there is an error, log it and return an empty dict
    if response.status_code != 200:
        logging.error(f"Error occurred while getting confluence content: {response.text}")
        return {}
    return response.json()

def conflu_url_from_page_id(page_id):
    return f"https://elsevier.atlassian.net/wiki/pages/viewpage.action?pageId={page_id}"

@lru_cache(maxsize=128)
def extract_confluence_intel(page_id, email, confluence_token):
    logging.info(f"Getting confluence intel for {page_id}")
    content = get_confluence_content(page_id, email, confluence_token)
    if "body" not in content:
        return {
            "title": "Page not found",
            "url": conflu_url_from_page_id(page_id),
            "page_id": page_id,
            "text": "Page not found",
            "links": []
        }
    raw_text = content["body"]["export_view"]["value"]
    soup = BeautifulSoup(raw_text, "html.parser")
    text = "\n ".join([p.get_text() for p in soup.find_all("p")])
    links = [a["href"] for a in soup.find_all("a", href=True)]
    filtered_links = []
    for link in links:
        if confluence_page_id := extract_confluence_page_id(link):
            filtered_links.append(link)
        elif "https://elsevier.atlassian.net" in link:
            continue
        else:
            filtered_links.append(link)
    return {
        "title": content["title"],
        "confluence_id": page_id,
        "text": text,
        "links": filtered_links,
        "text_preview": f"{text[:100]}..." if text else "(No text retrieved)",
    }

@lru_cache(maxsize=128)
def get_child_urls(page_id, email, confluence_token):
    logging.info(f"Getting children for {page_id}")
    children = get_confluence_children(page_id, email, confluence_token)
    page_links = extract_confluence_intel(page_id, email, confluence_token)["links"]
    return children + page_links

@lru_cache(maxsize=128)
def get_confluence_children(page_id, email, confluence_token):
    logging.info(f"Getting confluence children for {page_id}")
    url = f"https://elsevier.atlassian.net/wiki/api/v2/pages/{page_id}/children"
    auth = HTTPBasicAuth(email, confluence_token)
    headers = {
     "Accept": "application/json"
    }
    response = requests.request(
      "GET",
      url,
      headers=headers,
      auth=auth,
      verify=False
    )
    try:
        links = response.json().get("results", [])
        return list(f"https://elsevier.atlassian.net/wiki/spaces/{child["spaceId"]}/pages/{child["id"]}" for child in links)
    except Exception as e:
        logging.error(f"Response was not JSON: {response.text}")
        logging.error(f"Error occurred while getting children for {page_id}: {e}")
        return list([])
