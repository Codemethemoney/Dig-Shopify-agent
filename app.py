from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

SHOP_URL = os.getenv("SHOPIFY_DOMAIN")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
HEADERS = {
    'X-Shopify-Access-Token': ACCESS_TOKEN,
    'Content-Type': 'application/json'
}

@app.route('/update-homepage', methods=['POST'])
def update_homepage():
    data = request.json
    new_text = data.get('text', '')

    # Get current theme ID
    themes = requests.get(f"https://{SHOP_URL}/admin/api/2024-01/themes.json", headers=HEADERS).json()
    main_theme = [t for t in themes['themes'] if t['role'] == 'main'][0]
    theme_id = main_theme['id']

    # Get homepage layout (index.json)
    asset = requests.get(f"https://{SHOP_URL}/admin/api/2024-01/themes/{theme_id}/assets.json?asset[key]=sections/index.json", headers=HEADERS).json()
    homepage = asset['asset']['value']

    # Replace welcome message with new text
    updated_homepage = homepage.replace("Welcome to our store", new_text)

    # Push the update
    resp = requests.put(
        f"https://{SHOP_URL}/admin/api/2024-01/themes/{theme_id}/assets.json",
        headers=HEADERS,
        json={
            "asset": {
                "key": "sections/index.json",
                "value": updated_homepage
            }
        }
    )
    return jsonify({"status": "updated"}), resp.status_code

@app.route('/', methods=['GET'])
def root():
    return "DIG CLOTHING CO. Agent Active", 200

if __name__ == '__main__':
    app.run(debug=True)
