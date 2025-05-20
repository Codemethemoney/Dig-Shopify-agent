import os
import json
import logging
from flask import Flask, request, jsonify, session
from dotenv import load_dotenv
import shopify

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

# Shopify API credentials
API_KEY = os.environ.get('SHOPIFY_API_KEY')
API_SECRET = os.environ.get('SHOPIFY_API_SECRET')
SHOP_NAME = os.environ.get('SHOPIFY_DOMAIN')
API_VERSION = '2023-10'
SHOPIFY_ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN')

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
        logger.error(f"Error fetching settings_data.json: {str(e1)}")
        
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
            logger.error(f"Error fetching templates/index.json: {str(e2)}")
            
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
                logger.error(f"Error fetching sections/index.json: {str(e3)}")
                raise Exception(f"Failed to fetch homepage asset: {str(e3)}")

@app.route('/update-homepage', methods=['POST'])
def update_homepage():
    try:
        # Get the new headline from request
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'success': False, 'error': 'Missing required text parameter'}), 400
            
        new_headline = data['text']
        logger.info(f"Received request to update headline to: {new_headline}")
        
        # Get shop and token
        shop, token = get_shop_and_token()
        
        # Get the main theme
        main_theme = get_main_theme(shop, token)
        if not main_theme:
            logger.error("No main theme found")
            return jsonify({'success': False, 'error': 'No main theme found'}), 404
            
        logger.info(f"Found main theme: {main_theme.name} (ID: {main_theme.id})")
        
        # Get homepage asset
        result = get_homepage_asset(shop, token, main_theme.id)
        logger.info(f"Retrieved asset of type: {result['type']}")
        
        # Update headline based on asset type
        if result['type'] == 'settings_data':
            # Update brand_headline in settings_data.json
            content = result['content']
            
            # FIXED CODE: Check if 'current' is a string (preset name) or a dictionary
            if 'current' in content:
                if isinstance(content['current'], str):
                    # If 'current' is a string, we need to update the value in the preset
                    preset_name = content['current']
                    logger.info(f"Current is a string, preset name: {preset_name}")
                    if 'presets' in content and preset_name in content['presets']:
                        logger.info(f"Updating brand_headline in preset: {preset_name}")
                        content['presets'][preset_name]['brand_headline'] = new_headline
                else:
                    # If 'current' is already a dictionary, update directly
                    logger.info("Current is a dictionary, updating brand_headline directly")
                    content['current']['brand_headline'] = new_headline
            else:
                # If neither structure exists, create it
                logger.info("No current field found, creating one")
                content['current'] = {'brand_headline': new_headline}
                
        elif result['type'] == 'templates_index':
            # Update headline in the template sections
            content = result['content']
            updated = False
            for section_id, section in content.get('sections', {}).items():
                if section.get('type') in ['image-banner', 'hero', 'slideshow']:
                    if 'settings' not in section:
                        section['settings'] = {}
                    logger.info(f"Updating heading in section: {section_id}")
                    section['settings']['heading'] = new_headline
                    updated = True
                    break
            
            if not updated:
                logger.warning("No suitable section found to update heading")
                    
        elif result['type'] == 'sections_index':
            # Update headline in the section settings
            content = result['content']
            if 'settings' not in content:
                content['settings'] = {}
            logger.info("Updating heading in sections_index.json")
            content['settings']['heading'] = new_headline
            
        # Save the updated content
        asset = result['asset']
        asset.value = json.dumps(content)
        asset.save()
        logger.info("Asset saved successfully")
        
        return jsonify({'success': True})
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error updating homepage: {error_msg}")
        return jsonify({'success': False, 'error': error_msg}), 500

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
        error_msg = str(e)
        logger.error(f"Error in debug endpoint: {error_msg}")
        return jsonify({'error': error_msg}), 500

@app.route('/update-theme', methods=['POST'])
def update_theme():
    """General-purpose theme update endpoint for various operations"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'operation' not in data:
            return jsonify({'success': False, 'error': 'Missing operation parameter'}), 400
            
        operation = data['operation']
        logger.info(f"Received theme update request, operation: {operation}")
        
        # Handle different operation types
        if operation == 'update_headline':
            # Reuse existing logic
            return update_homepage()
        elif operation == 'update_description':
            # Example for modifying brand description
            if 'text' not in data:
                return jsonify({'success': False, 'error': 'Missing text parameter'}), 400
                
            # Handle description update logic here
            return jsonify({'success': True, 'message': 'Feature not yet implemented'}), 501
        elif operation == 'update_color_scheme':
            # Example for modifying color scheme
            return jsonify({'success': True, 'message': 'Feature not yet implemented'}), 501
        else:
            return jsonify({'success': False, 'error': f'Unknown operation: {operation}'}), 400
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in update-theme endpoint: {error_msg}")
        return jsonify({'success': False, 'error': error_msg}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)