"""
Utility helper functions
"""

import logging
# import sqlite3 
from datetime import datetime
import os

def setup_logging():
    """Setup logging configuration"""
    base_dir = os.path.dirname(__file__)
    log_path = os.path.join(base_dir, "..", "data")
    os.makedirs(log_path, exist_ok=True)

    log_file = os.path.join(log_path, "Latest_game_result.log")

    # Create a dedicated logger for game results
    logger = logging.getLogger('game_result_logger')
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers to avoid duplicates
    logger.handlers = []
    
    # Create file handler
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    
    return logger

def save_game_result(logger, winner, players, game_duration):
    """Save game result to .log file"""
    print("WORKS")
    logger.info(f'The game result at {datetime.now().strftime("%Y-%m-%d")}\n')
    logger.info(f'WINNERS\n')
    for _ in winner:
        logger.info(f'{_} \n')
    logger.info(f'PLAYERS\n')
    for _ in players:
        logger.info(f'{_} \n')
    logger.info(f'The game duration is {game_duration} seconds')
    
# def save_game_result(winner, players, game_duration):
#     """Save game result to database"""
#     try:
#         conn = sqlite3.connect('data/game_history.db')
#         cursor = conn.cursor()
        
#         # Create table if it doesn't exist
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS game_history (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 date TEXT,
#                 winner TEXT,
#                 players TEXT,
#                 duration INTEGER,
#                 num_players INTEGER,
#                 num_witches INTEGER
#             )
#         ''')
        
#         # Insert game result
#         players_str = ','.join([p.name for p in players])
#         num_witches = sum(1 for p in players if p.is_witch())
        
#         cursor.execute('''
#             INSERT INTO game_history (date, winner, players, duration, num_players, num_witches)
#             VALUES (?, ?, ?, ?, ?, ?)
#         ''', (
#             datetime.now().isoformat(),
#             winner,
#             players_str,
#             game_duration,
#             len(players),
#             num_witches
#         ))
        
#         conn.commit()
#         conn.close()
#         return True
#     except Exception as e:
#         print(f"Error saving game result: {e}")
#         return False

# def get_game_history(limit=10):
#     """Retrieve game history from database"""
#     try:
#         conn = sqlite3.connect('data/game_history.db')
#         cursor = conn.cursor()
        
#         cursor.execute('''
#             SELECT date, winner, players, num_players, num_witches
#             FROM game_history
#             ORDER BY date DESC
#             LIMIT ?
#         ''', (limit,))
        
#         results = cursor.fetchall()
#         conn.close()
#         return results
#     except Exception as e:
#         print(f"Error retrieving game history: {e}")
#         return []

def validate_player_names(names):
    """Validate player names input"""
    if not names:
        return False, "No players entered"
    
    if len(names) < 4:
        return False, "Need at least 4 players"
    
    if len(names) > 12:
        return False, "Maximum 12 players allowed"
    
    # Check for duplicates
    if len(set(names)) != len(names):
        return False, "Player names must be unique"
    
    # Check for empty names
    if any(not name.strip() for name in names):
        return False, "Player names cannot be empty"
    
    return True, "Valid"