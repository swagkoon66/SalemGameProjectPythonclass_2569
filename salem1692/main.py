"""
Salem 1692: Digital Board Game
Entry point for the application
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.app import SalemGameApp

def main():
    """Main entry point for the game"""
    try:
        app = SalemGameApp()
        app.run()
    except Exception as e:
        print(f"Error starting game: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()