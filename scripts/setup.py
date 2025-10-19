#!/usr/bin/env python3
"""
Setup script for the NATGAS TRADER

This script helps set up the environment and configuration.
"""

import os
import sys
import subprocess

def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e}")
        return False

def create_config_file():
    """Create config.env file from template"""
    if os.path.exists('config/config.env'):
        print("config.env file already exists, skipping creation")
        return True
    
    if os.path.exists('config/env_example.txt'):
        try:
            with open('config/env_example.txt', 'r') as src:
                content = src.read()
            
            with open('config/config.env', 'w') as dst:
                dst.write(content)
            
            print("config.env file created from template")
            print("Please edit config/config.env file with your API keys")
            return True
        except Exception as e:
            print(f"Failed to create config.env file: {e}")
            return False
    else:
        print("env_example.txt not found, creating basic config.env file")
        try:
            with open('config/config.env', 'w') as f:
                f.write("# NATGAS TRADER Configuration\n")
                f.write("ALPACA_API_KEY=your_alpaca_api_key_here\n")
                f.write("ALPACA_SECRET_KEY=your_alpaca_secret_key_here\n")
                f.write("ALPACA_BASE_URL=https://paper-api.alpaca.markets\n")
                f.write("EIA_API_KEY=your_eia_api_key_here\n")
            
            print("config.env file created with basic configuration")
            print("Please edit config/config.env file with your API keys")
            return True
        except Exception as e:
            print(f"Failed to create config.env file: {e}")
            return False

def create_logs_directory():
    """Create logs directory"""
    try:
        os.makedirs('logs', exist_ok=True)
        print("Logs directory created")
        return True
    except Exception as e:
        print(f"Failed to create logs directory: {e}")
        return False

def main():
    """Main setup function"""
    print("NATGAS TRADER Setup")
    print("=" * 30)
    
    success = True
    
    # Install dependencies
    if not install_dependencies():
        success = False
    
    # Create config.env file
    if not create_config_file():
        success = False
    
    # Create logs directory
    if not create_logs_directory():
        success = False
    
    if success:
        print("\nSetup completed successfully!")
        print("\nNext steps:")
        print("1. Edit config/config.env file with your Alpaca API credentials")
        print("2. (Optional) Add EIA API key for real storage data")
        print("3. Run: python tests/test_components.py (to test components)")
        print("4. Run: python main.py once (to run the bot once)")
        print("5. Run: python main.py continuous 6 (to run continuously)")
    else:
        print("\nSetup completed with errors. Please check the messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()