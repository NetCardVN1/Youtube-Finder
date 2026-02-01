import discord
from discord import app_commands
from googleapiclient.discovery import build
import os
import re
from keep_alive import keep_alive

# 1. Lấy thông tin từ Environment Variables trên Render
TOKEN = os.getenv('DISCORD_TOKEN')
YT_KEY = os.getenv('YOUTUBE_API_KEY')

# 2. Khởi tạo YouTube API
youtube = build('youtube', 'v3', developerKey=YT_KEY)

# 3. Cấu hình Bot với các Intents cụ thể (Khớp với hình ní gửi)
class MyBot(discord.Client):
    def __init__(self):
        # Thiết lập các quyền hạn ní đã bật xanh trong ảnh
        intents = discord.Intents.default()
        intents.message_content = True  # Quyền đọc nội dung lệnh
        intents.members = True          # Quyền xem thành viên
        intents.presences = True        # Quyền trạng thái online
        
        super().__init__(intents=intents)
        # Tree để quản lý các lệnh Slash (/)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Đồng bộ lệnh Slash với Discord ngay khi khởi động
        await self.tree.sync()
        print("--- ĐÃ ĐỒNG BỘ LỆNH SLASH (/) ---")

bot = MyBot()

# --- Các hàm bổ trợ ---

def get_video_id(url):
    """Trích xuất ID nếu người dùng dán link video"""
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    return match.group(1) if match else None

async def search_logic(interaction, query, s_type, label, artist=None):
    """Xử lý tìm kiếm và trả kết quả"""
    await interaction.response.defer()
    
    q_final = query
    api_type = "video" if s_type in ["music", "video"] else s_type
    
    # Nếu query là link, lấy tiêu đề video đó làm gốc
    vid = get_video_id(query)
    if vid:
        try:
            v_info = youtube.videos().list(part="snippet", id=vid).execute()
            if v_info['items']:
                q_final = v_info['items'][0]['snippet']['title']
        except: pass

    # Tinh chỉnh từ khóa tìm kiếm
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
        
        # Tạo link output
        if 'videoId' in ids: 
            link = f"https://www.youtube.com/watch?v={ids['videoId']}"
        elif 'channelId' in ids: 
            link = f"https://www.youtube.com/channel/{ids['channelId']}"
        elif 'playlistId' in ids: 
            link = f"https://www.youtube.com/playlist?list={ids['playlistId']}"
        
        await interaction.followup.send(f"Đây là {label} của bạn.\n{link}")
        
    except Exception as e:
        await interaction.followup.send(f"Lỗi: {e}")

# --- Các lệnh Slash ---

@bot.tree.command(name="ytmusic", description="Tìm nhạc (Query chính + Artist)")
@app_commands.describe(query="Tên bài hoặc link video", artist="Tên nghệ sĩ (tùy chọn)")
async def ytmusic(interaction: discord.Interaction, query: str, artist: str = None):
    await search_logic(interaction, query, "music", "music", artist)

@bot.tree.command(name="ytvideo", description="Tìm video YouTube")
async def ytvideo(interaction: discord.Interaction, query: str):
    await search_logic(interaction, query, "video", "video")

@bot.tree.command(name="ytchannel", description="Tìm kênh YouTube")
async def ytchannel(interaction: discord.Interaction, query: str):
    await search_logic(interaction, query, "channel", "channel")

@bot.tree.command(name="ytplaylist", description="Tìm danh sách phát")
async def ytplaylist(interaction: discord.Interaction, query: str):
    await search_logic(interaction, query, "playlist", "playlist")

@bot.event
async def on_ready():
    # Khi thấy dòng này trong Log Render là bot đã Online thành công
    print(f'--- ĐÃ ONLINE: {bot.user} ---')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/ytmusic"))

# 4. Chạy server Flask để Render không "ngủ gật"
keep_alive()

# 5. Khởi động Bot
if TOKEN and YT_KEY:
    try:
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        print("LỖI: Token không hợp lệ. Hãy Reset Token trên Discord Dev Portal!")
else:
    print("THIẾU BIẾN MÔI TRƯỜNG! Hãy kiểm tra DISCORD_TOKEN và YOUTUBE_API_KEY trên Render.")
