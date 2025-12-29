"""Simple validation script to check if the upgraded GUI setup is working."""

import sys
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are installed."""
    print("Checking dependencies...")
    
    required = [
        "streamlit",
        "pandas",
        "numpy",
        "plotly",
        "scipy",
        "openai",
        "dotenv",
    ]
    
    missing = []
    for pkg in required:
        try:
            if pkg == "dotenv":
                __import__("dotenv")
            else:
                __import__(pkg)
            print(f"  ✓ {pkg}")
        except ImportError:
            print(f"  ✗ {pkg} - MISSING")
            missing.append(pkg)
    
    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("\n✓ All dependencies installed")
    return True


def check_files():
    """Check if all new files exist."""
    print("\nChecking new files...")
    
    gui_dir = Path(__file__).parent
    
    files = [
        "arrival_rate_fitting.py",
        "config_ui.py",
        "async_runner.py",
        "ai_agent.py",
        "data_manager.py",
    ]
    
    missing = []
    for filename in files:
        filepath = gui_dir / filename
        if filepath.exists():
            print(f"  ✓ {filename}")
        else:
            print(f"  ✗ {filename} - MISSING")
            missing.append(filename)
    
    if missing:
        print(f"\n❌ Missing files: {', '.join(missing)}")
        return False
    
    print("\n✓ All new files present")
    return True


def check_env_file():
    """Check if .env file exists and has OPENAI_API_KEY."""
    print("\nChecking .env file...")
    
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"
    
    if not env_file.exists():
        print("  ⚠ .env file not found")
        print("  Create .env file with: OPENAI_API_KEY=your_api_key_here")
        return False
    
    print("  ✓ .env file exists")
    
    # Check if it has the API key (without revealing it)
    try:
        with open(env_file, 'r') as f:
            content = f.read()
            if "OPENAI_API_KEY" in content:
                print("  ✓ OPENAI_API_KEY found in .env")
                return True
            else:
                print("  ⚠ OPENAI_API_KEY not found in .env")
                print("  Add: OPENAI_API_KEY=your_api_key_here")
                return False
    except Exception as e:
        print(f"  ✗ Error reading .env: {e}")
        return False


def check_base_config():
    """Check if base configuration file exists."""
    print("\nChecking base configuration...")
    
    experiments_dir = Path(__file__).parent.parent / "experiments"
    config_file = experiments_dir / "comal_recipes.json"
    
    if not config_file.exists():
        print("  ✗ comal_recipes.json not found")
        return False
    
    print("  ✓ comal_recipes.json found")
    return True


def check_syntax():
    """Check if Python files have valid syntax."""
    print("\nChecking Python syntax...")
    
    gui_dir = Path(__file__).parent
    
    files = [
        "arrival_rate_fitting.py",
        "config_ui.py",
        "async_runner.py",
        "ai_agent.py",
        "data_manager.py",
        "app.py",
    ]
    
    for filename in files:
        filepath = gui_dir / filename
        try:
            with open(filepath, 'r') as f:
                compile(f.read(), filename, 'exec')
            print(f"  ✓ {filename}")
        except SyntaxError as e:
            print(f"  ✗ {filename} - Syntax error at line {e.lineno}")
            return False
        except Exception as e:
            print(f"  ✗ {filename} - {e}")
            return False
    
    print("\n✓ All files have valid syntax")
    return True


def main():
    """Run all validation checks."""
    print("=" * 60)
    print("RESTAURANT SIMULATION UI - SETUP VALIDATION")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(("Dependencies", check_dependencies()))
    results.append(("Files", check_files()))
    results.append(("Syntax", check_syntax()))
    results.append(("Base Config", check_base_config()))
    results.append(("Environment", check_env_file()))
    
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL" if result is False else "⚠ WARN"
        print(f"{status:10s} {name}")
    
    all_passed = all(r is not False for _, r in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ SETUP VALIDATION PASSED")
        print("\nYou can now run the app with:")
        print("  streamlit run gui/app.py")
    else:
        print("✗ SETUP VALIDATION FAILED")
        print("\nPlease fix the issues above before running the app")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

