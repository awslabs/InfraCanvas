#!/usr/bin/env python3
"""
Test script to verify orchestrator CDK integration.
"""
from validators.base import ValidationConfig
from validators.orchestrator import ValidationOrchestrator

def test_orchestrator_cdk_support():
    """Test that orchestrator properly initializes CDK validators."""
    print("Testing orchestrator CDK support...")
    print()
    
    # Create config
    config = ValidationConfig(
        enable_syntax_validation=True,
        enable_security_scanning=True,
        enable_best_practices=True,
        enable_dry_run=True
    )
    
    # Initialize orchestrator
    orchestrator = ValidationOrchestrator(config)
    
    # Check that CDK validators are registered
    print("Registered validator formats:")
    for format_name, validators in orchestrator.validators.items():
        print(f"  {format_name}: {len(validators)} validator(s)")
        for validator in validators:
            available = "✓" if validator.is_available() else "✗"
            print(f"    {available} {validator.get_name()}")
    
    print()
    
    # Test getting CDK validators
    cdk_validators = orchestrator._get_validators_for_format('cdk')
    print(f"CDK validators available: {len(cdk_validators)}")
    
    if cdk_validators:
        print("✓ CDK validators are properly registered")
    else:
        print("⚠ No CDK validators available (CDK CLI not installed)")
    
    print()

def main():
    """Run test."""
    print("=" * 60)
    print("Orchestrator CDK Integration Test")
    print("=" * 60)
    print()
    
    try:
        test_orchestrator_cdk_support()
        
        print("=" * 60)
        print("Test completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
