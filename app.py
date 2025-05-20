import os
import json
import requests
import certifi
from flask import Flask, request, jsonify, session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

# Get credentials from environment
SHOP_NAME    = os.environ.get('SHOPIFY_DOMAIN')
ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN')
API_VERSION  = '2023-10'


@app.route('/')
def index():
    return "DIG Shopify Agent - Homepage Editor is running!"


def get_main_theme():
    """Get the active theme ID using direct API call"""
    url = f"https://{SHOP_NAME}/admin/api/{API_VERSION}/themes.json"
    headers = {
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    resp = requests.get(
        url,
        headers=headers,
        verify=certifi.where()
    )
    if resp.status_code != 200:
        raise Exception(f"Failed to get themes: {resp.text}")
    themes = resp.json().get('themes', [])
    return next((t for t in themes if t.get('role') == 'main'), None)


def get_asset(theme_id, key):
    """Get an asset from the theme"""
    url = f"https://{SHOP_NAME}/admin/api/{API_VERSION}/themes/{theme_id}/assets.json"
    params = {"asset[key]": key}
    headers = {
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    resp = requests.get(
        url,
        headers=headers,
        params=params,
        verify=certifi.where()
    )
    if resp.status_code != 200:
        raise Exception(f"Failed to get asset {key}: {resp.text}")
    return resp.json().get('asset', {})


def update_asset(theme_id, key, value):
    """Update an asset in the theme"""
    url = f"https://{SHOP_NAME}/admin/api/{API_VERSION}/themes/{theme_id}/assets.json"
    headers = {
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    data = {
        "asset": {
            "key": key,
            "value": value
        }
    }
    resp = requests.put(
        url,
        headers=headers,
        json=data,
        verify=certifi.where()
    )
    if resp.status_code != 200:
        raise Exception(f"Failed to update asset {key}: {resp.text}")
    return resp.json().get('asset', {})


@app.route('/update-homepage', methods=['POST'])
def update_homepage():
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'success': False, 'error': 'Missing required text parameter'}), 400

        new_headline = data['text']
        main_theme = get_main_theme()
        if not main_theme:
            return jsonify({'success': False, 'error': 'No main theme found'}), 404
        theme_id = main_theme.get('id')

        asset = get_asset(theme_id, 'config/settings_data.json')
        if not asset or 'value' not in asset:
            return jsonify({'success': False, 'error': 'Failed to get settings_data.json'}), 500

        content = json.loads(asset['value'])
        if 'current' in content:
            if isinstance(content['current'], str):
                preset = content['current']
                if 'presets' in content and preset in content['presets']:
                    content['presets'][preset]['brand_headline'] = new_headline
            else:
                content['current']['brand_headline'] = new_headline
        else:
            content['current'] = {'brand_headline': new_headline}

        update_asset(theme_id, 'config/settings_data.json', json.dumps(content))
        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/debug-settings', methods=['GET'])
def debug_settings():
    """A debug route to inspect theme settings and structure"""
    try:
        main_theme = get_main_theme()
        if not main_theme:
            return jsonify({'error': 'No main theme found'}), 404
        theme_id = main_theme.get('id')

        url = f"https://{SHOP_NAME}/admin/api/{API_VERSION}/themes/{theme_id}/assets.json"
        headers = {
            "X-Shopify-Access-Token": ACCESS_TOKEN,
            "Content-Type": "application/json"
        }
        resp = requests.get(
            url,
            headers=headers,
            verify=certifi.where()
        )
        if resp.status_code != 200:
            raise Exception(f"Failed to get assets: {resp.text}")
        assets = resp.json().get('assets', [])

        debug_info = {
            'theme_info': {
                'id': theme_id,
                'name': main_theme.get('name'),
                'role': main_theme.get('role')
            },
            'available_assets': [a.get('key') for a in assets if a.get('key', '').endswith('.json')]
        }

        for path in ['config/settings_data.json', 'templates/index.json', 'sections/index.json']:
            try:
                a = get_asset(theme_id, path)
                debug_info[path] = {
                    'exists': True,
                    'sample': json.loads(a.get('value', '{}'))
                }
            except:
                debug_info[path] = {'exists': False}

        return jsonify(debug_info)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)