"""
Connection management for multiplayer game
Handles client and server connections with improved reliability
"""

import socket
import threading
import time
import logging
from .protocol import send_message, receive_message, Message, MessageType

logger = logging.getLogger(__name__)

class ClientConnection:
    """
    Manages client connection to server
    Handles reconnection and heartbeat
    """
    
    def __init__(self, host='localhost', port=5555):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.player_id = None
        self.player_name = None
        self.message_handlers = []
        self.receive_thread = None
        self.heartbeat_thread = None
        self.last_heartbeat = 0
        self.heartbeat_interval = 5  # seconds
        self.heartbeat_timeout = 15  # seconds
        
    def connect(self):
        """Connect to server with retry"""
        try:
            # Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)  # 10 second connection timeout
            
            # Connect
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(None)  # Remove timeout after connection
            
            self.connected = True
            self.last_heartbeat = time.time()
            
            # Start receive thread
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            # Start heartbeat thread
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()
            
            logger.info(f"Connected to server at {self.host}:{self.port}")
            return True
            
        except socket.timeout:
            logger.error("Connection timeout")
            return False
        except ConnectionRefusedError:
            logger.error("Connection refused - server may not be running")
            return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from server gracefully"""
        if self.connected:
            self.connected = False
            
            # Send disconnect message
            try:
                send_message(self.socket, Message(MessageType.DISCONNECT, {
                    'player_id': self.player_id,
                    'player_name': self.player_name
                }))
            except:
                pass
            
            # Close socket
            try:
                self.socket.close()
            except:
                pass
            
            logger.info("Disconnected from server")
    
    def send(self, message):
        """Send a message to server"""
        if self.connected and self.socket:
            return send_message(self.socket, message)
        return False
    
    def register_handler(self, handler):
        """Register a message handler"""
        self.message_handlers.append(handler)
    
    def _receive_loop(self):
        """Receive messages from server"""
        while self.connected:
            try:
                message = receive_message(self.socket, timeout=1.0)
                if message:
                    # Handle heartbeat specially
                    if message.type == MessageType.HEARTBEAT:
                        self._handle_heartbeat(message)
                    else:
                        # Notify all other handlers
                        for handler in self.message_handlers:
                            try:
                                handler(message)
                            except Exception as e:
                                logger.error(f"Handler error: {e}")
                else:
                    # No message received, check connection
                    if time.time() - self.last_heartbeat > self.heartbeat_timeout:
                        logger.warning("Heartbeat timeout, disconnecting")
                        break
                    
            except Exception as e:
                if self.connected:
                    logger.error(f"Receive error: {e}")
                break
        
        # Connection lost
        self.connected = False
        logger.info("Connection lost")
        
        # Notify handlers of disconnection
        for handler in self.message_handlers:
            try:
                handler(Message(MessageType.DISCONNECT, {'reason': 'connection_lost'}))
            except:
                pass
    
    def _heartbeat_loop(self):
        """Send heartbeat messages to keep connection alive"""
        while self.connected:
            time.sleep(self.heartbeat_interval)
            
            if self.connected:
                # Send heartbeat
                heartbeat_msg = Message(MessageType.HEARTBEAT, {
                    'timestamp': time.time(),
                    'player_id': self.player_id
                })
                
                if not self.send(heartbeat_msg):
                    logger.warning("Failed to send heartbeat")
                    break
    
    def _handle_heartbeat(self, message):
        """Handle heartbeat from server"""
        self.last_heartbeat = time.time()
        
        # Send heartbeat ack
        ack_msg = Message(MessageType.HEARTBEAT_ACK, {
            'timestamp': message.data.get('timestamp'),
            'player_id': self.player_id
        })
        self.send(ack_msg)


class ServerConnection:
    """
    Manages server connections to clients
    Handles multiple clients with thread pooling
    """
    
    def __init__(self, host='0.0.0.0', port=5555):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}  # {client_id: {'socket': socket, 'name': name, 'address': address, 'last_heartbeat': time}}
        self.client_counter = 0
        self.running = False
        self.message_handler = None
        self.accept_thread = None
        self.cleanup_thread = None
        self.lock = threading.Lock()  # Thread-safe client access
        
    def start(self):
        """Start the server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            self.running = True
            
            # Start accept thread
            self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.accept_thread.start()
            
            # Start cleanup thread
            self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self.cleanup_thread.start()
            
            logger.info(f"Server started on {self.host}:{self.port}")
            return True
            
        except socket.error as e:
            logger.error(f"Server start error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error starting server: {e}")
            return False
    
    def stop(self):
        """Stop the server gracefully"""
        self.running = False
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        # Close all client connections
        with self.lock:
            for client_id, client in list(self.clients.items()):
                try:
                    client['socket'].close()
                except:
                    pass
        
        # Clear clients
        self.clients.clear()
        
        logger.info("Server stopped")
    
    def send_to_client(self, client_id, message):
        """Send message to specific client"""
        with self.lock:
            if client_id in self.clients:
                try:
                    return send_message(self.clients[client_id]['socket'], message)
                except Exception as e:
                    logger.error(f"Error sending to client {client_id}: {e}")
                    return False
        return False
    
    def broadcast(self, message, exclude_client=None):
        """Send message to all connected clients"""
        with self.lock:
            for client_id, client in self.clients.items():
                if client_id != exclude_client:
                    try:
                        send_message(client['socket'], message)
                    except Exception as e:
                        logger.error(f"Error broadcasting to {client_id}: {e}")
    
    def get_client_name(self, client_id):
        """Get client name by ID"""
        with self.lock:
            if client_id in self.clients:
                return self.clients[client_id]['name']
        return None
    
    def get_client_ids(self):
        """Get list of all client IDs"""
        with self.lock:
            return list(self.clients.keys())
    
    def get_client_count(self):
        """Get number of connected clients"""
        with self.lock:
            return len(self.clients)
    
    def remove_client(self, client_id):
        """Remove a client from the server"""
        with self.lock:
            if client_id in self.clients:
                try:
                    self.clients[client_id]['socket'].close()
                except:
                    pass
                del self.clients[client_id]
                logger.info(f"Client {client_id} removed")
    
    def _accept_loop(self):
        """Accept incoming connections"""
        while self.running:
            try:
                # Set timeout to allow checking running flag
                self.server_socket.settimeout(1.0)
                
                try:
                    client_socket, address = self.server_socket.accept()
                except socket.timeout:
                    continue
                
                # Accept connection
                logger.info(f"New connection from {address}")
                
                # Wait for connect message with timeout
                client_socket.settimeout(5.0)
                message = receive_message(client_socket)
                client_socket.settimeout(None)
                
                if message and message.type == MessageType.CONNECT:
                    player_name = message.data.get('name', f'Player{self.client_counter + 1}')
                    
                    # Assign client ID
                    with self.lock:
                        self.client_counter += 1
                        client_id = self.client_counter
                        
                        self.clients[client_id] = {
                            'socket': client_socket,
                            'name': player_name,
                            'address': address,
                            'last_heartbeat': time.time(),
                            'connected_at': time.time()
                        }
                    
                    # Send connect ack with player ID
                    send_message(client_socket, Message(MessageType.CONNECT_ACK, {
                        'player_id': client_id,
                        'player_name': player_name,
                        'server_time': time.time()
                    }))
                    
                    logger.info(f"Player {player_name} (ID: {client_id}) connected from {address}")
                    
                    # Notify server about new connection
                    if self.message_handler:
                        self.message_handler(client_id, Message(MessageType.PLAYER_JOINED, {
                            'player_id': client_id,
                            'player_name': player_name
                        }))
                    
                    # Start receive thread for this client
                    thread = threading.Thread(target=self._client_receive_loop, 
                                             args=(client_id, client_socket), 
                                             daemon=True)
                    thread.start()
                    
                else:
                    # Invalid connect message
                    client_socket.close()
                    logger.warning(f"Invalid connect message from {address}")
                    
            except Exception as e:
                if self.running:
                    logger.error(f"Accept error: {e}")
    
    def _client_receive_loop(self, client_id, client_socket):
        """Receive messages from a client"""
        while self.running and client_id in self.clients:
            try:
                message = receive_message(client_socket, timeout=1.0)
                if message:
                    # Update heartbeat
                    with self.lock:
                        if client_id in self.clients:
                            self.clients[client_id]['last_heartbeat'] = time.time()
                    
                    # Handle heartbeat specially
                    if message.type == MessageType.HEARTBEAT:
                        self._handle_heartbeat(client_id, message)
                    elif message.type == MessageType.DISCONNECT:
                        break
                    else:
                        # Forward to server's message handler
                        if self.message_handler:
                            try:
                                self.message_handler(client_id, message)
                            except Exception as e:
                                logger.error(f"Message handler error: {e}")
                else:
                    # No message received, check if client is still alive
                    with self.lock:
                        if client_id in self.clients:
                            last_hb = self.clients[client_id]['last_heartbeat']
                            if time.time() - last_hb > 30:  # 30 second timeout
                                logger.warning(f"Client {client_id} heartbeat timeout")
                                break
                            
            except Exception as e:
                logger.error(f"Error receiving from client {client_id}: {e}")
                break
        
        # Client disconnected
        self._handle_disconnect(client_id)
    
    def _handle_heartbeat(self, client_id, message):
        """Handle heartbeat from client"""
        # Send heartbeat ack
        ack_msg = Message(MessageType.HEARTBEAT_ACK, {
            'timestamp': message.data.get('timestamp'),
            'client_id': client_id
        })
        self.send_to_client(client_id, ack_msg)
    
    def _handle_disconnect(self, client_id):
        """Handle client disconnection"""
        player_name = self.get_client_name(client_id)
        self.remove_client(client_id)
        
        if player_name:
            logger.info(f"Player {player_name} disconnected")
            
            # Notify server
            if self.message_handler:
                self.message_handler(client_id, Message(MessageType.PLAYER_LEFT, {
                    'player_id': client_id,
                    'player_name': player_name
                }))
            
            # Notify other clients
            self.broadcast(Message(MessageType.CHAT_MESSAGE, {
                'text': f"⚠️ {player_name} has left the game ⚠️"
            }))
    
    def _cleanup_loop(self):
        """Clean up stale connections"""
        while self.running:
            time.sleep(10)  # Check every 10 seconds
            
            with self.lock:
                current_time = time.time()
                stale_clients = []
                
                for client_id, client in self.clients.items():
                    if current_time - client['last_heartbeat'] > 60:  # 1 minute timeout
                        stale_clients.append(client_id)
                
                # Remove stale clients
                for client_id in stale_clients:
                    logger.warning(f"Removing stale client {client_id}")
                    self._handle_disconnect(client_id)