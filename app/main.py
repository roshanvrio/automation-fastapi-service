from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from app.database.connection import SessionLocal
from app.database.queries import get_metrics, get_queue_priority, get_active_vms, get_idle_vms, get_vm_utilization

app = FastAPI(title = "Automation Dashboard Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Dashboard Backend API is running"}

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):

    await websocket.accept()
    print("WebSocket Connection Established")

    try:
        while True:

            db = SessionLocal()
            try:
                metrics_data = get_metrics(db)
                await websocket.send_json({
                    "type": "metrics_update",
                    "data": metrics_data
                })

                #print(f"Sent metrics data: {metrics_data}")

                queue_data = get_queue_priority(db)
                await websocket.send_json({
                    "type": "queue_priority_update",
                    "data": queue_data
                })

                #print(f"Sent queue priority data: {queue_data}")

                active_vms_data = get_active_vms(db)
                await websocket.send_json({
                    "type": "active_vms_update",
                    "data": active_vms_data
                })

                #print(f"Sent active VMs data: {active_vms_data}")

                idle_vms_data = get_idle_vms(db)
                await websocket.send_json({
                    "type": "idle_vms_update",
                    "data": idle_vms_data
                })

                #print(f"Sent idle VMs data: {idle_vms_data}")

                vm_utilization_data = get_vm_utilization(db)
                await websocket.send_json({
                    "type": "vm_utilization_update",
                    "data": vm_utilization_data
                })

            except Exception as e:
                print(f"Error getting data: {e}")
                await websocket.send_json({
                    "type": "error",
                    "source": "dashboard",
                    "message": str(e)
                })

            finally:
                db.close()

            await asyncio.sleep(10)
        
    except WebSocketDisconnect:
        print("WebSocket Disconnected")
    except Exception as e:
        print(f"Websocket error: {e}")
