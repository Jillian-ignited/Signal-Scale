from flask import Blueprint, request, jsonify
from ..services.real_competitive_intelligence import RealCompetitiveIntelligence
import logging

real_intelligence_bp = Blueprint('real_intelligence', __name__)
intelligence_service = RealCompetitiveIntelligence()

@real_intelligence_bp.route('/api/intelligence/analyze', methods=['POST'])
def analyze_competitive_intelligence():
    """Generate real competitive intelligence analysis"""
    try:
        brand_config = request.get_json()
        print(f"Received brand_config: {brand_config}")
        
        if not brand_config or 'brand' not in brand_config:
            print("Error: Brand configuration missing")
            return jsonify({
                'success': False,
                'error': 'Brand configuration required'
            }), 400
        
        print(f"Starting analysis for brand: {brand_config['brand']['name']}")
        
        # Generate real competitive intelligence
        result = intelligence_service.generate_competitive_analysis(brand_config)
        print(f"Analysis result: {result}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Exception in analyze_competitive_intelligence: {str(e)}")
        import traceback
        traceback.print_exc()
        logging.error(f"Intelligence analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Analysis failed',
            'details': str(e)
        }), 500

@real_intelligence_bp.route('/api/intelligence/website-analysis', methods=['POST'])
def analyze_website():
    """Analyze a specific competitor website"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({
                'success': False,
                'error': 'Website URL required'
            }), 400
        
        analysis = intelligence_service.analyze_website(url)
        
        return jsonify({
            'success': True,
            'data': analysis
        })
        
    except Exception as e:
        logging.error(f"Website analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Website analysis failed',
            'details': str(e)
        }), 500

@real_intelligence_bp.route('/api/intelligence/refresh', methods=['POST'])
def refresh_intelligence():
    """Refresh competitive intelligence data"""
    try:
        brand_config = request.get_json()
        
        # Generate fresh analysis
        result = intelligence_service.generate_competitive_analysis(brand_config)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Intelligence refresh error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Refresh failed',
            'details': str(e)
        }), 500

