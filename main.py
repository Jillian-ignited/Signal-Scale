from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
import json

# Import your services
from services.real_competitive_intelligence import RealCompetitiveIntelligence

app = Flask(__name__)

# Enable CORS for all routes
CORS(app, origins=["*"], methods=["GET", "POST", "OPTIONS"], 
     allow_headers=["Content-Type", "Authorization"])

# Initialize the competitive intelligence service
intelligence_service = RealCompetitiveIntelligence()

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'Signal & Scale Backend',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/intelligence/analyze', methods=['POST', 'OPTIONS'])
def analyze_brand():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
    
    try:
        # Get the request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        print(f"Received analysis request: {json.dumps(data, indent=2)}")
        
        # Validate required fields
        if 'brand' not in data:
            return jsonify({
                'success': False,
                'error': 'Brand information is required'
            }), 422
        
        brand = data['brand']
        if 'name' not in brand:
            return jsonify({
                'success': False,
                'error': 'Brand name is required'
            }), 422
        
        # Generate competitive intelligence
        result = intelligence_service.generate_competitive_analysis(data)
        
        print(f"Analysis completed successfully for {brand['name']}")
        return jsonify(result)
        
    except Exception as e:
        print(f"Analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
