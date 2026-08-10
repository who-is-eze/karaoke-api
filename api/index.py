import os
import mariadb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Karaoke API")


def db():
    try:
        return mariadb.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME", "karaoke")
        )
    except mariadb.Error as e:
        raise RuntimeError(f"Error de MariaDB: {e}")


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
    conn = db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO users (discord_id, roblox_id, roblox_username)
        VALUES (?, ?, ?)
        ON DUPLICATE KEY UPDATE
        roblox_id = VALUES(roblox_id),
        roblox_username = VALUES(roblox_username)
        """,
        (data.discord_id, data.roblox_id, data.roblox_username)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return {"success": True}


@app.get("/users/{discord_id}")
async def get_user(discord_id: int):
    conn = db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT roblox_id, roblox_username
        FROM users
        WHERE discord_id = ?
        """,
        (discord_id,)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        raise HTTPException(404, "Usuario no vinculado")

    return {
        "roblox_id": user[0],
        "roblox_username": user[1]
    }


@app.post("/rooms")
async def create_room(data: Room):
    conn = db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT room_id FROM rooms WHERE room_id = ?",
        (data.room_id,)
    )

    if cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(400, "La sala ya existe")

    cursor.execute(
        """
        INSERT INTO rooms (room_id, owner_id, status)
        VALUES (?, ?, 'waiting')
        """,
        (data.room_id, data.owner_id)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "success": True,
        "room_id": data.room_id
    }


@app.get("/rooms/{room_id}")
async def get_room(room_id: str):
    conn = db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT owner_id, status,
               current_song_title,
               current_song_url
        FROM rooms
        WHERE room_id = ?
        """,
        (room_id,)
    )

    room = cursor.fetchone()

    if not room:
        cursor.close()
        conn.close()
        raise HTTPException(404, "Sala no encontrada")

    cursor.execute(
        """
        SELECT player_id, ready
        FROM room_players
        WHERE room_id = ?
        """,
        (room_id,)
    )

    players = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "room_id": room_id,
        "owner_id": room[0],
        "status": room[1],
        "song": (
            {
                "title": room[2],
                "url": room[3]
            }
            if room[2] else None
        ),
        "players": [
            {
                "player_id": player[0],
                "ready": bool(player[1])
            }
            for player in players
        ]
    }


@app.delete("/rooms/{room_id}")
async def delete_room(room_id: str):
    conn = db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT room_id FROM rooms WHERE room_id = ?",
        (room_id,)
    )

    if not cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(404, "Sala no encontrada")

    cursor.execute(
        "DELETE FROM rooms WHERE room_id = ?",
        (room_id,)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return {"success": True}


@app.post("/rooms/{room_id}/players")
async def join_room(room_id: str, data: Player):
    conn = db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT room_id FROM rooms WHERE room_id = ?",
        (room_id,)
    )

    if not cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(404, "Sala no encontrada")

    cursor.execute(
        """
        INSERT INTO room_players (room_id, player_id, ready)
        VALUES (?, ?, FALSE)
        ON DUPLICATE KEY UPDATE
        ready = FALSE
        """,
        (room_id, data.player_id)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return {"success": True}


@app.delete("/rooms/{room_id}/players/{player_id}")
async def leave_room(room_id: str, player_id: int):
    conn = db()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM room_players
        WHERE room_id = ? AND player_id = ?
        """,
        (room_id, player_id)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return {"success": True}


@app.post("/rooms/{room_id}/ready")
async def player_ready(room_id: str, data: Player):
    conn = db()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE room_players
        SET ready = TRUE
        WHERE room_id = ? AND player_id = ?
        """,
        (room_id, data.player_id)
    )

    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        raise HTTPException(404, "Jugador no está en la sala")

    conn.commit()
    cursor.close()
    conn.close()

    return {"success": True}


@app.post("/rooms/{room_id}/song")
async def set_song(room_id: str, data: Song):
    conn = db()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE rooms
        SET current_song_title = ?,
            current_song_url = ?,
            status = 'playing'
        WHERE room_id = ?
        """,
        (data.title, data.url, room_id)
    )

    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        raise HTTPException(404, "Sala no encontrada")

    conn.commit()
    cursor.close()
    conn.close()

    return {"success": True}


@app.delete("/rooms/{room_id}/song")
async def clear_song(room_id: str):
    conn = db()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE rooms
        SET current_song_title = NULL,
            current_song_url = NULL,
            status = 'waiting'
        WHERE room_id = ?
        """,
        (room_id,)
    )

    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        raise HTTPException(404, "Sala no encontrada")

    conn.commit()
    cursor.close()
    conn.close()

    return {"success": True}
