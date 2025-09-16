"""
JSON schema validator for CI Orchestrator output validation.
"""
import json
from typing import Dict, Any, Optional, List
from jsonschema import validate, ValidationError, Draft7Validator
import structlog

logger = structlog.get_logger()

class JSONValidator:
    """Validates CI Orchestrator output against the defined JSON schema."""
    
    def __init__(self, schema_path: str = None):
        self.schema = self._load_schema(schema_path)
        self.validator = Draft7Validator(self.schema) if self.schema else None
    
    def _load_schema(self, schema_path: str = None) -> Optional[Dict[str, Any]]:
        """Load JSON schema from file."""
        try:
            if not schema_path:
                # Use default schema path
                schema_path = "/home/ubuntu/ci_orchestrator/config/output_schema.json"
            
            with open(schema_path, 'r') as f:
                schema = json.load(f)
            
            logger.info(f"Loaded JSON schema from {schema_path}")
            return schema
            
        except Exception as e:
            logger.error(f"Error loading JSON schema: {str(e)}")
            return None
    
    def validate_output(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate output data against schema and return validation result."""
        try:
            if not self.validator:
                return {
                    'valid': False,
                    'errors': ['JSON schema not loaded'],
                    'warnings': []
                }
            
            # Perform validation
            errors = []
            warnings = []
            
            # Collect all validation errors
            for error in self.validator.iter_errors(output_data):
                errors.append(self._format_validation_error(error))
            
            # Check for warnings (non-critical issues)
            warnings = self._check_warnings(output_data)
            
            is_valid = len(errors) == 0
            
            if is_valid:
                logger.info("Output validation successful")
            else:
                logger.warning(f"Output validation failed with {len(errors)} errors")
            
            return {
                'valid': is_valid,
                'errors': errors,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"Error during validation: {str(e)}")
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': []
            }
    
    def _format_validation_error(self, error: ValidationError) -> str:
        """Format validation error for human readability."""
        try:
            path = " -> ".join(str(p) for p in error.absolute_path)
            if path:
                return f"Error at {path}: {error.message}"
            else:
                return f"Error: {error.message}"
        except Exception:
            return str(error.message)
    
    def _check_warnings(self, output_data: Dict[str, Any]) -> List[str]:
        """Check for non-critical warnings in the output data."""
        warnings = []
        
        try:
            # Check for empty sections
            if 'weekly_report' in output_data:
                weekly_report = output_data['weekly_report']
                if isinstance(weekly_report, dict):
                    if not weekly_report.get('engagement_highlights', []):
                        warnings.append("Weekly report has no engagement highlights")
                    if not weekly_report.get('streetwear_trends', []):
                        warnings.append("Weekly report has no streetwear trends")
                    if not weekly_report.get('competitive_mentions', []):
                        warnings.append("Weekly report has no competitive mentions")
            
            if 'cultural_radar' in output_data:
                cultural_radar = output_data['cultural_radar']
                if isinstance(cultural_radar, dict):
                    if not cultural_radar.get('creators', []):
                        warnings.append("Cultural radar has no creators")
                    if not cultural_radar.get('top_3_to_activate', []):
                        warnings.append("Cultural radar has no top 3 to activate")
            
            if 'peer_tracker' in output_data:
                peer_tracker = output_data['peer_tracker']
                if isinstance(peer_tracker, dict):
                    scorecard = peer_tracker.get('scorecard', {})
                    if not scorecard.get('scores', []):
                        warnings.append("Peer tracker has no scores")
                    if not peer_tracker.get('priority_fixes', []):
                        warnings.append("Peer tracker has no priority fixes")
            
            # Check for placeholder data
            output_str = json.dumps(output_data).lower()
            if 'unavailable' in output_str or 'error' in output_str:
                warnings.append("Output contains unavailable or error data")
            
            if 'placeholder' in output_str or 'sample' in output_str:
                warnings.append("Output may contain placeholder data")
            
        except Exception as e:
            logger.error(f"Error checking warnings: {str(e)}")
            warnings.append("Could not check for warnings")
        
        return warnings
    
    def fix_common_issues(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to fix common validation issues."""
        try:
            fixed_data = output_data.copy()
            
            # Ensure required sections exist
            if 'weekly_report' in fixed_data and fixed_data['weekly_report']:
                fixed_data['weekly_report'] = self._fix_weekly_report(fixed_data['weekly_report'])
            
            if 'cultural_radar' in fixed_data and fixed_data['cultural_radar']:
                fixed_data['cultural_radar'] = self._fix_cultural_radar(fixed_data['cultural_radar'])
            
            if 'peer_tracker' in fixed_data and fixed_data['peer_tracker']:
                fixed_data['peer_tracker'] = self._fix_peer_tracker(fixed_data['peer_tracker'])
            
            return fixed_data
            
        except Exception as e:
            logger.error(f"Error fixing common issues: {str(e)}")
            return output_data
    
    def _fix_weekly_report(self, weekly_report: Dict[str, Any]) -> Dict[str, Any]:
        """Fix common issues in weekly report section."""
        try:
            fixed_report = weekly_report.copy()
            
            # Ensure brand_mentions_overview has required fields
            if 'brand_mentions_overview' not in fixed_report:
                fixed_report['brand_mentions_overview'] = {
                    'this_window': 0,
                    'prev_window': 0,
                    'delta_pct': 0.0
                }
            else:
                overview = fixed_report['brand_mentions_overview']
                if 'this_window' not in overview:
                    overview['this_window'] = 0
                if 'prev_window' not in overview:
                    overview['prev_window'] = 0
                if 'delta_pct' not in overview:
                    overview['delta_pct'] = 0.0
            
            # Ensure customer_sentiment has required fields
            if 'customer_sentiment' not in fixed_report:
                fixed_report['customer_sentiment'] = {
                    'positive': 'No positive sentiment data available',
                    'negative': 'No negative sentiment data available',
                    'neutral': 'No neutral sentiment data available'
                }
            
            # Ensure arrays exist
            for field in ['engagement_highlights', 'streetwear_trends', 'competitive_mentions', 'opportunities_risks']:
                if field not in fixed_report:
                    fixed_report[field] = []
            
            return fixed_report
            
        except Exception as e:
            logger.error(f"Error fixing weekly report: {str(e)}")
            return weekly_report
    
    def _fix_cultural_radar(self, cultural_radar: Dict[str, Any]) -> Dict[str, Any]:
        """Fix common issues in cultural radar section."""
        try:
            fixed_radar = cultural_radar.copy()
            
            # Ensure creators array exists
            if 'creators' not in fixed_radar:
                fixed_radar['creators'] = []
            
            # Fix creator objects
            fixed_creators = []
            for creator in fixed_radar.get('creators', []):
                if isinstance(creator, dict):
                    fixed_creator = creator.copy()
                    
                    # Ensure required fields
                    required_fields = {
                        'creator': 'Unknown Creator',
                        'platform': 'Unknown',
                        'profile': '',
                        'followers': 0,
                        'engagement_rate': 0.0,
                        'brand_mentioned': False,
                        'content_focus': 'Unknown',
                        'recommendation': 'monitor',
                        'influence_score': 0
                    }
                    
                    for field, default_value in required_fields.items():
                        if field not in fixed_creator:
                            fixed_creator[field] = default_value
                    
                    # Ensure influence_score is within bounds
                    if not isinstance(fixed_creator['influence_score'], int) or fixed_creator['influence_score'] < 0:
                        fixed_creator['influence_score'] = 0
                    elif fixed_creator['influence_score'] > 100:
                        fixed_creator['influence_score'] = 100
                    
                    fixed_creators.append(fixed_creator)
            
            fixed_radar['creators'] = fixed_creators
            
            # Ensure top_3_to_activate exists
            if 'top_3_to_activate' not in fixed_radar:
                fixed_radar['top_3_to_activate'] = []
            
            return fixed_radar
            
        except Exception as e:
            logger.error(f"Error fixing cultural radar: {str(e)}")
            return cultural_radar
    
    def _fix_peer_tracker(self, peer_tracker: Dict[str, Any]) -> Dict[str, Any]:
        """Fix common issues in peer tracker section."""
        try:
            fixed_tracker = peer_tracker.copy()
            
            # Ensure scorecard exists
            if 'scorecard' not in fixed_tracker:
                fixed_tracker['scorecard'] = {
                    'dimensions': [],
                    'brands': [],
                    'scores': []
                }
            
            # Ensure arrays exist
            for field in ['strengths', 'gaps', 'priority_fixes']:
                if field not in fixed_tracker:
                    fixed_tracker[field] = []
            
            # Fix score objects
            fixed_scores = []
            for score in fixed_tracker['scorecard'].get('scores', []):
                if isinstance(score, dict):
                    fixed_score = score.copy()
                    
                    # Ensure required fields
                    if 'dimension' not in fixed_score:
                        fixed_score['dimension'] = 'Unknown'
                    if 'brand' not in fixed_score:
                        fixed_score['brand'] = 'Unknown'
                    if 'score' not in fixed_score:
                        fixed_score['score'] = 0
                    if 'notes' not in fixed_score:
                        fixed_score['notes'] = []
                    
                    # Ensure score is within bounds
                    if not isinstance(fixed_score['score'], int) or fixed_score['score'] < 0:
                        fixed_score['score'] = 0
                    elif fixed_score['score'] > 10:
                        fixed_score['score'] = 10
                    
                    fixed_scores.append(fixed_score)
            
            fixed_tracker['scorecard']['scores'] = fixed_scores
            
            return fixed_tracker
            
        except Exception as e:
            logger.error(f"Error fixing peer tracker: {str(e)}")
            return peer_tracker
    
    def create_minimal_valid_output(self, mode: str = 'all') -> Dict[str, Any]:
        """Create a minimal valid output structure for testing."""
        output = {}
        
        if mode in ['weekly_report', 'all']:
            output['weekly_report'] = {
                'brand_mentions_overview': {
                    'this_window': 0,
                    'prev_window': 0,
                    'delta_pct': 0.0
                },
                'customer_sentiment': {
                    'positive': 'No data available',
                    'negative': 'No data available',
                    'neutral': 'No data available'
                },
                'engagement_highlights': [],
                'streetwear_trends': [],
                'competitive_mentions': [],
                'opportunities_risks': []
            }
        
        if mode in ['cultural_radar', 'all']:
            output['cultural_radar'] = {
                'creators': [],
                'top_3_to_activate': []
            }
        
        if mode in ['peer_tracker', 'all']:
            output['peer_tracker'] = {
                'scorecard': {
                    'dimensions': [],
                    'brands': [],
                    'scores': []
                },
                'strengths': [],
                'gaps': [],
                'priority_fixes': []
            }
        
        return output

