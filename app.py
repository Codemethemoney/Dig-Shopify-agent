from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Get environment variables
SHOP_URL = os.getenv("SHOPIFY_DOMAIN")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

HEADERS = {
    'X-Shopify-Access-Token': ACCESS_TOKEN,
    'Content-Type': 'application/json'
}

# Root route for status check
@app.route('/', methods=['GET'])
def home():
    return "DIG CLOTHING CO. Agent Active", 200

# Route to update homepage headline
@app.route('/update-homepage', methods=['POST'])
def update_homepage():
    data = request.json
    new_text = data.get('text', '')

    try:
        # Get current theme ID
        themes_resp = requests.get(f"https://{SHOP_URL}/admin/api/2024-01/themes.json", headers=HEADERS)
        themes = themes_resp.json()
        main_theme = [t for t in themes['themes'] if t['role'] == 'main'][0]
        theme_id = main_theme['id']

        # Get current homepage layout (index.json)
        asset_resp = requests.get(
            f"https://{SHOP_URL}/admin/api/2024-01/themes/{theme_id}/assets.json?asset[key]=sections/index.json",
            headers=HEADERS
        )
        homepage_data = asset_resp.json()
        homepage = homepage_data['asset']['value']

        # Replace placeholder text
        updated_homepage = homepage.replace("Welcome to our store", new_text)

        # Upload updated homepage content
        update_resp = requests.put(
            f"https://{SHOP_URL}/admin/api/2024-01/themes/{theme_id}/assets.json",
            headers=HEADERS,
            json={
                "asset": {
                    "key": "sections/index.json",
                    "value": updated_homepage
                }
            }
        )

        if update_resp.status_code == 200:
            return jsonify({"status": "Homepage updated successfully."}), 200
        else:
            return jsonify({"error": "Failed to update homepage."}), update_resp.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Port binding for Render
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
