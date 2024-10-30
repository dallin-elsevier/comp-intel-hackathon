import os
import streamlit as st
import requests
from functools import lru_cache
from dotenv import load_dotenv
import logging
import utils.context_explorer as context_explorer
import uuid
import pages.chat as chat

load_dotenv()
email = os.getenv("EMAIL")
confluence_token = os.getenv("CONFLUENCE_TOKEN")

logging.basicConfig(level=logging.INFO)

# Function to initialize URLs with unique IDs and child structure
def initialize_url(url, parent_id=None):
    unique_id = str(uuid.uuid4())
    context = context_explorer.get_url_context(url)
    return {
        "id": unique_id,
        "url": url,
        "confluence_id": context.get("confluence_id"),
        "title": context.get("title"),
        "text_preview": context.get("text_preview"),
        "text": context.get("text"),
        "parent_id": parent_id,
        "children": []
    }

# Recursive function to display URLs and handle nesting
def display_url_structure(url_structure, level=1):
    checked_urls = []
    for item in url_structure:
        indentCol, col1, col2, col3 = st.columns([level*3, 2, 64, 2])

        with col1:
            # Should be checked ONLY unless text is empty or none
            shouldBeChecked = item["text"] and item["text_preview"]
            checked = st.checkbox("", value=shouldBeChecked, key=f"check_{item['id']}")
            if checked:
                checked_urls.append(item)  # Append the full item for final output

        with col2:
            st.markdown(f"**{item['title'] or item['url']}**")
            if item["text_preview"]:
                st.markdown(f"{item['text_preview']}")

            # Editable URL input
            edited_url = st.text_input("Edit URL", value=item["url"], key=f"edit_{item['id']}")
            if edited_url != item["url"]:
                # Re-fetch context data if URL is modified
                logging.info(f"URL modified: {item['url']} -> {edited_url}")
                context = context_explorer.get_url_context(edited_url)
                item.update({
                    "url": edited_url,
                    "title": context.get("title"),
                    "confluence_id": context.get("confluence_id"),
                    "text": context.get("text"),
                    "text_preview": context.get("text_preview")
                })
                st.rerun()

        with col3:
            if item["confluence_id"] and "expanded" not in item:
                if st.button("➕", key=f"expand_{item['id']}"):
                    # Add child URLs (stubs here; replace with actual logic)
                    children = context_explorer.get_child_urls(item["confluence_id"], email, confluence_token)
                    for child_url in children:
                        item["children"].append(initialize_url(child_url, parent_id=item["id"]))
                    item["expanded"] = True
            elif "expanded" in item:
                st.write("✔️")  # Indicate already expanded
            elif not item["text"]:
                st.write("❌")

        # Display child URLs recursively
        if "children" in item:
            checked_urls.extend(display_url_structure(item["children"], level + 1))

        # Horizontal line between entries
        st.markdown("<hr>", unsafe_allow_html=True)

    return checked_urls

# Main app function
def show():
    st.title("Intel Gathering")

    initial_url = st.session_state.confluence_page_search

    # Initialize session state if needed
    if 'url_structure' not in st.session_state:
        initial_intel = initialize_url(initial_url)
        children = context_explorer.get_child_urls(initial_intel["confluence_id"], email, confluence_token)
        for child_url in children:
            initial_intel["children"].append(initialize_url(child_url, parent_id=initial_intel["id"]))
            initial_intel["expanded"] = True
        st.session_state['url_structure'] = [
            initial_intel
        ]

    checked_urls = display_url_structure(st.session_state['url_structure'])

    # Final list of checked URLs based on their unique IDs
    st.session_state['final_checked_urls'] = checked_urls

    st.write("### Final Checked URLs")
    for item in st.session_state['final_checked_urls']:
        st.write(f"{item['title'] or item['url']} - {item['url']}")

    # Button to simulate returning final checked list
    if st.button("Return List"):
        st.session_state.confluence_page_search = None
        st.session_state.urls_to_add = st.session_state['final_checked_urls']
        st.session_state['url_structure'] = []
        return
