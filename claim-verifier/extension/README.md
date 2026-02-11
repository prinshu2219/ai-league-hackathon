# AI Claim Verifier – Browser Extension

Chrome extension (Manifest V3) to verify claims from any webpage.

## How to use

1. **From selection:** Select text on a page, right-click, choose **Verify claim with AI Claim Verifier**. A new tab opens the Claim Verifier app with the claim pre-filled.
2. **From popup:** Click the extension icon, type or paste a claim, click **Open in Claim Verifier**.

## Load unpacked (development)

1. Run the Streamlit app: from `claim-verifier` run `streamlit run app.py`.
2. In Chrome, go to `chrome://extensions/`, enable **Developer mode**, click **Load unpacked**, and select this `extension` folder.
3. Default app URL is `http://localhost:8501`. To use a deployed app, click **Set Claim Verifier URL** in the popup and enter the base URL.

## Options

Use **Set Claim Verifier URL** in the popup (or open extension options) to set the base URL of your Claim Verifier app (e.g. your Streamlit Cloud or Docker deployment).
