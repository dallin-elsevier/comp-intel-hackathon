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
    try:
        pattern = r"https://elsevier\.atlassian\.net/wiki/spaces/\w+/pages/(\d+)/?.*"
        if match := re.match(pattern, url):
            return match.group(1)
        return None
    except Exception as e:
        st.error(f"Error occurred while extracting the page ID: {e}")

@lru_cache(maxsize=128)
def extract_text_from_url(url):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            st.error(f"Error occurred while scraping the URL: {response.text}")
            return None
        soup = BeautifulSoup(response.content, "html.parser")
        text_content = " ".join([p.get_text() for p in soup.find_all("p")])
        return text_content
    except requests.RequestException as e:
        st.error(f"Error occurred while scraping the URL: {e}")
        return None

@lru_cache(maxsize=128)
def get_confluence_content(page_id, email, confluence_token):
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
    return response.json()

@lru_cache(maxsize=128)
def extract_confluence_intel(page_id, email, confluence_token):
    content = get_confluence_content(page_id, email, confluence_token)
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
        "url": f"https://elsevier.atlassian.net/wiki{content['_links']['webui']}",
        "page_id": page_id,
        "text": text,
        "links": filtered_links
    }

@lru_cache(maxsize=128)
def get_confluence_node(page_id, email, confluence_token):
    page_info = {}
    page_info = extract_confluence_intel(page_id, email, confluence_token)
    node = {
        "label": f"'{page_info["title"]}'",
        "value": page_info["url"],
        "text": page_info["text"],
    }
    return node

@lru_cache(maxsize=128)
def get_children(page_id, email, confluence_token):
    children = get_confluence_children(page_id, email, confluence_token)
    page_links = extract_confluence_intel(page_id, email, confluence_token)["links"]
    return children + page_links

@lru_cache(maxsize=128)
def get_confluence_children(page_id, email, confluence_token):
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
#         st.error(f"Error occurred while fetching the children: {e}")
        return []
