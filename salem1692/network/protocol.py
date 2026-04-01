"""
Network protocol for multiplayer communication
Defines message structure and types
"""

import json
import struct
import logging
from enum import Enum

# Setup logging for network debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Types of messages sent between client and server"""
    
    # Connection messages
    CONNECT = "CONNECT"
    CONNECT_ACK = "CONNECT_ACK"
    DISCONNECT = "DISCONNECT"
    HEARTBEAT = "HEARTBEAT"
    HEARTBEAT_ACK = "HEARTBEAT_ACK"
    
    # Game setup messages
    JOIN_GAME = "JOIN_GAME"
    JOIN_ACK = "JOIN_ACK"
    PLAYER_LIST = "PLAYER_LIST"
    GAME_START = "GAME_START"
    GAME_READY = "GAME_READY"
    
    # Game play messages
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
    
    # Chat
    CHAT_MESSAGE = "CHAT_MESSAGE"
    
    # Error messages
    ERROR = "ERROR"
    ERROR_INVALID_ACTION = "ERROR_INVALID_ACTION"
    ERROR_NOT_YOUR_TURN = "ERROR_NOT_YOUR_TURN"
    ERROR_PLAYER_NOT_FOUND = "ERROR_PLAYER_NOT_FOUND"
    
    # Status messages
    STATUS = "STATUS"
    PLAYER_JOINED = "PLAYER_JOINED"
    PLAYER_LEFT = "PLAYER_LEFT"
    PLAYER_ELIMINATED = "PLAYER_ELIMINATED"

class Message:
    """
    Message wrapper for network transmission
    Format: [4-byte length][JSON message]
    """
    
    def __init__(self, msg_type, data=None, msg_id=None):
        """
        Initialize a message
        
        Args:
            msg_type: MessageType enum or string
            data: Dictionary of message data
            msg_id: Optional message ID for tracking
        """
        import time
        self.type = msg_type if isinstance(msg_type, MessageType) else MessageType(msg_type)
        self.data = data or {}
        self.timestamp = time.time()
        self.id = msg_id or f"{int(self.timestamp * 1000)}"
    
    def to_json(self):
        """Convert message to JSON string"""
        return json.dumps({
            'id': self.id,
            'type': self.type.value,
            'timestamp': self.timestamp,
            'data': self.data
        }, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str):
        """Create message from JSON string"""
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
    """
    Send a message over a socket with length prefix
    
    Args:
        sock: Socket object
        message: Message object to send
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Convert message to JSON
        json_str = message.to_json()
        json_bytes = json_str.encode('utf-8')
        
        # Send length prefix (4 bytes, big-endian)
        length = len(json_bytes)
        length_bytes = struct.pack('!I', length)
        
        # Send length then message
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
    """
    Receive a message from a socket
    
    Args:
        sock: Socket object
        timeout: Optional timeout in seconds
    
    Returns:
        Message object if successful, None otherwise
    """
    try:
        # Set timeout if specified
        if timeout is not None:
            sock.settimeout(timeout)
        
        # Receive length prefix (4 bytes)
        length_bytes = b''
        while len(length_bytes) < 4:
            chunk = sock.recv(4 - len(length_bytes))
            if not chunk:
                return None
            length_bytes += chunk
        
        # Unpack length
        length = struct.unpack('!I', length_bytes)[0]
        
        # Sanity check - prevent huge messages
        if length > 10 * 1024 * 1024:  # 10 MB max
            logger.error(f"Message too large: {length} bytes")
            return None
        
        # Receive message body
        message_bytes = b''
        while len(message_bytes) < length:
            chunk = sock.recv(length - len(message_bytes))
            if not chunk:
                return None
            message_bytes += chunk
        
        # Parse JSON
        json_str = message_bytes.decode('utf-8')
        message = Message.from_json(json_str)
        
        if message:
            logger.debug(f"Received message: {message.type.value}")
        else:
            logger.warning("Failed to parse message")
        
        # Reset timeout
        if timeout is not None:
            sock.settimeout(None)
        
        return message
        
    except socket.timeout:
        logger.debug("Socket timeout while receiving")
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

# Import socket for error handling
import socket