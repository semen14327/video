import asyncio
import json
import re
from contextlib import asynccontextmanager
from typing import List, Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn

# ═══════════════════════════════════════════════════════════
# УЛУЧШЕНИЯ:
# 1. Система прав (owner/viewer)
# 2. Умная синхронизация (проверка дельты времени)
# 3. Поддержка .mp4 ссылок
# 4. Улучшенная обработка YouTube ID
# 5. Галерея "Сейчас смотрят"
# ═══════════════════════════════════════════════════════════

# --- ХРАНИЛИЩЕ ---
class Room:
    def __init__(self, room_id: str, owner_id: str):
        self.room_id = room_id
        self.owner_id = owner_id  # ← НОВОЕ! Владелец комнаты
        self.users: Dict[WebSocket, dict] = {}  # {ws: {"name": str, "is_owner": bool}}
        self.current_video_url: str = ""
        self.current_time: float = 0.0
        self.is_playing: bool = False
        self.video_source: str = "youtube"  # youtube | mp4
        self.playlist: List[dict] = []  # ← НОВОЕ! Очередь видео

    def is_owner(self, websocket: WebSocket) -> bool:
        """Проверка: является ли пользователь владельцем"""
        return self.users.get(websocket, {}).get("is_owner", False)
    
    def get_users_count(self) -> int:
        """Количество зрителей"""
        return len(self.users)
    
    async def broadcast(self, message: dict, exclude: WebSocket = None):
        """Отправить всем кроме exclude"""
        json_msg = json.dumps(message)
        for connection in list(self.users.keys()):
            if connection != exclude:
                try:
                    await connection.send_text(json_msg)
                except:
                    pass

rooms: Dict[str, Room] = {}

