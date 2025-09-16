"""
Test file for CI Orchestrator functionality.
"""
import asyncio
import json
import pytest
from src.models import CIOrchestratorInput, Brand, Competitor
from src.orchestrator import CIOrchestrator
from src.validators.json_validator import JSONValidator

class TestCIOrchestrator:
    """Test cases for CI Orchestrator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = CIOrchestrator()
        self.validator = JSONValidator()
        
        # Sample input data
        self.sample_input = CIOrchestratorInput(
            brand=Brand(name="Crooks & Castles", url="https://crooksncastles.com"),
            competitors=[
                Competitor(name="Paper Planes", url="https://paperplane.shop"),
                Competitor(name="Stüssy", url="https://stussy.com")
            ],
            mode="all",
            window_days=7
        )
    
    @pytest.mark.asyncio
    async def test_weekly_report_mode(self):
        """Test weekly report mode."""
        input_data = self.sample_input.copy()
        input_data.mode = "weekly_report"
        
        result = await self.orchestrator.run_analysis(input_data)
        
        # Check that result has weekly_report section
        assert hasattr(result, 'weekly_report')
        assert result.weekly_report is not None
        
        # Validate JSON structure
        result_dict = result.dict()
        validation = self.validator.validate_output(result_dict)
        assert validation['valid'], f"Validation errors: {validation['errors']}"
    
    @pytest.mark.asyncio
    async def test_cultural_radar_mode(self):
        """Test cultural radar mode."""
        input_data = self.sample_input.copy()
        input_data.mode = "cultural_radar"
        
        result = await self.orchestrator.run_analysis(input_data)
        
        # Check that result has cultural_radar section
        assert hasattr(result, 'cultural_radar')
        assert result.cultural_radar is not None
        
        # Validate JSON structure
        result_dict = result.dict()
        validation = self.validator.validate_output(result_dict)
        assert validation['valid'], f"Validation errors: {validation['errors']}"
    
    @pytest.mark.asyncio
    async def test_peer_tracker_mode(self):
        """Test peer tracker mode."""
        input_data = self.sample_input.copy()
        input_data.mode = "peer_tracker"
        
        result = await self.orchestrator.run_analysis(input_data)
        
        # Check that result has peer_tracker section
        assert hasattr(result, 'peer_tracker')
        assert result.peer_tracker is not None
        
        # Validate JSON structure
        result_dict = result.dict()
        validation = self.validator.validate_output(result_dict)
        assert validation['valid'], f"Validation errors: {validation['errors']}"
    
    @pytest.mark.asyncio
    async def test_all_mode(self):
        """Test all mode (combined analysis)."""
        result = await self.orchestrator.run_analysis(self.sample_input)
        
        # Check that result has all sections
        assert hasattr(result, 'weekly_report')
        assert hasattr(result, 'cultural_radar')
        assert hasattr(result, 'peer_tracker')
        
        # Validate JSON structure
        result_dict = result.dict()
        validation = self.validator.validate_output(result_dict)
        assert validation['valid'], f"Validation errors: {validation['errors']}"
    
    def test_json_validator(self):
        """Test JSON validator functionality."""
        # Test with minimal valid output
        minimal_output = self.validator.create_minimal_valid_output("all")
        validation = self.validator.validate_output(minimal_output)
        assert validation['valid']
        
        # Test with invalid output
        invalid_output = {"invalid": "structure"}
        validation = self.validator.validate_output(invalid_output)
        assert not validation['valid']
        assert len(validation['errors']) > 0

def run_manual_test():
    """Run a manual test of the CI Orchestrator."""
    async def test_run():
        orchestrator = CIOrchestrator()
        
        # Create test input
        test_input = CIOrchestratorInput(
            brand=Brand(name="Crooks & Castles", url="https://crooksncastles.com"),
            competitors=[
                Competitor(name="Paper Planes", url="https://paperplane.shop"),
                Competitor(name="Stüssy", url="https://stussy.com")
            ],
            mode="all",
            window_days=7
        )
        
        print("Running CI Orchestrator test...")
        result = await orchestrator.run_analysis(test_input)
        
        # Convert to dict and validate
        result_dict = result.dict()
        validator = JSONValidator()
        validation = validator.validate_output(result_dict)
        
        print(f"Validation result: {validation['valid']}")
        if validation['errors']:
            print(f"Errors: {validation['errors']}")
        if validation['warnings']:
            print(f"Warnings: {validation['warnings']}")
        
        # Print formatted JSON output
        print("\nGenerated Output:")
        print(json.dumps(result_dict, indent=2))
        
        return result
    
    # Run the test
    return asyncio.run(test_run())

if __name__ == "__main__":
    # Run manual test
    result = run_manual_test()

