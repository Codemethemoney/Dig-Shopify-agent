import os
import json
import requests
from flask import Flask, request, jsonify, session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

# Get credentials from environment
SHOP_NAME = os.environ.get('SHOPIFY_DOMAIN')
ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN')
API_VERSION = '2023-10'

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
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to get themes: {response.text}")
        
    themes = response.json().get('themes', [])
    main_theme = next((theme for theme in themes if theme.get('role') == 'main'), None)
    return main_theme

def get_asset(theme_id, key):
    """Get an asset from the theme"""
    url = f"https://{SHOP_NAME}/admin/api/{API_VERSION}/themes/{theme_id}/assets.json"
    params = {"asset[key]": key}
    headers = {
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise Exception(f"Failed to get asset {key}: {response.text}")
        
    return response.json().get('asset', {})

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
    
    response = requests.put(url, headers=headers, json=data)
    if response.status_code != 200:
        raise Exception(f"Failed to update asset {key}: {response.text}")
        
    return response.json().get('asset', {})

@app.route('/update-homepage', methods=['POST'])
def update_homepage():
    try:
        # Get the new headline from request
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'success': False, 'error': 'Missing required text parameter'}), 400
            
        new_headline = data['text']
        print(f"Received request to update headline to: {new_headline}")
        
        # Get the main theme
        main_theme = get_main_theme()
        if not main_theme:
            return jsonify({'success': False, 'error': 'No main theme found'}), 404
            
        theme_id = main_theme.get('id')
        print(f"Found main theme: {main_theme.get('name')} (ID: {theme_id})")
        
        # Get settings_data.json
        asset = get_asset(theme_id, 'config/settings_data.json')
        if not asset or 'value' not in asset:
            return jsonify({'success': False, 'error': 'Failed to get settings_data.json'}), 500
            
        # Parse the content
        content = json.loads(asset['value'])
        
        # Check the structure of settings_data.json
        if 'current' in content:
            if isinstance(content['current'], str):
                # 'current' is a string, update the preset
                preset_name = content['current']
                print(f"Current is a string, preset name: {preset_name}")
                if 'presets' in content and preset_name in content['presets']:
                    print(f"Updating brand_headline in preset: {preset_name}")
                    content['presets'][preset_name]['brand_headline'] = new_headline
            else:
                # 'current' is a dictionary, update directly
                print("Current is a dictionary, updating brand_headline directly")
                content['current']['brand_headline'] = new_headline
        else:
            # Neither structure exists, create it
            print("No current field found, creating one")
            content['current'] = {'brand_headline': new_headline}
            
        # Update the asset
        update_asset(theme_id, 'config/settings_data.json', json.dumps(content))
        print("Asset saved successfully")
        
        return jsonify({'success': True})
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error updating homepage: {error_msg}")
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/debug-settings', methods=['GET'])
def debug_settings():
    """A debug route to inspect theme settings and structure"""
    try:
        main_theme = get_main_theme()
        
        if not main_theme:
            return jsonify({'error': 'No main theme found'}), 404
            
        theme_id = main_theme.get('id')
        
        # Get theme assets list
        url = f"https://{SHOP_NAME}/admin/api/{API_VERSION}/themes/{theme_id}/assets.json"
        headers = {
            "X-Shopify-Access-Token": ACCESS_TOKEN,
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to get assets: {response.text}")
            
        assets = response.json().get('assets', [])
        
        debug_info = {
            'theme_info': {
                'id': theme_id,
                'name': main_theme.get('name'),
                'role': main_theme.get('role')
            },
            'available_assets': [asset.get('key') for asset in assets if '.json' in asset.get('key', '')]
        }
        
        # Check specific files
        paths = [
            'config/settings_data.json',
            'templates/index.json',
            'sections/index.json'
        ]
        
        for path in paths:
            try:
                asset = get_asset(theme_id, path)
                if 'value' in asset:
                    path_key = path.replace('/', '_').replace('.', '_')
                    debug_info[path_key] = {
                        'exists': True,
                        'sample': json.loads(asset['value'])
                    }
            except:
                path_key = path.replace('/', '_').replace('.', '_')
                debug_info[path_key] = {
                    'exists': False
                }
        
        return jsonify(debug_info)
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error in debug endpoint: {error_msg}")
        return jsonify({'error': error_msg}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)