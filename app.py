import os
import json
import shopify
from flask import Flask, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

# Shopify API credentials
API_KEY = '8622868c827cd8a022509cf274b9e0ab'
API_SECRET = '7e657964344db9c2470e102bc8a5567e'
SHOP_NAME = 'digclothingko.myshopify.com'
API_VERSION = '2023-10'
SHOPIFY_ACCESS_TOKEN = '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'

# Initialize Shopify API
shopify.Session.setup(api_key=API_KEY, secret=API_SECRET)

@app.route('/')
def index():
    return "DIG Shopify Agent - Homepage Editor is running!"

def get_shop_and_token():
    """Helper function to get shop name and access token from session"""
    shop = session.get('shop', SHOP_NAME)
    token = session.get('access_token')
    
    if not token:
        # For simplicity, using a predefined token
        token = SHOPIFY_ACCESS_TOKEN
        session['access_token'] = token
        
    return shop, token

def get_shopify_session(shop, token):
    """Create and activate a Shopify session"""
    shopify_session = shopify.Session(shop, API_VERSION, token)
    shopify.ShopifyResource.activate_session(shopify_session)
    return shopify_session

def get_main_theme(shop, token):
    """Get the active theme ID"""
    get_shopify_session(shop, token)
    themes = shopify.Theme.find()
    main_theme = next((theme for theme in themes if theme.role == 'main'), None)
    return main_theme

def get_homepage_asset(shop, token, theme_id):
    """Fetch homepage asset with fallback mechanism"""
    get_shopify_session(shop, token)
    
    # First attempt: Modern themes - config/settings_data.json
    try:
        asset = shopify.Asset.find('config/settings_data.json', theme_id=theme_id)
        content = json.loads(asset.value)
        return {
            'type': 'settings_data',
            'asset': asset,
            'content': content
        }
    except Exception as e1:
        print(f"Error fetching settings_data.json: {str(e1)}")
        
        # Second attempt: Try templates/index.json (OS 2.0)
        try:
            asset = shopify.Asset.find('templates/index.json', theme_id=theme_id)
            content = json.loads(asset.value)
            return {
                'type': 'templates_index',
                'asset': asset,
                'content': content
            }
        except Exception as e2:
            print(f"Error fetching templates/index.json: {str(e2)}")
            
            # Third attempt: sections/index.json (legacy)
            try:
                asset = shopify.Asset.find('sections/index.json', theme_id=theme_id)
                content = json.loads(asset.value)
                return {
                    'type': 'sections_index',
                    'asset': asset,
                    'content': content
                }
            except Exception as e3:
                print(f"Error fetching sections/index.json: {str(e3)}")
                raise Exception(f"Failed to fetch homepage asset: {str(e3)}")

@app.route('/update-homepage', methods=['POST'])
def update_homepage():
    try:
        # Get the new headline from request
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'success': False, 'error': 'Missing required text parameter'}), 400
            
        new_headline = data['text']
        
        # Get shop and token
        shop, token = get_shop_and_token()
        
        # Get the main theme
        main_theme = get_main_theme(shop, token)
        if not main_theme:
            return jsonify({'success': False, 'error': 'No main theme found'}), 404
            
        # Get homepage asset
        result = get_homepage_asset(shop, token, main_theme.id)
        
        # Update headline based on asset type
        if result['type'] == 'settings_data':
            # Update brand_headline in settings_data.json
            content = result['content']
            if 'current' in content and 'brand_headline' in content['current']:
                content['current']['brand_headline'] = new_headline
            else:
                # If the structure is different, add brand_headline to current
                if 'current' not in content:
                    content['current'] = {}
                content['current']['brand_headline'] = new_headline
                
        elif result['type'] == 'templates_index':
            # Update headline in the template sections
            content = result['content']
            for section_id, section in content.get('sections', {}).items():
                if section.get('type') in ['image-banner', 'hero', 'slideshow']:
                    if 'settings' not in section:
                        section['settings'] = {}
                    section['settings']['heading'] = new_headline
                    break
                    
        elif result['type'] == 'sections_index':
            # Update headline in the section settings
            content = result['content']
            if 'settings' not in content:
                content['settings'] = {}
            content['settings']['heading'] = new_headline
            
        # Save the updated content
        asset = result['asset']
        asset.value = json.dumps(content)
        asset.save()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error updating homepage: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/debug-settings', methods=['GET'])
def debug_settings():
    """A debug route to inspect theme settings and structure"""
    try:
        shop, token = get_shop_and_token()
        main_theme = get_main_theme(shop, token)
        
        if not main_theme:
            return jsonify({'error': 'No main theme found'}), 404
            
        debug_info = {
            'theme_info': {
                'id': main_theme.id,
                'name': main_theme.name,
                'role': main_theme.role
            },
            'available_assets': [],
            'settings_data': None,
            'templates_index': None,
            'sections_index': None
        }
        
        # Get theme assets
        get_shopify_session(shop, token)
        assets = shopify.Asset.find(theme_id=main_theme.id)
        debug_info['available_assets'] = [asset.key for asset in assets if 
                                       'json' in asset.key or 
                                       'index' in asset.key or 
                                       'config' in asset.key]
        
        # Check specific files
        paths = [
            'config/settings_data.json',
            'templates/index.json',
            'sections/index.json'
        ]
        
        for path in paths:
            try:
                asset = shopify.Asset.find(path, theme_id=main_theme.id)
                path_key = path.replace('/', '_').replace('.', '_')
                debug_info[path_key] = {
                    'exists': True,
                    'sample': json.loads(asset.value)
                }
            except:
                debug_info[path_key] = {
                    'exists': False
                }
        
        return jsonify(debug_info)
        
    except Exception as e:
        print(f"Error in debug endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))