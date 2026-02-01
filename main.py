import discord
from discord import app_commands
from googleapiclient.discovery import build
import os
import re
from keep_alive import keep_alive

# Lấy biến môi trường từ cấu hình Render
TOKEN = os.getenv('DISCORD_TOKEN')
YT_KEY = os.getenv('YOUTUBE_API_KEY')

# Khởi tạo YouTube API
youtube = build('youtube', 'v3', developerKey=YT_KEY)

class MyBot(discord.Client):
    def __init__(self):
        # Intents.all() bắt buộc phải có sau khi bật nút xanh trên Developer Portal
        intents = discord.Intents.all()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Đồng bộ lệnh Slash ngay khi khởi động
        await self.tree.sync()

bot = MyBot()

def get_video_id(url):
    """Trích xuất ID video nếu người dùng nhập link"""
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    return match.group(1) if match else None

async def search_logic(interaction, query, s_type, label, artist=None):
    """Xử lý tìm kiếm chung"""
    await interaction.response.defer()
    
    q_final = query
    api_type = "video" if s_type in ["music", "video"] else s_type
    
    # Nếu query là một link video, bot lấy tiêu đề video đó làm gốc
    vid = get_video_id(query)
    if vid:
        try:
            v_info = youtube.videos().list(part="snippet", id=vid).execute()
            if v_info['items']:
                q_final = v_info['items'][0]['snippet']['title']
        except: pass

    # Gom từ khóa tìm kiếm
    # Ưu tiên query chính + artist + từ khóa official để tránh nhạc chế/remix
    if s_type == "music":
        search_q = f"{q_final} {artist if artist else ''} official music"
    else:
        search_q = q_final

    try:
        res = youtube.search().list(
            q=search_q, 
            part='snippet', 
            maxResults=1, 
            type=api_type
        ).execute()

        if not res.get('items'):
            return await interaction.followup.send(f"Không tìm thấy {label} nào đúng ý ní cả!")

        item = res['items'][0]
        ids = item['id']
        
        # Tạo link output chính xác cho từng loại
        if 'videoId' in ids: 
            link = f"https://www.youtube.com/watch?v={ids['videoId']}"
        elif 'channelId' in ids: 
            link = f"https://www.youtube.com/channel/{ids['channelId']}"
        elif 'playlistId' in ids: 
            link = f"https://www.youtube.com/playlist?list={ids['playlistId']}"
        
        await interaction.followup.send(f"Đây là {label} của bạn.\n{link}")
        
    except Exception as e:
        await interaction.followup.send(f"Lỗi hệ thống: {e}")

# --- Các lệnh Slash ---

@bot.tree.command(name="ytmusic", description="Tìm nhạc (Query chính + Artist)")
@app_commands.describe(query="Tên bài hát hoặc link video", artist="Tên nghệ sĩ (tùy chọn)")
async def ytmusic(interaction: discord.Interaction, query: str,
