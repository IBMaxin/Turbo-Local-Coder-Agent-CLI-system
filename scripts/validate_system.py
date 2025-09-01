#!/usr/bin/env python3
"""
System validation script for Turbo Local Coder Agent
Tests all components and provides diagnostic information.
"""

import json
import sys
from pathlib import Path

def test_configuration():
    """Test configuration loading."""
    print("=== Testing Configuration ===")
    try:
        from agent.core.config import load_settings
        settings = load_settings()
        print(f"✓ Configuration loaded successfully")
        print(f"  - Turbo Host: {settings.turbo_host}")
        print(f"  - Local Host: {settings.local_host}")
        print(f"  - Planner Model: {settings.planner_model}")
        print(f"  - Coder Model: {settings.coder_model}")
        print(f"  - Max Steps: {settings.max_steps}")
        print(f"  - API Key: {'Set' if settings.api_key else 'Missing'}")
        return True
    except Exception as e:
        print(f"✗ Configuration failed: {e}")
        return False

def test_tools():
    """Test all tools individually."""
    print("\n=== Testing Tools ===")
    success = True
    
    # Test fs tools
    try:
        from agent.tools.fs import fs_write, fs_read, fs_list
        
        # Test write
        result = fs_write("test_validation.txt", "Hello from validation!")
        if result.ok:
            print("✓ fs_write working")
        else:
            print(f"✗ fs_write failed: {result.detail}")
            success = False
            
        # Test read
        result = fs_read("test_validation.txt")
        if result.ok and "validation" in result.detail:
            print("✓ fs_read working")
        else:
            print(f"✗ fs_read failed: {result.detail}")
            success = False
            
        # Test list
        result = fs_list(".")
        if result.ok:
            print("✓ fs_list working")
        else:
            print(f"✗ fs_list failed: {result.detail}")
            success = False
            
    except Exception as e:
        print(f"✗ File system tools failed: {e}")
        success = False
    
    # Test shell tool
    try:
        from agent.tools.shell import shell_run
        result = shell_run("echo 'Shell test'")
        if result.ok and "Shell test" in result.stdout:
            print("✓ shell_run working")
        else:
            print(f"✗ shell_run failed: {result}")
            success = False
    except Exception as e:
        print(f"✗ Shell tool failed: {e}")
        success = False
    
    # Test python tool
    try:
        from agent.tools.python_exec import python_run
        result = python_run("snippet", "print('Python test')")
        if result.ok and "Python test" in result.stdout:
            print("✓ python_run snippet working")
        else:
            print(f"✗ python_run snippet failed: {result}")
            success = False
            
        # Test pytest (may fail if no tests, but shouldn't crash)
        result = python_run("pytest")
        print(f"✓ python_run pytest accessible (exit code: {result.code})")
    except Exception as e:
        print(f"✗ Python tool failed: {e}")
        success = False
    
    return success

def test_planner():
    """Test planner connectivity."""
    print("\n=== Testing Planner ===")
    try:
        from agent.core.planner import get_plan
        plan = get_plan("Create a simple hello function", None)
        if plan.plan and plan.coder_prompt:
            print("✓ Planner working")
            print(f"  - Generated {len(plan.plan)} steps")
            print(f"  - Coder prompt length: {len(plan.coder_prompt)} chars")
            return True
        else:
            print("✗ Planner returned empty results")
            return False
    except Exception as e:
        print(f"✗ Planner failed: {e}")
        return False

def test_network_connectivity():
    """Test network connectivity to required services."""
    print("\n=== Testing Network Connectivity ===")
    import httpx
    success = True
    
    try:
        from agent.core.config import load_settings
        settings = load_settings()
        
        # Test remote endpoint
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(f"{settings.turbo_host}/")
                print(f"✓ Remote host reachable: {settings.turbo_host}")
        except Exception as e:
            print(f"✗ Remote host unreachable: {e}")
            success = False
            
        # Test local endpoint  
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{settings.local_host}/api/tags")
                print(f"✓ Local Ollama reachable: {settings.local_host}")
        except Exception as e:
            print(f"✗ Local Ollama unreachable: {e}")
            print("  Make sure Ollama is running: ollama serve")
            success = False
            
    except Exception as e:
        print(f"✗ Network test failed: {e}")
        success = False
        
    return success

def test_models():
    """Test model availability."""
    print("\n=== Testing Model Availability ===")
    import httpx
    success = True
    
    try:
        from agent.core.config import load_settings
        settings = load_settings()
        
        # Check local models
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(f"{settings.local_host}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    model_names = [m["name"] for m in models]
                    # Check if the model exists (handle :latest suffix)
                    model_found = False
                    for available_model in model_names:
                        if (settings.coder_model == available_model or 
                            settings.coder_model == available_model.replace(':latest', '') or
                            settings.coder_model + ':latest' == available_model):
                            model_found = True
                            break
                    
                    if model_found:
                        print(f"✓ Local coder model available: {settings.coder_model}")
                    else:
                        print(f"✗ Local coder model missing: {settings.coder_model}")
                        print(f"  Available: {model_names}")
                        success = False
                else:
                    print("✗ Could not check local models")
                    success = False
        except Exception as e:
            print(f"✗ Local model check failed: {e}")
            success = False
            
    except Exception as e:
        print(f"✗ Model availability test failed: {e}")
        success = False
        
    return success

def cleanup():
    """Clean up test files."""
    test_file = Path("test_validation.txt")
    if test_file.exists():
        test_file.unlink()

def main():
    """Run all validation tests."""
    print("Turbo Local Coder Agent - System Validation")
    print("=" * 50)
    
    tests = [
        ("Configuration", test_configuration),
        ("Tools", test_tools),
        ("Network Connectivity", test_network_connectivity), 
        ("Model Availability", test_models),
        ("Planner", test_planner),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    cleanup()
    
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} {test_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All systems operational!")
        print("The Turbo Local Coder Agent is ready for use.")
    else:
        print("\n⚠️  Some systems have issues.")
        print("Check the error messages above and refer to TROUBLESHOOTING.md")
        
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())