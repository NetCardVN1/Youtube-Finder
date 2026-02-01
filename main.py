import discord
from discord import app_commands
from googleapiclient.discovery import build
import re
import os
from keep_alive import keep_alive

# Lấy Token và Key từ biến môi trường (Thiết lập trên Render)
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# Khởi tạo YouTube API
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

class YTSearchBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Đồng bộ lệnh Slash với Discord
        await self.tree.sync()

bot = YTSearchBot()

def extract_video_id(url):
    """Lấy ID video từ link YouTube"""
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    return match.group(1) if match else None

async def handle_search(interaction, query, s_type, label):
    await interaction.response.defer()
    
    final_query = query
    api_type = "video" if s_type in ["video", "music"] else s_type
    
    # Nếu người dùng dán link vào lệnh ytmusic, bot sẽ tìm tiêu đề video đó trước
    v_id = extract_video_id(query)
    if v_id and s_type == "music":
        try:
            v_info = youtube.videos().list(part="snippet", id=v_id).execute()
            if v_info['items']:
                final_query = v_info['items'][0]['snippet']['title']
        except: pass

    # Tối ưu tìm kiếm
    search_q = f"{final_query} music" if s_type == "music" else final_query

    try:
        res = youtube.search().list(
            q=search_q, 
            part='snippet', 
            maxResults=1, 
            type=api_type
        ).execute()

        if not res.get('items'):
            return await interaction.followup.send(f"Không tìm thấy {label} nào cả ní ơi!")

        item = res['items'][0]
        ids = item['id']
        
        # Tạo link tương ứng
        if 'videoId' in ids: link = f"https://www.youtube.com/watch?v={ids['videoId']}"
        elif 'channelId' in ids: link = f"https://www.youtube.com/channel/{ids['channelId']}"
        elif 'playlistId' in ids: link = f"https://www.youtube.com/playlist?list={ids['playlistId']}"
        
        await interaction.followup.send(f"Đây là {label} của bạn.\n{link}")
    except Exception as e:
        await interaction.followup.send(f"Lỗi rồi ní: {e}")

# --- Các lệnh Slash ---

@bot.tree.command(name="ytmusic", description="Tìm nhạc từ tên hoặc dán link video chứa nhạc")
async def ytmusic(interaction: discord.Interaction, query: str):
    await handle_search(interaction, query, "music", "music")

@bot.tree.command(name="ytvideo", description="Tìm video YouTube")
async def ytvideo(interaction: discord.Interaction, query: str):
    await handle_search(interaction, query, "video", "video")

@bot.tree.command(name="ytchannel", description="Tìm kênh YouTube")
async def ytchannel(interaction: discord.Interaction, query: str):
    await handle_search(interaction, query, "channel", "channel")

@bot.tree.command(name="ytplaylist", description="Tìm danh sách phát")
async def ytplaylist(interaction: discord.Interaction, query: str):
    await handle_search(interaction, query, "playlist", "playlist")

@bot.event
async def on_ready():
    print(f'Bot {bot.user} đã sẵn sàng phục vụ ní!')

# Chạy web server và Bot
keep_alive()
bot.run(DISCORD_TOKEN)

