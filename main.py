from fastapi import FastAPI, Request
import aiohttp
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

USER_FILE = "authenticated_users.json"

def load_users():
    try:
        with open(USER_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=4)

authenticated_users = load_users()

async def send_ip_to_discord(ip, user_id, user_agent):
    async with aiohttp.ClientSession() as session:
        await session.post(WEBHOOK_URL, json={
            "content": f"🕵️‍♂️ 인증 IP: `{ip}`\nUser ID: `{user_id}`\nUser-Agent: `{user_agent}`"
        })

@app.get("/callback")
async def callback(request: Request):
    code = request.query_params.get("code")
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "Unknown")

    async with aiohttp.ClientSession() as session:
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with session.post("https://discord.com/api/oauth2/token", data=data, headers=headers) as res:
            token_json = await res.json()
            access_token = token_json.get("access_token")

        headers = {"Authorization": f"Bearer {access_token}"}
        async with session.get("https://discord.com/api/users/@me", headers=headers) as res:
            user_json = await res.json()
            user_id = user_json["id"]

        await send_ip_to_discord(client_ip, user_id, user_agent)

        authenticated_users[user_id] = access_token
        save_users(authenticated_users)

    return {"message": "인증 완료되었습니다. 운영자가 초대할 것입니다."}
