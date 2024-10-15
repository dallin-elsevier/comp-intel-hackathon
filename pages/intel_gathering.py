import os
import streamlit as st
import requests
from functools import lru_cache
from dotenv import load_dotenv
import logging
import utils.context_explorer as context_explorer
import pages.chat as chat

load_dotenv()
email = os.getenv("EMAIL")
confluence_token = os.getenv("CONFLUENCE_TOKEN")

logging.basicConfig(level=logging.INFO)

def show():
    st.title("Intel Gathering")

    if 'intel_search_url_list' not in st.session_state:
        initial_url = st.session_state.confluence_page_search
        st.session_state['intel_search_url_list'] = context_explorer.get_children(initial_url, email, confluence_token)

    if 'expanded_urls' not in st.session_state:
        st.session_state['expanded_urls'] = set()

    checked_urls = {}

    # Iterate over the list of URLs in session state
    for i, url in enumerate(st.session_state['intel_search_url_list']):
        col1, col2, col3, col4 = st.columns([1, 8, 2, 2])

        with col1:
            # Checkbox for each URL
            checked_urls[url] = st.checkbox("", value=True, key=f"check_{i}")

        with col2:
            # Editable URL
            edited_url = st.text_input(url, value=url, key=f"edit_{i}")
            # Update the URL in the session state list if edited
            st.session_state['intel_search_url_list'][i] = edited_url

        with col3:
            if context_explorer.extract_confluence_page_id(edited_url):
                if edited_url in st.session_state['expanded_urls']:
                    # Already expanded, show a different icon (e.g., a checkmark or down arrow)
                    st.write("✔️")  # You can replace this with any other icon or emoji
                else:
                    # Show the plus icon to expand the URL
                    if st.button("➕", key=f"expand_{i}"):
                        # Expand the sublist and insert into the main URL list
                        page_id = context_explorer.extract_confluence_page_id(edited_url)
                        sublist = context_explorer.get_children(page_id, email, confluence_token)
                        st.session_state['intel_search_url_list'].extend(sublist)
                        st.session_state['expanded_urls'].add(edited_url)
            elif context_explorer.extract_text_from_url(edited_url) == None:
                st.write("❌")
            else:
                st.write(" ")
        st.markdown("<hr>", unsafe_allow_html=True)

    # Filter checked URLs
    filtered_urls = [url for url, is_checked in checked_urls.items() if is_checked]

    st.write("### Selected URLs")
    for url in filtered_urls:
        st.write(url)

    # Button to return the final list (simulate returning to another context)
    if st.button("Return List"):
        st.session_state.urls_to_add = filtered_urls
        st.session_state.confluence_page_search = None
        logging.info(f"URLs: {filtered_urls}")
        st.rerun()
