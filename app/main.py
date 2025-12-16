# app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.crud import get_metrics, get_queue_prioritization, get_active_vms, get_idle_vms
import asyncio
import json
from typing import List

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """Send message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error sending to client: {e}")

manager = ConnectionManager()

@app.get("/")
def root():
    return {"message": "Automation Dashboard API is running"}

# @app.get("/api/metrics")
# def metrics():
#     """HTTP endpoint - still available as fallback"""
#     try:
#         return get_metrics()
#     except Exception as e:
#         return {
#             "errors": 0,
#             "exceptions": 0,
#             "successful": 0,
#             "inProgress": 0,
#             "totalInQueue": 0,
#             "avgTime": 0,
#             "error": str(e)
#         }

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """
    Single WebSocket endpoint for all dashboard data.
    Sends multiple event types that frontend can handle separately:
    - metrics_update: KPI metrics (errors, exceptions, successful, etc.)
    - queue_priority_update: Bots in queue sorted by transaction count
    - Add more event types here as needed for new sections
    """
    await manager.connect(websocket)

    try:
        while True:
            timestamp = asyncio.get_event_loop().time()

            # Event 1: Metrics update
            try:
                metrics_data = get_metrics()
                await websocket.send_json({
                    "type": "metrics_update",
                    "data": metrics_data,
                    "timestamp": timestamp
                })
            except Exception as e:
                print(f"Error fetching metrics: {e}")
                await websocket.send_json({
                    "type": "error",
                    "source": "metrics",
                    "message": str(e)
                })

            # Event 2: Queue priority update
            try:
                queue_data = get_queue_prioritization()
                await websocket.send_json({
                    "type": "queue_priority_update",
                    "data": queue_data,
                    "timestamp": timestamp
                })
            except Exception as e:
                print(f"Error fetching queue priority: {e}")
                await websocket.send_json({
                    "type": "error",
                    "source": "queue_priority",
                    "message": str(e)
                })

            # Event 3: Active VMs update (for hexagon grid - CaseStatus='InProgress')
            try:
                active_vms_data = get_active_vms()
                await websocket.send_json({
                    "type": "active_vms_update",
                    "data": active_vms_data,
                    "timestamp": timestamp
                })
            except Exception as e:
                print(f"Error fetching active VMs: {e}")
                await websocket.send_json({
                    "type": "error",
                    "source": "active_vms",
                    "message": str(e)
                })

            # Event 4: Idle VMs update (for Entry/Exit pool - VMs NOT in progress)
            try:
                idle_vms_data = get_idle_vms()
                await websocket.send_json({
                    "type": "idle_vms_update",
                    "data": idle_vms_data,
                    "timestamp": timestamp
                })
            except Exception as e:
                print(f"Error fetching idle VMs: {e}")
                await websocket.send_json({
                    "type": "error",
                    "source": "idle_vms",
                    "message": str(e)
                })

            # Add more events here for future sections:
            # Event 4: await websocket.send_json({"type": "bot_status_update", ...})
            # Event 5: await websocket.send_json({"type": "alerts_update", ...})

            # Wait 10 seconds before next update cycle
            await asyncio.sleep(10)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected from dashboard WebSocket")
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)