from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

@app.route('/')
def health():
    return {'status': 'healthy', 'service': 'Signal & Scale Backend'}

@app.route('/api/intelligence/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    brand = data['brand']
    competitors = data.get('competitors', [])
    
    return jsonify({
        'success': True,
        'data': {
            'brand_name': brand['name'],
            'industry': brand.get('industry', 'Technology'),
            'kpis': {
                'trend_momentum': 8.7,
                'brand_score': 85,
                'competitors_tracked': len(competitors),
                'sentiment_score': 78,
                'dtc_score': 82
            },
            'cultural_radar': f"Cultural analysis for {brand['name']} shows strong market presence in {brand.get('industry', 'Technology')}...",
            'competitive_playbook': f"Competitive analysis for {brand['name']} indicates leader position...",
            'dtc_audit': f"DTC audit for {brand['name']} shows 82/100 performance score..."
        }
    })
