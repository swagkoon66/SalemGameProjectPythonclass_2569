"""
Network protocol for multiplayer communication
Defines message structure and types
"""

import json
import struct
import logging
import socket
from enum import Enum
import os

base_dir = os.path.dirname(__file__)
temp_dir = os.path.join(base_dir, "temp")
os.makedirs(temp_dir, exist_ok=True)

log_file = os.path.join(temp_dir, "protocol.log")

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    filemode="w",
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class MessageType(Enum):
    CONNECT = "CONNECT"
    CONNECT_ACK = "CONNECT_ACK"
    DISCONNECT = "DISCONNECT"
    HEARTBEAT = "HEARTBEAT"
    HEARTBEAT_ACK = "HEARTBEAT_ACK"
    JOIN_GAME = "JOIN_GAME"
    JOIN_ACK = "JOIN_ACK"
    PLAYER_LIST = "PLAYER_LIST"
    PLAYER_READY = "PLAYER_READY"
    GAME_START = "GAME_START"
    GAME_READY = "GAME_READY"
    PLAYER_TURN = "PLAYER_TURN"
    DRAW_CARD = "DRAW_CARD"
    DRAW_CARD_RESULT = "DRAW_CARD_RESULT"
    ACCUSE = "ACCUSE"
    ACCUSE_RESULT = "ACCUSE_RESULT"
    VOTE = "VOTE"
    VOTE_RESULT = "VOTE_RESULT"
    RESOLVE_ACCUSATION = "RESOLVE_ACCUSATION"
    GAME_STATE = "GAME_STATE"
    GAME_OVER = "GAME_OVER"
    NEXT_TURN = "NEXT_TURN"
    TURN_ENDED = "TURN_ENDED"
    CHAT_MESSAGE = "CHAT_MESSAGE"
    ERROR = "ERROR"
    ERROR_INVALID_ACTION = "ERROR_INVALID_ACTION"
    ERROR_NOT_YOUR_TURN = "ERROR_NOT_YOUR_TURN"
    ERROR_PLAYER_NOT_FOUND = "ERROR_PLAYER_NOT_FOUND"
    STATUS = "STATUS"
    PLAYER_JOINED = "PLAYER_JOINED"
    PLAYER_LEFT = "PLAYER_LEFT"
    PLAYER_ELIMINATED = "PLAYER_ELIMINATED"
    PLAY_CARD = "PLAY_CARD"
    NIGHT_KILL = "NIGHT_KILL"
    NIGHT_SAVE = "NIGHT_SAVE"
    NIGHT_RESOLVED = "NIGHT_RESOLVED"
    DAWN_VOTE = "DAWN_VOTE"
    CONFESS = "CONFESS"
    CONFESS_PHASE = "CONFESS_PHASE"
    CONFESS_DONE = "CONFESS_DONE"

class Message:
    def __init__(self, msg_type, data=None, msg_id=None):
        import time
        self.type = msg_type if isinstance(msg_type, MessageType) else MessageType(msg_type)
        self.data = data or {}
        self.timestamp = time.time()
        self.id = msg_id or f"{int(self.timestamp * 1000)}"
    
    def to_json(self):
        return json.dumps({
            'id': self.id,
            'type': self.type.value,
            'timestamp': self.timestamp,
            'data': self.data
        }, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str):
        try:
            data = json.loads(json_str)
            return cls(
                msg_type=data['type'],
                data=data.get('data', {}),
                msg_id=data.get('id')
            )
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"Message creation error: {e}")
            return None
    
    def __str__(self):
        return f"Message(id={self.id}, type={self.type.value}, data={self.data})"
    
    def __repr__(self):
        return self.__str__()

def send_message(sock, message):
    try:
        json_str = message.to_json()
        json_bytes = json_str.encode('utf-8')
        length = len(json_bytes)
        length_bytes = struct.pack('!I', length)
        sock.sendall(length_bytes)
        sock.sendall(json_bytes)
        logger.debug(f"Sent message: {message.type.value} (length: {length})")
        return True
    except struct.error as e:
        logger.error(f"Struct packing error: {e}")
        return False
    except socket.error as e:
        logger.error(f"Socket error while sending: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending message: {e}")
        return False

def receive_message(sock, timeout=None):
    try:
        if timeout is not None:
            sock.settimeout(timeout)
        
        length_bytes = b''
        while len(length_bytes) < 4:
            chunk = sock.recv(4 - len(length_bytes))
            if not chunk:
                return None
            length_bytes += chunk
        
        length = struct.unpack('!I', length_bytes)[0]
        
        if length > 10 * 1024 * 1024:
            logger.error(f"Message too large: {length} bytes")
            return None
        
        message_bytes = b''
        while len(message_bytes) < length:
            chunk = sock.recv(length - len(message_bytes))
            if not chunk:
                return None
            message_bytes += chunk
        
        json_str = message_bytes.decode('utf-8')
        message = Message.from_json(json_str)
        
        if message:
            logger.debug(f"Received message: {message.type.value}")
        else:
            logger.warning("Failed to parse message")
        
        if timeout is not None:
            sock.settimeout(None)
        
        return message
        
    except socket.timeout:
        logger.debug("Socket timeout while receiving")
        # FIX 2: always reset timeout so socket doesn't stay stuck in timed mode
        if timeout is not None:
            try:
                sock.settimeout(None)
            except Exception:
                pass
        return None
    except socket.error as e:
        logger.error(f"Socket error while receiving: {e}")
        return None
    except struct.error as e:
        logger.error(f"Struct unpacking error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error receiving message: {e}")
        return None