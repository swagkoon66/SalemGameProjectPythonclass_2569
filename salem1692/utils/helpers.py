"""
Utility helper functions for save result
"""

import logging
import os
from datetime import datetime


def save_game_result(msg):
    # Save game result as logging
    try:
        # Get directory where this file (helpers.py) is located
        helpers_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Go up one level to project root, then into data folder
        project_root = os.path.dirname(helpers_dir)
        data_dir = os.path.join(project_root, "data")
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        # Log file in data directory
        log_file = os.path.join(data_dir, "Latest_game_result.log")
        
        print(f"\nDEBUG: Saving log to: {log_file}\n")
        
        # Create logger
        logger = logging.getLogger('game_result_logger')
        logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        if logger.handlers:
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
        
        # Create file handler
        file_handler = logging.FileHandler(log_file, mode='w')
        file_handler.setLevel(logging.INFO)
        
        # Create formatter WITHOUT timestamp (just the message)
        formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(file_handler)
        
        # Write game results
        # First line WITH timestamp
        logger.info(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} - The last game\'s result')
        # Rest WITHOUT timestamp (formatter only shows message)
        logger.info(msg)

        # CRITICAL: Flush and close the handler
        file_handler.flush()
        file_handler.close()
        logger.removeHandler(file_handler)
        
        print("Game result saved successfully!\n")
        
    except Exception as e:
        print(f"Error saving game log: {e}")
        import traceback
        traceback.print_exc()
    return True
    
def test_logging_path():
    """Test logging path and permissions on startup"""
    print("\n" + "="*60)
    print("TESTING LOGGING PATH")
    print("="*60)
    
    try:
        # Get directory where this file (helpers.py) is located
        helpers_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"Helpers directory: {helpers_dir}")
        
        # Go up one level to project root, then into data folder
        project_root = os.path.dirname(helpers_dir)
        print(f"Project root: {project_root}")
        
        data_dir = os.path.join(project_root, "data")
        print(f"Data directory: {data_dir}")
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        print(f"Directory created/exists: ✓")
        
        # Log file will be in data directory
        log_file = os.path.join(data_dir, "Latest_game_result.log")
        print(f"Log file path: {log_file}")
        
        # Test write permissions
        test_content = f"Test write at {datetime.now()}\n"
        with open(log_file, 'w') as f:
            f.write(test_content)
        print(f"Write test: ✓")
        
        # Verify file was created
        if os.path.exists(log_file):
            file_size = os.path.getsize(log_file)
            print(f"File exists: ✓ (size: {file_size} bytes)")
        else:
            print(f"File exists: ✗ WARNING!")
        
        # Test read permissions
        with open(log_file, 'r') as f:
            content = f.read()
        print(f"Read test: ✓")
        
        print("="*60)
        print("LOGGING PATH TEST COMPLETED SUCCESSFULLY!")
        print("="*60 + "\n")
        
    except Exception as e:
        print("="*60)
        print("LOGGING PATH TEST FAILED!")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print("="*60 + "\n")