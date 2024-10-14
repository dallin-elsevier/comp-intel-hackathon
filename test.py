import streamlit as st
import requests
from functools import lru_cache

# Fake sublist fetcher, stubbed out
def get_sublist(url):
    return [f"{url}/subpage1", f"{url}/subpage2"]

# Memoized function to check if a URL matches a domain
@lru_cache(maxsize=128)
def check_domain(url, domain):
    return domain in url

# Memoized function to check for 404 status
@lru_cache(maxsize=128)
def check_for_404(url):
    try:
        response = requests.head(url, allow_redirects=True)
        return response.status_code == 404
    except requests.RequestException:
        return True  # Consider a request failure as a 404 for this example

# Main app function
def main():
    st.title("URL Checker")

    # Initialize session state to store final checked URLs and editable URLs
    if 'url_list' not in st.session_state:
        # Initial list of URLs
        st.session_state['url_list'] = [
            "https://example.com",
            "https://example.com/notfound",
            "https://anotherdomain.com"
        ]

    if 'expanded_urls' not in st.session_state:
        st.session_state['expanded_urls'] = set()

    domain_to_match = st.text_input("Domain to match", "example.com")

    st.write("### URLs:")
    checked_urls = {}

    # Iterate over the list of URLs in session state
    for i, url in enumerate(st.session_state['url_list']):
        col1, col2, col3, col4 = st.columns([1, 8, 2, 2])

        with col1:
            # Checkbox for each URL
            checked_urls[url] = st.checkbox("", value=True, key=f"check_{i}")

        with col2:
            # Editable URL
            edited_url = st.text_input(url, value=url, key=f"edit_{i}")
            # Update the URL in the session state list if edited
            st.session_state['url_list'][i] = edited_url

        with col3:
            # Check if it matches the domain
            if check_domain(edited_url, domain_to_match):
                # Plus icon for matching URLs to expand a sublist
                if st.button("➕", key=f"expand_{i}"):
                    if edited_url not in st.session_state['expanded_urls']:
                        # Expand the sublist and insert into the main URL list
                        sublist = get_sublist(edited_url)
                        st.session_state['url_list'].extend(sublist)
                        st.session_state['expanded_urls'].add(edited_url)
            elif check_for_404(edited_url):
                # Red "X" for URLs that return 404
                st.write("❌")
            else:
                st.write(" ")
        st.markdown("<hr>", unsafe_allow_html=True)

    # Filter checked URLs
    filtered_urls = [url for url, is_checked in checked_urls.items() if is_checked]

    st.write("### Final Checked URLs")
    for url in filtered_urls:
        st.write(url)

    # Button to return the final list (simulate returning to another context)
    if st.button("Return Final List"):
        st.write(f"Final URLs: {filtered_urls}")

if __name__ == "__main__":
    main()
