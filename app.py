import streamlit as st
from datetime import datetime
from llama_index.core.llms import ChatMessage
import logging
import time
import requests
from requests.auth import HTTPBasicAuth
import json
import re
from bs4 import BeautifulSoup
from llama_index.llms.ollama import Ollama
import os
from dotenv import load_dotenv
from streamlit_tree_select import tree_select

load_dotenv()
email = os.getenv("EMAIL")
token = os.getenv("TOKEN")

logging.basicConfig(level=logging.INFO)

if 'intel_urls' not in st.session_state:
    st.session_state.intel_urls = []

if 'user_facing_messages' not in st.session_state:
    st.session_state.user_facing_messages = []

if 'real_messages' not in st.session_state:
    st.session_state.real_messages = [{"role": "system", "content": f"You are an analyst who processes given information and makes inferences. Today's date is {"{:%B %d, %Y}".format(datetime.now())}."}]

if 'confluence_page_search' not in st.session_state:
    st.session_state.confluence_page_search = "119601397530606"

if 'urls_to_add' not in st.session_state:
    st.session_state.urls_to_add = set([])

if 'memoized_confluence_pages' not in st.session_state:
    st.session_state.memoized_confluence_pages = {}

def stream_chat(model, messages):
    try:
        llm = Ollama(model=model, request_timeout=120.0)
        resp = llm.stream_chat(messages)
        response = ""
        response_placeholder = st.empty()
        for r in resp:
            response += r.delta
            response_placeholder.write(response)
        logging.info(f"Model: {model}, Messages: {messages}, Response: {response}")
        return response
    except Exception as e:
        logging.error(f"Error during streaming: {str(e)}")
        raise e

def extract_confluence_page_id(url):
    try:
        pattern = r"https://elsevier\.atlassian\.net/wiki/spaces/\w+/pages/(\d+)/.*"
        if match := re.match(pattern, url):
            return match.group(1)
        return None
    except Exception as e:
        st.error(f"Error occurred while extracting the page ID: {e}")

