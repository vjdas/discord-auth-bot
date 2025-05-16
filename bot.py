# ✅ bot.py (멀티 서버 대응, Firestore 연동)

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
REDIRECT_URI = os.getenv("REDIRECT_URI")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
FIREBASE_COLLECTION = os.getenv("FIREBASE_COLLECTION", "authenticated_users")

OAUTH_URL = (
    f"https://discord.com/api/oauth2/authorize"
    f"?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
    f"&response_type=code&scope=identify+guilds.join"
)

cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

class StartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="✅ 인증하기", url=OAUTH_URL, style=discord.ButtonStyle.link))

async def load_users(guild_id):
    docs = db.collection(FIREBASE_COLLECTION).document(guild_id).collection("members").stream()
    return {doc.id: doc.to_dict().get("access_token") for doc in docs}

def save_user(guild_id, user_id, access_token):
    db.collection(FIREBASE_COLLECTION).document(guild_id).collection("members").document(user_id).set({
        "access_token": access_token
    })
    print(f"✅ Firestore 저장됨: {guild_id}/{user_id}")

@bot.event
async def on_ready():
    print(f"✅ 봇 로그인됨: {bot.user}")
    try:
        synced = await bot.tree.sync()  # 전체 서버에 등록
        print(f"📌 전역 슬래시 명령 동기화됨: {len(synced)}개")
    except Exception as e:
        print(f"❌ 명령어 동기화 실패: {e}")

@bot.event
async def on_message(message):
    if message.author.bot and "🆕 인증 성공!" in message.content:
        try:
            guild_id = str(message.guild.id) if message.guild else "global"
            lines = message.content.splitlines()
            user_id = lines[2].split("`")[1]
            access_token = lines[3].split("`")[1]
            save_user(guild_id, user_id, access_token)
        except Exception as e:
            print(f"❌ 저장 중 오류: {e}")

@bot.tree.command(name="start", description="인증을 시작합니다")
async def start(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 사용 가능합니다.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🔐 인증이 필요합니다",
        description="아래 버튼을 눌러 Discord 인증을 완료해주세요.",
        color=discord.Color.blue()
    )
    embed.set_image(url="https://media.discordapp.net/attachments/1357680375803019377/1372186674586587228/Ver.gif?width=700&height=700")
    await interaction.response.send_message(embed=embed, view=StartView())

@bot.tree.command(name="list_verified", description="인증된 유저 목록을 봅니다 (관리자용)")
async def list_verified(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 사용 가능합니다.", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    users = await load_users(guild_id)
    if not users:
        await interaction.response.send_message("📭 인증된 유저가 없습니다.", ephemeral=True)
        return

    user_list = "\n".join([f"- <@{uid}>" for uid in users.keys()])
    await interaction.response.send_message(f"📋 인증된 유저 목록:\n{user_list}", ephemeral=True)

@bot.tree.command(name="복구", description="모든 인증된 유저를 서버에 초대합니다")
async def 복구(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 사용 가능합니다.", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    users = await load_users(guild_id)
    if not users:
        await interaction.response.send_message("❌ 인증된 유저가 없습니다.", ephemeral=True)
        return

    success = 0
    failed = 0

    async with aiohttp.ClientSession() as session:
        for user_id, access_token in users.items():
            headers = {
                "Authorization": f"Bot {BOT_TOKEN}",
                "Content-Type": "application/json"
            }
            data = {"access_token": access_token}

            async with session.put(
                f"https://discord.com/api/guilds/{interaction.guild.id}/members/{user_id}",
                json=data, headers=headers
            ) as res:
                if res.status in [201, 204]:
                    success += 1
                else:
                    failed += 1
                    error = await res.text()
                    print(f"❌ 초대 실패: {user_id} / 상태 {res.status} / {error}")

    await interaction.response.send_message(f"✅ 초대 성공: {success}명\n❌ 실패: {failed}명", ephemeral=True)

bot.run(BOT_TOKEN)
