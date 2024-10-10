# Comp Intel 

This repo is for the 2024 hackathon project "competitive intel exchange"

## To Run

1. Set up and activate your python venv for this project
2. Run `pip install -r requirements.txt` to download dependencies
3. Set up an `.env` file with the following variables:
   - `EMAIL` - your `science.regn.net` email (for confluence)
   - `CONFLUENCE_TOKEN` - your Atlassian API token
   - `OPENAIKEY` - the key allowing access to `https://els-patientpass.openai.azure.com/`
4. Run `streamlit run app.py`
