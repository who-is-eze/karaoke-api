from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Karaoke API")

rooms = {}
users = {}


class Room(BaseModel):
    room_id: str
    owner_id: int


class RobloxLink(BaseModel):
    discord_id: int
    roblox_id: int
    roblox_username: str


class Player(BaseModel):
    room_id: str
    player_id: int


class Song(BaseModel):
    room_id: str
    title: str
    url: str


@app.get("/")
async def root():
    return {"status": "online"}


@app.post("/users/link")
async def link_user(data: RobloxLink):
    users[data.discord_id] = {
        "roblox_id": data.roblox_id,
        "roblox_username": data.roblox_username
    }
    return {"success": True}


@app.get("/users/{discord_id}")
async def get_user(discord_id: int):
    user = users.get(discord_id)
    if not user:
        raise HTTPException(404, "Usuario no vinculado")
    return user


@app.post("/rooms")
async def create_room(data: Room):
    if data.room_id in rooms:
        raise HTTPException(400, "La sala ya existe")

    rooms[data.room_id] = {
        "owner_id": data.owner_id,
        "status": "waiting",
        "song": None,
        "players": {}
    }

    return {"success": True, "room_id": data.room_id}


@app.get("/rooms/{room_id}")
async def get_room(room_id: str):
    room = rooms.get(room_id)
    if not room:
        raise HTTPException(404, "Sala no encontrada")
    return {"room_id": room_id, **room}


@app.delete("/rooms/{room_id}")
async def delete_room(room_id: str):
    if room_id not in rooms:
        raise HTTPException(404, "Sala no encontrada")

    del rooms[room_id]
    return {"success": True}


@app.post("/rooms/{room_id}/players")
async def join_room(room_id: str, data: Player):
    room = rooms.get(room_id)
    if not room:
        raise HTTPException(404, "Sala no encontrada")

    room["players"][data.player_id] = {
        "ready": False
    }

    return {"success": True}


@app.delete("/rooms/{room_id}/players/{player_id}")
async def leave_room(room_id: str, player_id: int):
    room = rooms.get(room_id)
    if not room:
        raise HTTPException(404, "Sala no encontrada")

    room["players"].pop(player_id, None)
    return {"success": True}


@app.post("/rooms/{room_id}/ready")
async def player_ready(room_id: str, data: Player):
    room = rooms.get(room_id)
    if not room:
        raise HTTPException(404, "Sala no encontrada")

    player = room["players"].get(data.player_id)
    if not player:
        raise HTTPException(404, "Jugador no está en la sala")

    player["ready"] = True
    return {"success": True}


@app.post("/rooms/{room_id}/song")
async def set_song(room_id: str, data: Song):
    room = rooms.get(room_id)
    if not room:
        raise HTTPException(404, "Sala no encontrada")

    room["song"] = {
        "title": data.title,
        "url": data.url
    }
    room["status"] = "playing"

    return {"success": True}


@app.delete("/rooms/{room_id}/song")
async def clear_song(room_id: str):
    room = rooms.get(room_id)
    if not room:
        raise HTTPException(404, "Sala no encontrada")

    room["song"] = None
    room["status"] = "waiting"

    return {"success": True}