def extract_text_from_url(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        text_content = " ".join([p.get_text() for p in soup.find_all("p")])
        return text_content
    except Exception as e:
        st.error(f"Error occurred while scraping the URL: {e}")
        return None

def intel_input_change():
    intel_url = st.session_state.intel_input_box
    logging.info(f"Intel: {intel_url}")
    confluence_page_id = extract_confluence_page_id(intel_url)
    if confluence_page_id:
        st.session_state.confluence_page_search = confluence_page_id
        return
    else:
        text_content = extract_text_from_url(intel_url)
        append_intel([{"url": url, "text": text_content}])

def append_intel(pages_with_texts):
    urls = ", ".join([page["url"] for page in pages_with_texts])
    st.session_state.real_messages.append({"role": "user", "content": f"I would like you to brief yourself on information from {urls}. If you understand, please respond with today's date."})
    st.session_state.real_messages.append({"role": "assistant", "content": f"I understand, and today's date is {"{:%B %d, %Y}".format(datetime.now())}."})
    for page in pages_with_texts:
        st.session_state.real_messages.append({"role": "user", "content": f"Information from {page["url"]}:\r\n\r\n{page["text"]}\r\n\r\nRetrieved on {datetime.now()}."})
    st.session_state.user_facing_messages.append({"role": "system", "content": f"(Contents of {urls} retrieved and stored in the conversation)"})

def get_confluence_content(page_id):
    url = f"https://elsevier.atlassian.net/wiki/api/v2/pages/{page_id}?body-format=export_view"
    auth = HTTPBasicAuth(email, token)
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

def extract_confluence_intel(page_id):
    content = get_confluence_content(page_id)
    raw_text = content["body"]["export_view"]["value"]
    soup = BeautifulSoup(raw_text, "html.parser")
    text = "\n ".join([p.get_text() for p in soup.find_all("p")])
    links = [a["href"] for a in soup.find_all("a", href=True)]
    return {
        "title": content["title"],
        "url": f"https://elsevier.atlassian.net/wiki{content['_links']['webui']}",
        "page_id": page_id,
        "text": text,
        "links": links
    }

def get_confluence_node(page_id, depth=0):
    page_info = {}
    if page_id in st.session_state.memoized_confluence_pages:
        page_info = st.session_state.memoized_confluence_pages[page_id]
    else:
        page_info = extract_confluence_intel(page_id)
        st.session_state.memoized_confluence_pages[page_id] = page_info
    node = {
        "label": f"'{page_info["title"]}'",
        "value": page_info["url"],
        "text": page_info["text"],
    }
    if depth < 2:
        node["children"] = get_children(page_id, page_info["links"], depth=depth+1)
    return node

def get_children(page_id, links, depth=0):
    children = []
    for link in links:
        if confluence_page_id := extract_confluence_page_id(link):
            if confluence_page_id == st.session_state.confluence_page_search:
                continue
            if (confluence_page_id in st.session_state.memoized_confluence_pages) or (confluence_page_id in st.session_state.urls_to_add):
                children.append(get_confluence_node(confluence_page_id, depth))
                continue
        elif "https://elsevier.atlassian.net" in link:
            continue
        children.append({"label": link, "value": link})
    for confluence_child in get_confluence_children(page_id):
        children.append(get_confluence_node(confluence_child["id"], depth))
    return children

def get_confluence_children(page_id):
    url = f"https://elsevier.atlassian.net/wiki/api/v2/pages/{page_id}/children"
    auth = HTTPBasicAuth(email, token)
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
    return response.json().get("results", [])


def main():
    logging.info("App started")

    if page_to_search := st.session_state.confluence_page_search:
        if st.sidebar.button("Cancel"):
            st.session_state.confluence_page_search = None
            st.rerun()
        if st.sidebar.button("Submit"):
            if not st.session_state.urls_to_add:
                st.warning("Please select at least one item to add.")
            else:
                st.session_state.confluence_page_search = None
                page_infos_to_add = []
                for url in st.session_state.urls_to_add:
                    if page_id := extract_confluence_page_id(url):
                        page_infos_to_add.append(st.session_state.memoized_confluence_pages[page_id])
                    else:
                        page_infos_to_add.append({"url": url, "text": extract_text_from_url(url)})
                append_intel(page_infos_to_add)
                st.session_state.intel_urls.extend(st.session_state.urls_to_add)
                st.session_state.urls_to_add = set([])
                st.rerun()

        # Search for Confluence page
        st.title("Confluence Page Selector")
        st.write(f"Confluence Page ID: {page_to_search}")
        nodes = [get_confluence_node(page_to_search)]
        print(json.dumps(nodes, indent=2))
        return_select = tree_select(nodes, no_cascade=True, show_expand_all=True)
        st.write("Selected items:")
        for checked_item in return_select["checked"]:
            st.session_state.urls_to_add.add(checked_item)
            print(checked_item)
            if item_page_id := extract_confluence_page_id(checked_item):
                page_info = st.session_state.memoized_confluence_pages.get(item_page_id)
                print(page_info)
                if not page_info:
                    page_info = extract_confluence_intel(item_page_id)
                    st.session_state.memoized_confluence_pages[item_page_id] = page_info
                st.markdown(f"- [{page_info['title']}]({page_info['url']})")
                continue
            st.markdown(f"- {checked_item}")

        #links_in_page = get_links_in_page(page_to_search)
        #for link in links_in_page:
            # Show as selected if already in the stack or to be added
            # selected = link in st.session_state.confluence_page_search_stack or link in st.session_state.confluence_pages_to_add
            #st.write(link)
        return

    st.title("Comp Intel Exchange")

    version = "0.0.2-confluence-demo"
    #model = "llama3.2:latest"
    #model = "llama3.1:latest"
    model = "phi3.5:latest"
    subtitle = f"Version: '{version}'\nModel: '{model}'"

    st.code(subtitle)

    st.sidebar.text_input("Copy URLs of Intel Here", key="intel_input_box", on_change=intel_input_change)
    for intel_url in st.session_state.intel_urls:
        st.sidebar.write(intel_url)

    for message in st.session_state.user_facing_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if prompt := st.chat_input("Your question"):
        logging.info(f"User input: {prompt}")

        st.session_state.real_messages.append({"role": "user", "content": prompt})
        st.session_state.user_facing_messages.append({"role": "user", "content": prompt})
        st.write(prompt)

    if st.session_state.real_messages and st.session_state.real_messages[-1]["role"] != "assistant" and st.session_state.real_messages[-1]["role"] != "system":
        with st.chat_message("assistant"):
            start_time = time.time()
            logging.info("Generating response")

            with st.spinner("Writing..."):
                try:
                    messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in st.session_state.real_messages]
                    response_message = stream_chat(model, messages)
                    duration = time.time() - start_time
                    st.session_state.real_messages.append({"role": "assistant", "content": response_message})
                    st.session_state.user_facing_messages.append({"role": "assistant", "content": response_message})
                    logging.info(f"Response: {response_message}, Duration: {duration:.2f} s")

                except Exception as e:
                    st.session_state.real_messages.append({"role": "assistant", "content": str(e)})
                    st.session_state.user_facing_messages.append({"role": "assistant", "content": str(e)})
                    st.error("An error occurred while generating the response.")
                    logging.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
