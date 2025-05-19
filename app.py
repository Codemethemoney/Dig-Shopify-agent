from flask import Flask, request, jsonify
import requests
import os
import urllib3

# Disable SSL warnings (safe if only talking to Shopify)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Get your Shopify credentials from environment variables
SHOP_URL = os.getenv("SHOPIFY_DOMAIN")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

# Standard request headers
HEADERS = {
    'X-Shopify-Access-Token': ACCESS_TOKEN,
    'Content-Type': 'application/json'
}

# Health check route
@app.route('/', methods=['GET'])
def home():
    return "DIG CLOTHING CO. Agent Active", 200

# Endpoint to update homepage slogan
@app.route('/update-homepage', methods=['POST'])
def update_homepage():
    data = request.json
    new_text = data.get('text', '')

    try:
        # Step 1: Get theme list
        themes_resp = requests.get(
            f"https://{SHOP_URL}/admin/api/2024-01/themes.json",
            headers=HEADERS,
            verify=False
        )
        if themes_resp.status_code != 200:
            return jsonify({
                "error": "Failed to fetch themes",
                "status_code": themes_resp.status_code,
                "response": themes_resp.text
            }), themes_resp.status_code

        themes = themes_resp.json()
        main_theme = [t for t in themes['themes'] if t['role'] == 'main'][0]
        theme_id = main_theme['id']

        # Step 2: Get current homepage layout
        asset_resp = requests.get(
            f"https://{SHOP_URL}/admin/api/2024-01/themes/{theme_id}/assets.json?asset[key]=sections/index.json",
            headers=HEADERS,
            verify=False
        )
        if asset_resp.status_code != 200:
            return jsonify({
                "error": "Failed to fetch homepage asset",
                "status_code": asset_resp.status_code,
                "response": asset_resp.text
            }), asset_resp.status_code

        homepage_data = asset_resp.json()
        homepage_content = homepage_data['asset']['value']

        # Step 3: Replace default text
        updated_content = homepage_content.replace("Welcome to our store", new_text)

        # Step 4: Push updated layout
        update_resp = requests.put(
            f"https://{SHOP_URL}/admin/api/2024-01/themes/{theme_id}/assets.json",
            headers=HEADERS,
            json={
                "asset": {
                    "key": "sections/index.json",
                    "value": updated_content
                }
            },
            verify=False
        )
        if update_resp.status_code == 200:
            return jsonify({"status": "Homepage updated successfully."}), 200
        else:
            return jsonify({
                "error": "Failed to upload updated layout",
                "status_code": update_resp.status_code,
                "response": update_resp.text
            }), update_resp.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Start the server for Render deployment
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