# --- УТИЛИТЫ ---
def extract_youtube_id(url: str) -> Optional[str]:
    """
    Улучшенная регулярка для YouTube ID
    Поддерживает:
    - youtube.com/watch?v=ID
    - youtu.be/ID
    - youtube.com/embed/ID
    """
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/.*[?&]v=([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def detect_video_source(url: str) -> tuple[str, str]:
    """
    Определить источник видео
    Возвращает: (source_type, video_id_or_url)
    """
    # Проверка YouTube
    yt_id = extract_youtube_id(url)
    if yt_id:
        return ("youtube", yt_id)
    
    # Проверка .mp4
    if url.lower().endswith(('.mp4', '.webm', '.ogg')):
        return ("mp4", url)
    
    # Fallback
    return ("unknown", url)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Watch Together запущен!")
    print("📊 Галерея комнат доступна")
    yield
    rooms.clear()

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

# --- МЕНЕДЖЕР ---
class ConnectionManager:
    async def connect(self, websocket: WebSocket, room_id: str, user_name: str, is_owner: bool = False):
        await websocket.accept()
        
        # Создать комнату если не существует
        if room_id not in rooms:
            rooms[room_id] = Room(room_id, user_name)
            is_owner = True  # Первый = владелец
        
        room = rooms[room_id]
        room.users[websocket] = {
            "name": user_name,
            "is_owner": is_owner or (user_name == room.owner_id)
        }
        
        # Отправляем текущее состояние
        await websocket.send_text(json.dumps({
            "type": "init",
            "url": room.current_video_url,
            "time": room.current_time,
            "is_playing": room.is_playing,
            "source": room.video_source,
            "is_owner": room.is_owner(websocket),
            "viewers": room.get_users_count()
        }))

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in rooms:
            if websocket in rooms[room_id].users:
                del rooms[room_id].users[websocket]
                
                # Удалить пустую комнату
                if len(rooms[room_id].users) == 0:
                    del rooms[room_id]

manager = ConnectionManager()

# --- РОУТЫ ---
@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/gallery", response_class=HTMLResponse)
async def gallery(request: Request):
    """Галерея активных комнат"""
    active_rooms = []
    for room_id, room in rooms.items():
        if room.current_video_url:
            active_rooms.append({
                "id": room_id,
                "viewers": room.get_users_count(),
                "url": room.current_video_url,
                "source": room.video_source
            })
    
    return templates.TemplateResponse("gallery.html", {
        "request": request,
        "rooms": active_rooms
    })

@app.websocket("/ws/{room_id}/{user_name}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_name: str):
    await manager.connect(websocket, room_id, user_name)
    room = rooms[room_id]
    
    # Сообщение о входе
    role = "👑 АДМИН" if room.is_owner(websocket) else "👤 Зритель"
    await room.broadcast({
        "type": "chat", 
        "user": "System", 
        "text": f"{user_name} ({role}) присоединился"
    })
    
    # Обновить счётчик зрителей
    await room.broadcast({
        "type": "viewers_update",
        "count": room.get_users_count()
    })

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            # ═══════════════════════════════════════════════
            # ЧАТ
            # ═══════════════════════════════════════════════
            if msg['type'] == 'chat':
                await room.broadcast({
                    "type": "chat", 
                    "user": user_name, 
                    "text": msg['text']
                })

            # ═══════════════════════════════════════════════
            # СМЕНА ВИДЕО (только OWNER!)
            # ═══════════════════════════════════════════════
            elif msg['type'] == 'change_video':
                # ✅ ПРОВЕРКА ПРАВ
                if not room.is_owner(websocket):
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Только админ может менять видео!"
                    }))
                    continue
                
                # Определить источник
                source, video_id = detect_video_source(msg['url'])
                
                if source == "unknown":
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Неподдерживаемый формат видео!"
                    }))
                    continue
                
                room.current_video_url = video_id
                room.video_source = source
                room.current_time = 0
                room.is_playing = True
                
                await room.broadcast({
                    "type": "change_video",
                    "url": video_id,
                    "source": source
                })

            # ═══════════════════════════════════════════════
            # СИНХРОНИЗАЦИЯ (только OWNER!)
            # ═══════════════════════════════════════════════
            elif msg['type'] == 'sync_action':
                # ✅ ПРОВЕРКА ПРАВ
                if not room.is_owner(websocket):
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Только админ может управлять воспроизведением!"
                    }))
                    continue
                
                # ✅ УМНАЯ СИНХРОНИЗАЦИЯ
                # Если разница меньше 2 сек — не трогаем
                time_delta = abs(msg['time'] - room.current_time)
                
                room.current_time = msg['time']
                room.is_playing = (msg['action'] == 'play')
                
                # Отправляем только если дельта > 2 сек
                if time_delta > 2.0 or msg['action'] in ['play', 'pause']:
                    await room.broadcast({
                        "type": "sync_action",
                        "action": msg['action'],
                        "time": msg['time']
                    }, exclude=websocket)

            # ═══════════════════════════════════════════════
            # ЭМОЦИИ
            # ═══════════════════════════════════════════════
            elif msg['type'] == 'emotion':
                await room.broadcast({
                    "type": "emotion",
                    "emoji": msg['emoji']
                })
            
            # ═══════════════════════════════════════════════
            # ПЛЕЙЛИСТ (добавить в очередь)
            # ═══════════════════════════════════════════════
            elif msg['type'] == 'add_to_playlist':
                room.playlist.append({
                    "url": msg['url'],
                    "user": user_name
                })
                
                await room.broadcast({
                    "type": "playlist_update",
                    "playlist": room.playlist
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        
        # Сообщение о выходе
        if room_id in rooms:
            await rooms[room_id].broadcast({
                "type": "chat", 
                "user": "System", 
                "text": f"{user_name} вышел"
            })
            
            # Обновить счётчик
            await rooms[room_id].broadcast({
                "type": "viewers_update",
                "count": rooms[room_id].get_users_count()
            })

import os

if __name__ == "__main__":
    # Читаем порт, который дает Railway, иначе берем 8000
    port = int(os.environ.get("PORT", 8000))
    print(f"🎬 Watch Together Server starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
# if __name__ == "__main__":
#     print("🎬 Watch Together Server")
#     print("📺 Открой: http://localhost:8000")
#     print("🎭 Галерея: http://localhost:8000/gallery")
#     uvicorn.run(app, host="0.0.0.0", port=8000)
