from flask import Flask, request, jsonify
import requests
import os
import urllib3

# Disable SSL warnings for Shopify connections
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

SHOP_URL = os.getenv("SHOPIFY_DOMAIN")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

HEADERS = {
    'X-Shopify-Access-Token': ACCESS_TOKEN,
    'Content-Type': 'application/json'
}

@app.route('/', methods=['GET'])
def home():
    return "DIG CLOTHING CO. Agent Active", 200

@app.route('/update-homepage', methods=['POST'])
def update_homepage():
    data = request.json
    new_text = data.get('text', '')

    try:
        # 1. Get the active theme ID
        themes_resp = requests.get(
            f"https://{SHOP_URL}/admin/api/2024-01/themes.json",
            headers=HEADERS,
            verify=False
        )
        if themes_resp.status_code != 200:
            return jsonify({"error": "Theme fetch failed", "details": themes_resp.text}), themes_resp.status_code

        themes = themes_resp.json()
        main_theme = [t for t in themes['themes'] if t['role'] == 'main'][0]
        theme_id = main_theme['id']

        # 2. Fetch the settings_data.json file
        config_resp = requests.get(
            f"https://{SHOP_URL}/admin/api/2024-01/themes/{theme_id}/assets.json?asset[key]=config/settings_data.json",
            headers=HEADERS,
            verify=False
        )
        if config_resp.status_code != 200:
            return jsonify({"error": "Could not fetch settings_data.json", "details": config_resp.text}), config_resp.status_code

        settings_data = config_resp.json()['asset']['value']

        # 3. Convert JSON string to dict
        import json
        settings_obj = json.loads(settings_data)

        # 4. Replace brand_headline value
        settings_obj["presets"]["Default"]["brand_headline"] = new_text

        # 5. Convert back to JSON string
        updated_settings = json.dumps(settings_obj)

        # 6. Push the update
        update_resp = requests.put(
            f"https://{SHOP_URL}/admin/api/2024-01/themes/{theme_id}/assets.json",
            headers=HEADERS,
            json={
                "asset": {
                    "key": "config/settings_data.json",
                    "value": updated_settings
                }
            },
            verify=False
        )

        if update_resp.status_code == 200:
            return jsonify({"status": "Homepage headline updated to:", "headline": new_text}), 200
        else:
            return jsonify({"error": "Failed to update headline", "details": update_resp.text}), update_resp.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# For Render hosting
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
