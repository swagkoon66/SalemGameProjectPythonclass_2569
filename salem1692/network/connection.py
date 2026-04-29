"""
Connection management for multiplayer game
Handles client and server connections with improved reliability
"""

import socket
import threading
import time
from .protocol import send_message, receive_message, Message, MessageType

class ClientConnection:
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
        self.heartbeat_interval = 5
        self.heartbeat_timeout = 15
        
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(None)

            send_message(self.socket, Message(MessageType.CONNECT, {
                'name': self.player_name or 'Player'
            }))

            self.connected = True
            self.last_heartbeat = time.time()
            
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
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
        if self.connected:
            self.connected = False
            try:
                send_message(self.socket, Message(MessageType.DISCONNECT, {
                    'player_id': self.player_id,
                    'player_name': self.player_name
                }))
            except:
                pass
            try:
                self.socket.close()
            except:
                pass
            logger.info("Disconnected from server")
    
    def send(self, message):
        if self.connected and self.socket:
            return send_message(self.socket, message)
        return False
    
    def register_handler(self, handler):
        self.message_handlers.append(handler)
    
    def _receive_loop(self):
        while self.connected:
            try:
                message = receive_message(self.socket)
                if message:
                    if message.type == MessageType.HEARTBEAT:
                        self._handle_heartbeat(message)
                    else:
                        for handler in self.message_handlers:
                            try:
                                handler(message)
                            except Exception as e:
                                logger.error(f"Handler error: {e}")
                else:
                    break
            except Exception as e:
                if self.connected:
                    logger.error(f"Receive error: {e}")
                break
        
        self.connected = False
        logger.info("Connection lost")
        
        for handler in self.message_handlers:
            try:
                handler(Message(MessageType.DISCONNECT, {'reason': 'connection_lost'}))
            except:
                pass
    
    def _heartbeat_loop(self):
        while self.connected:
            time.sleep(self.heartbeat_interval)
            if self.connected:
                heartbeat_msg = Message(MessageType.HEARTBEAT, {
                    'timestamp': time.time(),
                    'player_id': self.player_id
                })
                if not self.send(heartbeat_msg):
                    logger.warning("Failed to send heartbeat")
                    break
    
    def _handle_heartbeat(self, message):
        self.last_heartbeat = time.time()
        ack_msg = Message(MessageType.HEARTBEAT_ACK, {
            'timestamp': message.data.get('timestamp'),
            'player_id': self.player_id
        })
        self.send(ack_msg)


class ServerConnection:
    def __init__(self, host='0.0.0.0', port=5555):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}
        self.client_counter = 0
        self.running = False
        self.message_handler = None
        self.accept_thread = None
        self.cleanup_thread = None
        self.lock = threading.Lock()
        
    def start(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            self.running = True
            
            self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.accept_thread.start()
            
            logger.info(f"Server started on {self.host}:{self.port}")
            return True
            
        except socket.error as e:
            logger.error(f"Server start error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error starting server: {e}")
            return False
    
    def stop(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        with self.lock:
            for client_id, client in list(self.clients.items()):
                try:
                    client['socket'].close()
                except:
                    pass
        self.clients.clear()
        logger.info("Server stopped")
    
    def send_to_client(self, client_id, message):
        with self.lock:
            if client_id in self.clients:
                try:
                    return send_message(self.clients[client_id]['socket'], message)
                except Exception as e:
                    logger.error(f"Error sending to client {client_id}: {e}")
                    return False
        return False
    
    def broadcast(self, message, exclude_client=None):
        with self.lock:
            for client_id, client in self.clients.items():
                if client_id != exclude_client:
                    try:
                        send_message(client['socket'], message)
                    except Exception as e:
                        logger.error(f"Error broadcasting to {client_id}: {e}")
    
    def get_client_name(self, client_id):
        with self.lock:
            if client_id in self.clients:
                return self.clients[client_id]['name']
        return None
    
    def get_client_ids(self):
        with self.lock:
            return list(self.clients.keys())
    
    def get_client_count(self):
        with self.lock:
            return len(self.clients)
    
    def remove_client(self, client_id):
        with self.lock:
            if client_id in self.clients:
                try:
                    self.clients[client_id]['socket'].close()
                except:
                    pass
                del self.clients[client_id]
                logger.info(f"Client {client_id} removed")
    
    def _accept_loop(self):
        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                try:
                    client_socket, address = self.server_socket.accept()
                except socket.timeout:
                    continue
                
                logger.info(f"New connection from {address}")
                
                client_socket.settimeout(5.0)
                message = receive_message(client_socket)
                client_socket.settimeout(None)
                
                if message and message.type == MessageType.CONNECT:
                    player_name = message.data.get('name', f'Player{self.client_counter + 1}')
                    
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
                    
                    send_message(client_socket, Message(MessageType.CONNECT_ACK, {
                        'player_id': client_id,
                        'player_name': player_name,
                        'server_time': time.time()
                    }))
                    
                    logger.info(f"Player {player_name} (ID: {client_id}) connected from {address}")
                    
                    if self.message_handler:
                        self.message_handler(client_id, Message(MessageType.PLAYER_JOINED, {
                            'player_id': client_id,
                            'player_name': player_name
                        }))
                    
                    thread = threading.Thread(target=self._client_receive_loop,
                                             args=(client_id, client_socket),
                                             daemon=True)
                    thread.start()
                    
                else:
                    client_socket.close()
                    logger.warning(f"Invalid connect message from {address}")
                    
            except Exception as e:
                if self.running:
                    logger.error(f"Accept error: {e}")
    
    def _client_receive_loop(self, client_id, client_socket):
        while self.running and client_id in self.clients:
            try:
                message = receive_message(client_socket)
                if message:
                    if message.type == MessageType.HEARTBEAT:
                        self._handle_heartbeat(client_id, message)
                    elif message.type == MessageType.DISCONNECT:
                        break
                    else:
                        if self.message_handler:
                            try:
                                self.message_handler(client_id, message)
                            except Exception as e:
                                logger.error(f"Message handler error: {e}")
                else:
                    break
            except Exception as e:
                logger.error(f"Error receiving from client {client_id}: {e}")
                break
        
        self._handle_disconnect(client_id)
    
    def _handle_heartbeat(self, client_id, message):
        ack_msg = Message(MessageType.HEARTBEAT_ACK, {
            'timestamp': message.data.get('timestamp'),
            'client_id': client_id
        })
        self.send_to_client(client_id, ack_msg)
    
    def _handle_disconnect(self, client_id):
        player_name = self.get_client_name(client_id)
        self.remove_client(client_id)
        
        if player_name:
            logger.info(f"Player {player_name} disconnected")
            if self.message_handler:
                self.message_handler(client_id, Message(MessageType.PLAYER_LEFT, {
                    'player_id': client_id,
                    'player_name': player_name
                }))
            self.broadcast(Message(MessageType.CHAT_MESSAGE, {
                'text': f"⚠️ {player_name} has left the game ⚠️"
            }))