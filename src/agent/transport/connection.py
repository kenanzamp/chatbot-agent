"""
WebSocket connection management with heartbeat.
"""

import asyncio
from typing import Dict, Optional
from fastapi import WebSocket
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections.
    
    Features:
    - Connection tracking by client ID
    - Heartbeat for stale connection detection
    - Graceful disconnect handling
    """
    
    def __init__(self, heartbeat_interval: int = 30):
        self.active_connections: Dict[str, WebSocket] = {}
        self.heartbeat_interval = heartbeat_interval
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}
        self._connection_times: Dict[str, datetime] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept and track a new connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self._connection_times[client_id] = datetime.utcnow()
        
        # Start heartbeat task
        self._heartbeat_tasks[client_id] = asyncio.create_task(
            self._heartbeat_loop(client_id)
        )
        
        logger.info(f"Client {client_id} connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, client_id: str):
        """Remove a connection."""
        self.active_connections.pop(client_id, None)
        self._connection_times.pop(client_id, None)
        
        if client_id in self._heartbeat_tasks:
            self._heartbeat_tasks[client_id].cancel()
            del self._heartbeat_tasks[client_id]
        
        logger.info(f"Client {client_id} disconnected. Total: {len(self.active_connections)}")
    
    async def send_json(self, client_id: str, data: dict) -> bool:
        """Send JSON message to a client."""
        websocket = self.active_connections.get(client_id)
        if not websocket:
            return False
        
        try:
            await websocket.send_json(data)
            return True
        except Exception as e:
            logger.error(f"Failed to send to {client_id}: {e}")
            self.disconnect(client_id)
            return False
    
    async def broadcast(self, data: dict, exclude: Optional[str] = None):
        """Send message to all connected clients."""
        for client_id in list(self.active_connections.keys()):
            if client_id != exclude:
                await self.send_json(client_id, data)
    
    async def _heartbeat_loop(self, client_id: str):
        """Send periodic pings to detect stale connections."""
        while client_id in self.active_connections:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                if client_id in self.active_connections:
                    await self.send_json(client_id, {"type": "ping"})
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Heartbeat failed for {client_id}: {e}")
                self.disconnect(client_id)
                break
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)
    
    def get_connection_info(self, client_id: str) -> Optional[dict]:
        """Get info about a connection."""
        if client_id not in self.active_connections:
            return None
        return {
            "client_id": client_id,
            "connected_at": self._connection_times.get(client_id),
            "active": True
        }
