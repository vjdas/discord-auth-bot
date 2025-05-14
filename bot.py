# ✅ bot.py (Render에 배포할 디스코드 봇)

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
import json
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
REDIRECT_URI = os.getenv("REDIRECT_URI")
GUILD_ID = int(os.getenv("GUILD_ID"))

# ✅ OAuth 인증 URL 생성
OAUTH_URL = (
    f"https://discord.com/api/oauth2/authorize"
    f"?client_id={CLIENT_ID}"
    f"&redirect_uri={REDIRECT_URI}"
    f"&response_type=code"
    f"&scope=identify+guilds.join"
)

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

intents = discord.Intents.default()
intents.message_content = True  # Webhook 감지용
bot = commands.Bot(command_prefix="!", intents=intents)

class StartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="✅ 인증하기", url=OAUTH_URL, style=discord.ButtonStyle.link))

@bot.event
async def on_ready():
    print(f"✅ 봇 로그인됨: {bot.user}")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"📌 슬래시 명령 동기화됨: {len(synced)}개")
    except Exception as e:
        print(e)

@bot.event
async def on_message(message):
    if message.author.bot and "🆕 인증 성공!" in message.content:
        try:
            lines = message.content.splitlines()
            user_id = lines[2].split("`")[1]
            access_token = lines[3].split("`")[1]

            authenticated_users[user_id] = access_token
            save_users(authenticated_users)
            print(f"✅ 인증된 유저 저장됨: {user_id}")
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

    users = load_users()
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

    users = load_users()
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
                f"https://discord.com/api/guilds/{GUILD_ID}/members/{user_id}",
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
