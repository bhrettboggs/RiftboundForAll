"""
Setup Script for Accessible Blackjack Web Interface
This will check your file structure and help you set it up correctly.
"""

import os
import sys

def setup_project():
    print("="*60)
    print("🎰 Accessible Blackjack - Setup Helper")
    print("="*60)
    print()
    
    # Check current directory
    current_dir = os.getcwd()
    print(f"📁 Current directory: {current_dir}")
    print()
    
    # List files in current directory
    files = os.listdir(current_dir)
    print("📋 Files in current directory:")
    for f in files:
        if os.path.isfile(f):
            print(f"   ✓ {f}")
    print()
    
    # Check for required original files
    print("🔍 Checking for original game files...")
    required_original = ['blackjack_logic.py', 'card_detection.py', 'tts_module.py']
    missing_original = []
    
    for file in required_original:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} - MISSING!")
            missing_original.append(file)
    print()
    
    if missing_original:
        print("⚠️  You need these original files first!")
        print("   Make sure you're in the correct directory.")
        return False
    
    # Check for web files
    print("🔍 Checking for web interface files...")
    web_files = {
        'web_app.py': 'Main Flask server',
        'requirements_web.txt': 'Python dependencies',
        'start_web_game.py': 'This launcher script'
    }
    
    missing_web = []
    for file, description in web_files.items():
        if os.path.exists(file):
            print(f"   ✅ {file} - {description}")
        else:
            print(f"   ❌ {file} - {description}")
            missing_web.append(file)
    print()
    
    # Check/create templates folder
    print("🔍 Checking templates folder...")
    if not os.path.exists('templates'):
        print("   📁 Creating templates folder...")
        try:
            os.makedirs('templates')
            print("   ✅ templates/ folder created!")
        except Exception as e:
            print(f"   ❌ Error creating folder: {e}")
            return False
    else:
        print("   ✅ templates/ folder exists")
    
    # Check for HTML file
    html_in_root = os.path.exists('blackjack.html')
    html_in_templates = os.path.exists('templates/blackjack.html')
    
    if html_in_templates:
        print("   ✅ templates/blackjack.html exists")
    elif html_in_root:
        print("   📦 Found blackjack.html in root folder")
        print("   📦 Moving it to templates/...")
        try:
            os.rename('blackjack.html', 'templates/blackjack.html')
            print("   ✅ Moved to templates/blackjack.html")
        except Exception as e:
            print(f"   ❌ Error moving file: {e}")
            return False
    else:
        print("   ❌ blackjack.html not found!")
        print()
        print("   💡 You need to create templates/blackjack.html")
        print("   💡 Copy the HTML code into: templates/blackjack.html")
        return False
    
    print()
    print("="*60)
    print("✅ Setup Complete!")
    print("="*60)
    print()
    print("📁 Your project structure:")
    print()
    print("   your-project/")
    print("   ├── blackjack_logic.py")
    print("   ├── card_detection.py")
    print("   ├── tts_module.py")
    print("   ├── web_app.py")
    print("   ├── start_web_game.py")
    print("   └── templates/")
    print("       └── blackjack.html")
    print()
    print("🚀 Ready to run!")
    print()
    print("   Next steps:")
    print("   1. Install dependencies: pip install -r requirements_web.txt")
    print("   2. Run the game: python start_web_game.py")
    print("   3. Open browser: http://localhost:5000")
    print()
    
    return True

if __name__ == "__main__":
    try:
        success = setup_project()
        if not success:
            print()
            print("⚠️  Setup incomplete. Please fix the issues above.")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        sys.exit(1)