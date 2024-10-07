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

logging.basicConfig(level=logging.INFO)

if 'intel_urls' not in st.session_state:
    st.session_state.intel_urls = []

if 'user_facing_messages' not in st.session_state:
    st.session_state.user_facing_messages = []

if 'real_messages' not in st.session_state:
    st.session_state.real_messages = [{"role": "system", "content": f"You are an analyst who processes given information and makes inferences. Today's date is {"{:%B %d, %Y}".format(datetime.now())}."}]

if 'confluence_page_search_id' not in st.session_state:
    st.session_state.confluence_page_search_id = "119601351459863"

if 'confluence_pages_to_add' not in st.session_state:
    st.session_state.confluence_pages_to_add = []

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
        match = re.match(pattern, url)
        if match:
            return match.group(1)
        return None
            page_id = url.split("/")[-1]
            return page_id
    except Exception as e:
        st.error(f"Error occurred while extracting the page ID: {e}")

def process_url(url):
    confluence_page_id = extract_confluence_page_id(url)
    if confluence_page_id:
        st.session_state.confluence_page_search_id = confluence_page_id
    else
        handle_regular_url(url)

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
    confluence_page_id = extract_confluence_page_id(url)
    if confluence_page_id:
        st.session_state.confluence_page_search_id = confluence_page_id
    else
        text_content = extract_text_from_url(url)
        append_intel([{"url": url, "text": text_content}])

def append_intel(pages_with_texts):
    urls = ", ".join([page["url"] for page in pages_with_texts])
    st.session_state.real_messages.append({"role": "user", "content": f"I would like you to brief yourself on information from {urls}. If you understand, please respond with today's date."})
    st.session_state.real_messages.append({"role": "assistant", "content": f"I understand, and today's date is {"{:%B %d, %Y}".format(datetime.now())}."})
    for page in pages_with_texts:
        st.session_state.real_messages.append({"role": "user", "content": f"Information from {page.url}:\r\n\r\n{page.text}\r\n\r\nRetrieved on {datetime.now()}."})
    st.session_state.user_facing_messages.append({"role": "system", "content": f"(Contents of {urls} retrieved and stored in the conversation)"})

def main():
    logging.info("App started")

    st.title("Comp Intel Exchange")

    version = "0.0.2-confluence-demo"
    #model = "llama3.2:latest"
    #model = "llama3.1:latest"
    model = "phi3.5:latest"

    subtitle = f"Version: '{version}'\nModel: '{model}'"
    st.code(subtitle)

    if st.session_state.confluence_page_search_id:
        st.write(f"Confluence Page ID: {st.session_state.confluence_page_search_id}")
        return

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
