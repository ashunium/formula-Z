import discord
from discord.ext import commands
import random
import asyncio
from discord.ui import View, Button
import json
import atexit
import os
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("F1Bot")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

TRACKS_INFO = {
    "Australia": {"base_lap_time": 96.5, "laps": 58, "conditions": {"speed": "Medium", "acceleration": "Medium", "overtaking": "Medium", "corners": "Moderate"}},
    "China": {"base_lap_time": 92.7, "laps": 56, "conditions": {"speed": "Medium", "acceleration": "High", "overtaking": "Medium", "corners": "Moderate"}},
    "Japan": {"base_lap_time": 87.6, "laps": 53, "conditions": {"speed": "Medium", "acceleration": "Medium", "overtaking": "Medium", "corners": "Many"}},
    "Bahrain": {"base_lap_time": 93.8, "laps": 57, "conditions": {"speed": "High", "acceleration": "Medium", "overtaking": "Easy", "corners": "Moderate"}},
    "Saudi Arabia": {"base_lap_time": 90.0, "laps": 50, "conditions": {"speed": "High", "acceleration": "Low", "overtaking": "Easy", "corners": "Few"}},
    "Miami": {"base_lap_time": 91.8, "laps": 57, "conditions": {"speed": "Medium", "acceleration": "Medium", "overtaking": "Medium", "corners": "Moderate"}},
    "Imola": {"base_lap_time": 93.2, "laps": 63, "conditions": {"speed": "Medium", "acceleration": "Medium", "overtaking": "Hard", "corners": "Many"}},
    "Monaco": {"base_lap_time": 73.3, "laps": 78, "conditions": {"speed": "Low", "acceleration": "Low", "overtaking": "Hard", "corners": "Many"}},
    "Spain": {"base_lap_time": 85.5, "laps": 66, "conditions": {"speed": "Medium", "acceleration": "High", "overtaking": "Medium", "corners": "Moderate"}},
    "Canada": {"base_lap_time": 69.0, "laps": 70, "conditions": {"speed": "High", "acceleration": "Medium", "overtaking": "Easy", "corners": "Few"}},
    "Austria": {"base_lap_time": 67.2, "laps": 71, "conditions": {"speed": "High", "acceleration": "High", "overtaking": "Easy", "corners": "Few"}},
    "UK": {"base_lap_time": 90.3, "laps": 52, "conditions": {"speed": "High", "acceleration": "Medium", "overtaking": "Easy", "corners": "Moderate"}},
    "Belgium": {"base_lap_time": 102.0, "laps": 44, "conditions": {"speed": "High", "acceleration": "High", "overtaking": "Medium", "corners": "Moderate"}},
    "Hungary": {"base_lap_time": 71.5, "laps": 70, "conditions": {"speed": "Low", "acceleration": "Low", "overtaking": "Hard", "corners": "Many"}},
    "Netherlands": {"base_lap_time": 67.1, "laps": 72, "conditions": {"speed": "Low", "acceleration": "Medium", "overtaking": "Hard", "corners": "Many"}},
    "Monza": {"base_lap_time": 83.6, "laps": 53, "conditions": {"speed": "High", "acceleration": "Medium", "overtaking": "Easy", "corners": "Few"}},
    "Azerbaijan": {"base_lap_time": 95.0, "laps": 51, "conditions": {"speed": "High", "acceleration": "Low", "overtaking": "Medium", "corners": "Moderate"}},
    "Singapore": {"base_lap_time": 88.0, "laps": 61, "conditions": {"speed": "Low", "acceleration": "Low", "overtaking": "Hard", "corners": "Many"}},
    "Austin": {"base_lap_time": 85.7, "laps": 56, "conditions": {"speed": "Medium", "acceleration": "High", "overtaking": "Easy", "corners": "Moderate"}},
    "Mexico": {"base_lap_time": 67.6, "laps": 71, "conditions": {"speed": "Medium", "acceleration": "Medium", "overtaking": "Medium", "corners": "Moderate"}},
    "Brazil": {"base_lap_time": 73.0, "laps": 71, "conditions": {"speed": "Medium", "acceleration": "High", "overtaking": "Medium", "corners": "Moderate"}},
    "Las Vegas": {"base_lap_time": 89.5, "laps": 50, "conditions": {"speed": "High", "acceleration": "Low", "overtaking": "Easy", "corners": "Few"}},
    "Qatar": {"base_lap_time": 91.2, "laps": 57, "conditions": {"speed": "High", "acceleration": "Medium", "overtaking": "Medium", "corners": "Moderate"}},
    "Abu Dhabi": {"base_lap_time": 90.6, "laps": 55, "conditions": {"speed": "Medium", "acceleration": "Medium", "overtaking": "Medium", "corners": "Moderate"}}
}

WEATHER_OPTIONS = ["☀️ Sunny", "🌦️ Light Rain", "🌧️ Heavy Rain", "☁️ Cloudy", "🌬️ Windy"]

F1_POINTS = {
    1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1
}

AUTHORIZED_TM_USERS = [
    851188509501947924,
    721698800980197446,
    1323664472463642624,
    785052256428883990,
]

lobbies = {}
career_stats = {}
default_player_profile = {
    "races": 0, "wins": 0, "podiums": 0, "dnfs": 0, "fastest_lap": None, "total_time": 0.0,
    "points": 0, "zcoins": 0, "last_daily": 0, "last_weekly": 0, "last_monthly": 0,
    "car_parts": {
        "engine": 5,
        "aero": 5,
        "tyres": 5,
        "chassis": 5,
        "gearbox": 5,
        "suspension": 5
    },
    "part_upgrade_counts": {
        "engine": 0,
        "aero": 0,
        "tyres": 0,
        "chassis": 0,
        "gearbox": 0,
        "suspension": 0
    },
    "tournament_stats": {
        "points": 0, "wins": 0, "podiums": 0
    }
}

async def safe_send(channel, content=None, embed=None, retries=3, delay=5):
    for attempt in range(retries):
        try:
            if embed:
                await channel.send(embed=embed)
            elif content:
                await channel.send(content)
            return
        except (discord.HTTPException, discord.Forbidden) as e:
            if e.status == 429:
                logger.warning(f"Rate limited, retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logger.error(f"Failed to send message: {e}")
                return
    logger.warning(f"Failed to send message after {retries} retries")

def get_player_profile(user_id):
    user_id = int(user_id)
    if user_id not in career_stats:
        career_stats[user_id] = default_player_profile.copy()
    profile = career_stats[user_id]
    for key, value in default_player_profile.items():
        if key not in profile:
            profile[key] = value
        elif isinstance(value, dict):
            for subkey, subvalue in value.items():
                if subkey not in profile[key]:
                    profile[key][subkey] = subvalue
    save_career_stats()
    return profile

def save_career_stats():
    try:
        if not career_stats:
            logger.warning("Skipping save: career_stats is empty")
            return
        temp_file = "career_stats_temp.json"
        with open(temp_file, "w") as f:
            json.dump(career_stats, f, indent=2)
        if os.path.exists("career_stats.json"):
            os.replace("career_stats.json", "career_stats_backup.json")
        os.replace(temp_file, "career_stats.json")
        logger.info(f"💾 Saved career_stats.json (Size: {os.path.getsize('career_stats.json')} bytes)")
    except (IOError, OSError) as e:
        logger.error(f"Failed to save career_stats.json: {e}")
        if os.path.exists("career_stats_backup.json"):
            os.replace("career_stats_backup.json", "career_stats.json")
            logger.info("Restored career_stats.json from backup")

def load_career_stats():
    global career_stats
    try:
        if os.path.exists("career_stats.json"):
            with open("career_stats.json", "r") as f:
                file_content = f.read()
                if not file_content.strip():  # Check for empty file
                    logger.warning("career_stats.json is empty, starting fresh")
                    career_stats = {}
                    return
                data = json.loads(file_content)
                career_stats = {int(k): v for k, v in data.items()}
                # Ensure all profiles have necessary fields
                for user_id, profile in career_stats.items():
                    for key, value in default_player_profile.items():
                        if key not in profile:
                            profile[key] = value
                        elif isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                if subkey not in profile[key]:
                                    profile[key][subkey] = subvalue
                logger.info(f"✅ Loaded career_stats.json (Entries: {len(career_stats)})")
                # Log a sample of the loaded data for debugging
                if career_stats:
                    sample_user = next(iter(career_stats))
                    logger.info(f"Sample data: User {sample_user} - {career_stats[sample_user]}")
        else:
            logger.info("ℹ️ career_stats.json not found, starting fresh")
            career_stats = {}
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"⚠️ Error loading career_stats.json: {e}, attempting backup")
        try:
            if os.path.exists("career_stats_backup.json"):
                with open("career_stats_backup.json", "r") as f:
                    file_content = f.read()
                    if not file_content.strip():
                        logger.warning("career_stats_backup.json is empty, starting fresh")
                        career_stats = {}
                        return
                    data = json.loads(file_content)
                    career_stats = {int(k): v for k, v in data.items()}
                    # Ensure all profiles have necessary fields
                    for user_id, profile in career_stats.items():
                        for key, value in default_player_profile.items():
                            if key not in profile:
                                profile[key] = value
                            elif isinstance(value, dict):
                                for subkey, subvalue in value.items():
                                    if subkey not in profile[key]:
                                        profile[key][subkey] = subvalue
                    logger.info("✅ Loaded career_stats_backup.json")
                    # Log a sample of the loaded data
                    if career_stats:
                        sample_user = next(iter(career_stats))
                        logger.info(f"Sample data from backup: User {sample_user} - {career_stats[sample_user]}")
            else:
                logger.info("ℹ️ No backup found, starting fresh")
                career_stats = {}
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"❌ Failed to load backup: {e}, starting fresh")
            career_stats = {}

async def on_timeout(self):
    await self.message.edit(content="🛞 Pit stop cancelled: No tyre selected in time.", view=None)

def format_race_time(seconds):
    if not seconds:
        return "N/A"
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    millis = int((secs % 1) * 1000)
    return f"{int(hours)}:{int(minutes):02}:{int(secs):02}.{millis:03}"

def format_cooldown(seconds):
    if seconds <= 0:
        return "Ready to claim!"
    hours, remainder = divmod(int(seconds), 3600)
    minutes = remainder // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def get_zcoin_emoji(ctx):
    try:
        emoji = ctx.bot.get_emoji(1379843253641285723)
        return str(emoji) if emoji else "Zcoins"
    except Exception:
        return "Zcoins"

def migrate_to_car_parts():
    global career_stats
    try:
        with open("career_stats.json", "r") as f:
            career_stats = json.load(f)
    except FileNotFoundError:
        career_stats = {}
        logger.info("No career_stats.json found, starting fresh.")
        return
    for user_id, stats in career_stats.items():
        user_id = int(user_id)
        if "car_parts" not in stats:
            stats["car_parts"] = {
                "engine": 5, "aero": 5, "tyres": 5,
                "chassis": 5, "gearbox": 5, "suspension": 5
            }
        if "part_upgrade_counts" not in stats:
            stats["part_upgrade_counts"] = {
                "engine": 0, "aero": 0, "tyres": 0,
                "chassis": 0, "gearbox": 0, "suspension": 0
            }
        if "tournament_stats" not in stats:
            stats["tournament_stats"] = {
                "points": 0, "wins": 0, "podiums": 0
            }
        for key in ["races", "wins", "podiums", "dnfs", "points", "zcoins"]:
            if key not in stats:
                stats[key] = 0
        if "total_time" not in stats:
            stats["total_time"] = 0.0
        if "fastest_lap" not in stats:
            stats["fastest_lap"] = None
        for key in ["last_daily", "last_weekly", "last_monthly"]:
            if key not in stats:
                stats[key] = 0
    try:
        with open("career_stats.json", "w") as f:
            json.dump(career_stats, f, indent=4)
        logger.info("Migration to car parts and tournament stats completed successfully!")
    except Exception as e:
        logger.error(f"Migration failed: {e}")

def apply_track_conditions(lobby, player_data, strategy):
    conditions = lobby["conditions"]
    pid = None
    for player_id, data in lobby["player_data"].items():
        if data == player_data:
            pid = player_id
            break
    if pid is None:
        logger.error(f"Player data not found in lobby {lobby.get('channel_id', 'unknown')}")
        raise ValueError("Player not found in lobby")
    profile = get_player_profile(pid)
    # Compute stats from car parts
    stats = {
        "top_speed": 0,
        "acceleration": 0,
        "overtaking": 0,
        "cornering": 0,
        "tyre_management": 0,
        "reliability": 0
    }
    # Apply part contributions with exponential scaling
    scaling_factor = 1.0 
    stats["top_speed"] += (profile["car_parts"]["engine"] - 5) / 5 * 8 * scaling_factor
    scaling_factor = 1.0 
    stats["acceleration"] += (profile["car_parts"]["engine"] - 5) / 5 * 4 * scaling_factor
    scaling_factor = 1.0 
    stats["acceleration"] += (profile["car_parts"]["gearbox"] - 5) / 5 * 4 * scaling_factor
    scaling_factor = 1.0 
    stats["overtaking"] += (profile["car_parts"]["aero"] - 5) / 5 * 6 * scaling_factor
    stats["cornering"] += (profile["car_parts"]["aero"] - 5) / 5 * 4 * scaling_factor
    scaling_factor = 1.0 
    stats["cornering"] += (profile["car_parts"]["chassis"] - 5) / 5 * 2 * scaling_factor
    scaling_factor = 1.0 
    stats["cornering"] += (profile["car_parts"]["suspension"] - 5) / 5 * 4 * scaling_factor
    scaling_factor = 1.0 
    stats["tyre_management"] += (profile["car_parts"]["tyres"] - 5) / 5 * 8 * scaling_factor
    scaling_factor = 1.0 
    stats["tyre_management"] += (profile["car_parts"]["suspension"] - 5) / 5 * 4 * scaling_factor
    scaling_factor = 1.0 
    stats["reliability"] += (profile["car_parts"]["chassis"] - 5) / 5 * 6 * scaling_factor
    scaling_factor = 1.0 
    stats["reliability"] += (profile["car_parts"]["gearbox"] - 5) / 5 * 4 * scaling_factor
    
    # Speed: Adjusts base lap time
    speed_multipliers = {"High": 0.97, "Medium": 1.00, "Low": 1.03}
    speed_multiplier = speed_multipliers.get(conditions["speed"], 1.00)
    top_speed_mod = 1.0 - (stats["top_speed"] / 100.0) * 0.035 * (1 if conditions["speed"] == "High" else 0.5)
    speed_multiplier *= top_speed_mod
    
    # Acceleration: Adjusts fuel usage
    accel_multipliers = {"High": 1.20, "Medium": 1.00, "Low": 0.80}
    accel_multiplier = accel_multipliers.get(conditions["acceleration"], 1.00)
    accel_mod = 1.0 - (stats["acceleration"] / 100.0) * 0.20 * (1 if conditions["acceleration"] == "High" else 0.5)
    accel_multiplier *= accel_mod
    
    # Overtaking: Adjusts driver variance
    overtaking_ranges = {
        "Easy": (0.95, 1.05),
        "Medium": (0.97, 1.03),
        "Hard": (0.99, 1.01)
    }
    base_min, base_max = overtaking_ranges.get(conditions["overtaking"], (0.99, 1.01))
    overtaking_mod = stats["overtaking"] / 100.0
    variance_min = base_min - (0.015 * overtaking_mod if conditions["overtaking"] == "Easy" else 0.008 * overtaking_mod)
    variance_max = base_max + (0.015 * overtaking_mod if conditions["overtaking"] == "Easy" else 0.008 * overtaking_mod)
    
    # Corners: Adjusts tyre wear
    corner_tyre_wear = {"Few": 1.0, "Moderate": 1.1, "Many": 1.2}
    tyre_wear_multiplier = corner_tyre_wear.get(conditions["corners"], 1.0)
    cornering_mod = 1.0 - (stats["cornering"] / 100.0) * 0.20 * (1 if conditions["corners"] == "Many" else 0.5)
    tyre_wear_multiplier *= cornering_mod
    
    # Tyre Management: Global tyre wear reduction
    tyre_management_mod = 1.0 - (stats["tyre_management"] / 100.0) * 0.15
    
    # Crash risks
    collision_risks = {
        "Easy": 0.003 if strategy == "Push" else 0.001,  # Reduced for balance
        "Medium": 0.007 if strategy == "Push" else 0.004,
        "Hard": 0.010 if strategy == "Push" else 0.006
    }
    reliability_mod = max(0, 1.0 - (stats["reliability"] / 100.0) * 0.75)  # Cap at 0
    crash_risks = {
        "Collision": collision_risks.get(conditions["overtaking"], 0.002) * reliability_mod,
        "Engine Failure": {"Few": 0.0, "Moderate": 0.001, "Many": 0.002}.get(conditions["corners"], 0.001) * reliability_mod,
        "Gearbox Issue": {"Few": 0.0, "Moderate": 0.001, "Many": 0.002}.get(conditions["corners"], 0.001) * reliability_mod
    }
    
    return speed_multiplier, accel_multiplier, variance_min, variance_max, tyre_wear_multiplier * tyre_management_mod, crash_risks["Collision"], crash_risks["Engine Failure"], crash_risks["Gearbox Issue"]

@bot.command()
async def create(ctx):
    channel_id = ctx.channel.id
    user_id = ctx.author.id
    if channel_id in lobbies:
        await ctx.send("⚠️ A race lobby already exists in this channel.")
        return
    track_name = random.choice(list(TRACKS_INFO.keys()))
    initial_weather = random.choice(WEATHER_OPTIONS)
    track_info = TRACKS_INFO[track_name]
    has_weather_change = random.random() < 0.4
    weather_window = {}
    if has_weather_change:
        total_laps = track_info["laps"]
        start = random.randint(total_laps // 3, total_laps // 2)
        end = random.randint(start + 3, min(total_laps, start + 10))
        new_weather = random.choice([w for w in WEATHER_OPTIONS if w != initial_weather])
        weather_window = {"start": start, "end": end, "new_weather": new_weather}
    lobbies[channel_id] = {
        "host": user_id, "track": track_name, "conditions": TRACKS_INFO[track_name]["conditions"],
        "weather": initial_weather, "initial_weather": initial_weather,
        "weather_window": weather_window, "players": [user_id], "users": {user_id: ctx.author},
        "status": "waiting", "mode": "solo", "teams": [], "team_names": {}, "initial_settings": {}, "race_mode": "casual"
    }
    
    embed = discord.Embed(
        title="🏎️ New Race Lobby Created!",
        description=f"✦ {ctx.author.mention} has started a race lobby! ✦",
        color=discord.Color.green()
    )
    embed.add_field(
        name="Track",
        value=f"🏁 **{track_name}** — Lap Time: {track_info['base_lap_time']}s, Laps: {track_info['laps']}",
        inline=False
    )
    embed.add_field(
        name="Conditions",
        value=(
            f"⚡ Speed: {track_info['conditions']['speed']} | 🛞 Accel: {track_info['conditions']['acceleration']}\n"
            f"🏎️ Overtake: {track_info['conditions']['overtaking']} | 🔄 Corners: {track_info['conditions']['corners']}"
        ),
        inline=False
    )
    embed.add_field(name="Weather", value=initial_weather, inline=True)
    embed.add_field(name="Mode", value="Solo", inline=True)
    embed.set_footer(text="🏆 Join with !join")
    if weather_window:
        embed.add_field(
            name="Weather Forecast",
            value=f"Change to **{new_weather}** expected from **Lap {start} to {end}**",
            inline=False
        )
    embed.set_footer(text="Use !join to enter the race")
    await ctx.send(embed=embed)

@bot.command()
async def set(ctx, *, track_name: str):
    channel_id = ctx.channel.id
    user_id = ctx.author.id
    if channel_id not in lobbies:
        await ctx.send("❌ There's no active race lobby in this channel.")
        return
    lobby = lobbies[channel_id]
    if lobby["host"] != user_id:
        await ctx.send("🚫 Only the host can set the track.")
        return
    if track_name not in TRACKS_INFO:
        possible_tracks = [t for t in TRACKS_INFO if track_name.lower() in t.lower()]
        suggestion = f" Did you mean: {', '.join(possible_tracks)}?" if possible_tracks else ""
        await ctx.send(f"⚠️ Invalid track name.{suggestion}")
        return
    # Update track and conditions
    lobby["track"] = track_name
    lobby["conditions"] = TRACKS_INFO[track_name]["conditions"]
    # Reset weather and weather window, similar to !create
    initial_weather = random.choice(WEATHER_OPTIONS)
    track_info = TRACKS_INFO[track_name]
    has_weather_change = random.random() < 0.4
    weather_window = {}
    if has_weather_change:
        total_laps = track_info["laps"]
        start = random.randint(total_laps // 3, total_laps // 2)
        end = random.randint(start + 3, min(total_laps, start + 10))
        new_weather = random.choice([w for w in WEATHER_OPTIONS if w != initial_weather])
        weather_window = {"start": start, "end": end, "new_weather": new_weather}
    lobby["weather"] = initial_weather
    lobby["initial_weather"] = initial_weather
    lobby["weather_window"] = weather_window
    # Create embed for response
    embed = discord.Embed(
        title=f"🏁 Track Updated",
        description=f"✦ Set to **{track_name}** by {ctx.author.mention} ✦",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Track",
        value=f"🏁 **{track_name}** — Lap Time: {track_info['base_lap_time']}s, Laps: {track_info['laps']}",
        inline=False
    )
    embed.add_field(
        name="Conditions",
        value=(
            f"⚡ Speed: {track_info['conditions']['speed']} | 🛞 Accel: {track_info['conditions']['acceleration']}\n"
            f"🏎️ Overtake: {track_info['conditions']['overtaking']} | 🔄 Corners: {track_info['conditions']['corners']}"
        ),
        inline=False
    )
    embed.add_field(name="Weather", value=initial_weather, inline=True)
    if weather_window:
        embed.add_field(
            name="Weather Forecast",
            value=f"Change to **{new_weather}** expected from **Lap {start} to {end}**",
            inline=False
        )
    embed.set_footer(text="🏆 Track set for racing!")
    await ctx.send(embed=embed)

@bot.command()
async def tracks(ctx):
    def create_track_page(page, tracks_per_page=8):
        start = page * tracks_per_page
        end = min(start + tracks_per_page, len(TRACKS_INFO))
        embed = discord.Embed(
            title=f"Available Tracks (*Page {page + 1}/{len(TRACKS_INFO) // tracks_per_page + (1 if len(TRACKS_INFO) % tracks_per_page else 0)}*)",
            description="✦ Choose your circuit! ✦",
            color=discord.Color.blue()
        )
        track_list = []
        for track, info in list(TRACKS_INFO.items())[start:end]:
            conditions = info["conditions"]
            track_list.append(
                f"🏁 **{track}** — Lap Time: {info['base_lap_time']}s, Laps: {info['laps']}\n"
                f"   ⚡ Speed: {conditions['speed']} | 🛞 Accel: {conditions['acceleration']}\n"
                f"   🏎️ Overtake: {conditions['overtaking']} | 🔄 Corners: {conditions['corners']}\n"
                f"—"
            )
        embed.add_field(name="Tracks", value="\n".join(track_list)[:-1], inline=False)  # Remove trailing —
        embed.set_footer(text="🏆 Use !set <track> to choose a track (host only)")
        return embed

    class TrackPagesView(discord.ui.View):
        def __init__(self, ctx, current_page, total_pages):
            super().__init__(timeout=60)
            self.ctx = ctx
            self.current_page = current_page
            self.total_pages = total_pages
            self.update_buttons()

        def update_buttons(self):
            self.prev_button.disabled = self.current_page == 0
            self.next_button.disabled = self.current_page == self.total_pages - 1
            self.page_label.label = f"Page {self.current_page + 1}/{self.total_pages}"

        async def update_message(self, interaction):
            embed = create_track_page(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)

        @discord.ui.button(label="⬅️", style=discord.ButtonStyle.green)
        async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page > 0:
                self.current_page -= 1
                self.update_buttons()
                await self.update_message(interaction)

        @discord.ui.button(label="Page 1/3", style=discord.ButtonStyle.grey, disabled=True)
        async def page_label(self, interaction: discord.Interaction, button: discord.ui.Button):
            pass  # Disabled, no interaction

        @discord.ui.button(label="➡️", style=discord.ButtonStyle.green)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page < self.total_pages - 1:
                self.current_page += 1
                self.update_buttons()
                await self.update_message(interaction)

    tracks_per_page = 8
    total_pages = len(TRACKS_INFO) // tracks_per_page + (1 if len(TRACKS_INFO) % tracks_per_page else 0)
    view = TrackPagesView(ctx, 0, total_pages)
    embed = create_track_page(0)
    await ctx.send(embed=embed, view=view)

@bot.command()
async def join(ctx):
    channel_id = ctx.channel.id
    user_id = ctx.author.id
    if channel_id not in lobbies:
        await ctx.send("❌ No active race lobby in this channel. Use `!create` to start one.")
        return
    lobby = lobbies[channel_id]
    if lobby["status"] != "waiting":
        await ctx.send("⚠️ This race has already started.")
        return
    if user_id in lobby["players"]:
        await ctx.send("🙃 You're already in this race.")
        return
    MAX_PLAYERS = 20
    if len(lobby["players"]) >= MAX_PLAYERS:
        await ctx.send("🚗 This race is full!")
        return
    lobby["players"].append(user_id)
    lobby["users"][user_id] = ctx.author
    await ctx.send(f"✅ {ctx.author.mention} joined the race at **{lobby['track']}**!")

@bot.command()
async def leave(ctx):
    channel_id = ctx.channel.id
    user_id = ctx.author.id
    if channel_id not in lobbies:
        await ctx.send("❌ There's no active race lobby in this channel.")
        return
    lobby = lobbies[channel_id]
    if user_id not in lobby["players"]:
        await ctx.send("🙃 You're not part of this race.")
        return
    if lobby["status"] != "waiting":
        await ctx.send("🚫 You can't leave the race after it has started!")
        return
    lobby["players"].remove(user_id)
    if user_id == lobby["host"]:
        await ctx.send("⚠️ The host left. Race lobby is closed.")
        del lobbies[channel_id]
        return
    if not lobby["players"]:
        await ctx.send("🏁 All players have left. The race lobby is now closed.")
        del lobbies[channel_id]
        return
    await ctx.send(f"👋 {ctx.author.mention} left the race lobby.")

@bot.command()
async def start(ctx):
    channel_id = ctx.channel.id
    user_id = ctx.author.id
    if channel_id not in lobbies:
        embed = discord.Embed(
            title="❌ No Lobby Found",
            description="There’s no active race lobby in this channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    lobby = lobbies[channel_id]
    if user_id != lobby["host"]:
        embed = discord.Embed(
            title="🚫 Permission Denied",
            description="Only the host can start the race.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    if lobby["status"] != "waiting":
        embed = discord.Embed(
            title="⚠️ Race Already Started",
            description="This race has already begun.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    if len(lobby["players"]) < 2:
        embed = discord.Embed(
            title="❌ Not Enough Players",
            description="You need at least 2 players to start the race.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    lobby["safety_car_active"] = False
    lobby["safety_car_laps"] = 0
    lobby["laps"] = TRACKS_INFO[lobby["track"]]["laps"]
    lobby["status"] = "in_progress"
    lobby["current_lap"] = 1
    lobby["position_order"] = random.sample(lobby["players"], len(lobby["players"]))
    track = TRACKS_INFO[lobby["track"]]
    total_laps = track["laps"]
    lobby["player_data"] = {}
    for pid in lobby["players"]:
        try:
            user = await bot.fetch_user(pid)
            logger.info(f"✅ Successfully fetched user {pid}: {user.name}")
            lobby["users"][pid] = user
            initial_tyre = "Medium"
            initial_strategy = "Balanced"
            if "initial_settings" in lobby and pid in lobby["initial_settings"]:
                initial_tyre = lobby["initial_settings"][pid]["tyre"]
                initial_strategy = lobby["initial_settings"][pid]["strategy"]
            lobby["player_data"][pid] = {
                "strategy": initial_strategy,
                "tyre": initial_tyre,
                "last_pit_lap": 0,
                "total_time": 0.0,
                "fuel": 100.0,
                "tyre_condition": 100.0,
                "dnf": False,
                "dnf_reason": None,
                "lap_times": [],
                "last_sent_lap": 0,
                "last_sent_fuel": 100.0,
                "last_sent_tyre": 100.0,
                "last_position": "?"
            }
            view = StrategyPanelView(pid, channel_id)
            position = lobby["position_order"].index(pid) + 1
            total = len(lobby["players"])
            embed = discord.Embed(
                title="📊 Strategy Panel",
                description=(
                    f"Adjust your racing strategy below using the buttons.\n\n"
                    f"📍 You are currently **P{position}** out of **{total}**."
                ),
                color=discord.Color.orange()
            )
            embed.add_field(
                name="Strategies",
                value="⚡ Push\n⚖️ Balanced\n🛟 Save\n🛞 Pit Stop",
                inline=False
            )
            embed.set_footer(text="Use this panel during the race to update your strategy.")
            try:
                dm_msg = await user.send(embed=embed, view=view)
                lobby["player_data"][pid]["dm_msg"] = dm_msg
            except discord.Forbidden:
                embed = discord.Embed(
                    title="⚠️ DMs Disabled",
                    description=f"{user.mention} has DMs disabled and won’t receive the strategy panel.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error creating strategy panel for user {pid}: {e}")
    lights_gif_embed = discord.Embed(
        title="🔴🔴🔴🔴🟢 Lights Out!",
        description="Get ready to race...",
        color=discord.Color.red()
    )
    lights_gif_embed.set_image(url="https://media.tenor.com/RtrDuGASCoMAAAAM/f1.gif")
    await ctx.send(embed=lights_gif_embed)
    await asyncio.sleep(7)
    embed = generate_race_status_embed(lobby)
    msg = await ctx.send(embed=embed)
    lobby["status_msg_id"] = msg.id
    bot.loop.create_task(race_loop(ctx, channel_id, msg, total_laps))

async def race_loop(ctx, channel_id, status_msg, total_laps):
    try:
        lap_delay = 5.0
        while channel_id in lobbies:
            lap_start_time = time.time()
            if channel_id not in lobbies:
                logger.warning(f"Lobby {channel_id} removed during race_loop")
                return
            lobby = lobbies.get(channel_id)
            if not lobby:
                logger.error(f"Lobby {channel_id} missing during race_loop")
                return
            current_lap = lobby.get("current_lap", 1)
            collision_occurred = False  # Track if any collision happens this lap
            window = lobby.get("weather_window", {})
            start = window.get("start")
            end = window.get("end")
            new_weather = window.get("new_weather")
            initial_weather = lobby.get("initial_weather", lobby["weather"])
            weather_updates = []
            if start is not None and end is not None and current_lap == start and lobby["weather"] != new_weather:
                lobby["weather"] = new_weather
                weather_updates.append(f"Weather has changed to {new_weather} on Lap {current_lap}!")
            elif end is not None and current_lap == end + 1 and lobby["weather"] != initial_weather:
                lobby["weather"] = initial_weather
                weather_updates.append(f"Weather has reverted to {initial_weather} on Lap {current_lap}!")
            if weather_updates:
                await safe_send(ctx, "\n".join(weather_updates))
            if current_lap > total_laps:
                break
            track = lobby.get("track")
            if track in TRACKS_INFO:
                base_lap_time = TRACKS_INFO[track]["base_lap_time"]
            else:
                logger.error(f"Invalid track {track} in lobby {channel_id}")
                base_lap_time = 100.0
            weather = lobby["weather"]
            player_times = {}
            for pid in lobby["players"]:
                pdata = lobby["player_data"].get(pid)
                if not pdata or pdata.get("dnf", False):
                    logger.debug(f"⏖ Skipping DNF player {pid}")
                    continue
                if pid not in lobby["users"]:
                    try:
                        user = await bot.fetch_user(pid)
                        lobby["users"][pid] = user
                    except (discord.NotFound, discord.HTTPException):
                        logger.warning(f"Failed to fetch user {pid}")
                        continue
                strategy = pdata.get("strategy", "Balanced")
                tyre = pdata.get("tyre", "Medium")
                just_pitted = False
                pit_penalty = 0
                last_pit_lap = pdata.get("last_pit_lap", -2)
                if strategy == "Pit Stop" and last_pit_lap != current_lap:
                    pit_penalty = 20.0
                    pdata["last_pit_lap"] = current_lap
                    just_pitted = True
                    logger.info(f"🛞 PIT STOP TRIGGERED for {pid} (User: {lobby['users'].get(pid, {'name': 'Unknown'}).name}) on lap {current_lap}, Penalty: {pit_penalty}s")
                    logger.debug(f"Before pit reset: Fuel={pdata.get('fuel')}, Tyre condition={pdata.get('tyre_condition')}")
                    pdata["fuel"] = 100.0
                    pdata["tyre_condition"] = 100.0
                    logger.debug(f"After pit reset: Fuel={pdata['fuel']}, Tyre condition={pdata['tyre_condition']}, Strategy reset to Balanced")
                    
                # Replace the degradation block starting with `if not just_pitted and not lobby.get("safety_car_active", False):`
                if not lobby.get("safety_car_active", False):
                    base_fuel_usage = {"Push": 6.0, "Balanced": 4.0, "Save": 2.0}.get(strategy, 4.0)
                    base_wear = {"Push": 8.0, "Balanced": 5.0, "Save": 3.0}.get(strategy, 5.0)
                    speed_multiplier, accel_multiplier, variance_min, variance_max, tyre_wear_multiplier, collision_risk, engine_risk, gearbox_risk = apply_track_conditions(lobby, pdata, strategy)
                    base_lap_time *= speed_multiplier
                    fuel_usage = base_fuel_usage * accel_multiplier
                    tyre_type_wear = {
                        "Soft": 1.25,
                        "Medium": 1.0,
                        "Hard": 0.75,
                        "Intermediate": 1.1,
                        "Wet": 0.9
                    }.get(tyre, 1.0)
                    tyre_wear = base_wear * tyre_type_wear * tyre_wear_multiplier
                    if weather == "🌦️ Light Rain":
                        if tyre == "Intermediate":
                            tyre_wear *= 0.85
                        elif tyre == "Wet":
                            tyre_wear *= 1.15
                    elif weather == "🌧️ Heavy Rain":
                        if tyre == "Intermediate":
                            tyre_wear *= 1.10
                        elif tyre == "Wet":
                            tyre_wear *= 0.75
                    else:
                        if tyre == "Wet":
                            tyre_wear *= 1.6
                        elif tyre == "Intermediate":
                            tyre_wear *= 1.3
                    logger.debug(f"🔧 Degradation - Fuel Usage: {fuel_usage}, Tyre Wear: {tyre_wear}, Weather: {weather}, Track Conditions: Speed={speed_multiplier}, Accel={accel_multiplier}, Corners={tyre_wear_multiplier}, Crash Risks: Collision={collision_risk}, Engine={engine_risk}, Gearbox={gearbox_risk}")
                    prev_fuel = pdata.get("fuel", 100.0)
                    prev_tyre = pdata.get("tyre_condition", 100.0)
                    pdata["fuel"] = max(prev_fuel - fuel_usage, 0.0)
                    pdata["tyre_condition"] = max(prev_tyre - tyre_wear, 0.0)
            # Check for crashes
                    crash_types = [
                        ("Collision", collision_risk),
                        ("Engine Failure", engine_risk),
                        ("Gearbox Issue", gearbox_risk)
                    ]
                    for crash_type, risk in crash_types:
                        if risk > 0 and random.random() < risk and not pdata.get("dnf", False):
                            pdata["dnf"] = True
                            pdata["dnf_reason"] = crash_type
                            logger.info(f"💀 DNF: {pid} DNFed on lap {current_lap}: {crash_type}")
                            embed = discord.Embed(
                                title="🏎️ Crash Alert!",
                                description=f"✦ `{lobby['users'][pid].name}` DNFed: {crash_type}! ✦",
                                color=discord.Color.red()
                            )
                            embed.set_footer(text="🏆 Check your DM strategy panel!")
                            await safe_send(ctx, embed=embed)
                            if crash_type == "Collision":
                                collision_occurred = True
                            if pid in lobby["users"]:
                                try:
                                    dm_embed = discord.Embed(
                                        title="🏎️ Your Race Ended!",
                                        description=f"✦ Your car suffered a {crash_type.lower()} on Lap {current_lap}. ✦",
                                        color=discord.Color.red()
                                    )
                                    await lobby["users"][pid].send(embed=dm_embed)
                                except (discord.Forbidden, discord.HTTPException):
                                    logger.warning(f"Failed to send crash DM to {pid}")
                logger.debug(f"Checking safety car: collision_occurred={collision_occurred}, lap={current_lap}")
                await handle_safety_car(ctx, lobby, current_lap, collision_occurred)
                if pdata.get("fuel", 0.0) <= 0 or pdata.get("tyre_condition", 0.0) <= 0:
                    pdata["dnf"] = True
                    pdata["dnf_reason"] = "Out of fuel" if pdata.get("fuel", 0.0) <= 0 else "Tyres worn out"
                    logger.info(f"💀 DNF: {pid} DNFed on lap {current_lap}: {pdata['dnf_reason']}")
                    embed = discord.Embed(
                        title="🏎️ DNF Alert!",
                        description=f"✦ `{lobby['users'][pid].name}` DNFed: {pdata['dnf_reason']} on Lap {current_lap}! ✦",
                        color=discord.Color.red()
                    )
                    await safe_send(ctx, embed=embed)
                strat_factor = {
                    "Push": 0.96,
                    "Balanced": 1.0,
                    "Save": 1.04,
                    "Pit Stop": 1.15
                }.get(strategy, 1.0)
                weather_penalty = {
                    ("☀️ Sunny", "Soft"): 1.0,
                    ("☀️ Sunny", "Medium"): 1.02,
                    ("☀️ Sunny", "Hard"): 1.04,
                    ("☀️ Sunny", "Wet"): 1.4,
                    ("☀️ Sunny", "Intermediate"): 1.3,
                    ("🌦️ Light Rain", "Soft"): 1.35,
                    ("🌦️ Light Rain", "Medium"): 1.25,
                    ("🌦️ Light Rain", "Hard"): 1.3,
                    ("🌦️ Light Rain", "Intermediate"): 1.0,
                    ("🌦️ Light Rain", "Wet"): 1.1,
                    ("🌧️ Heavy Rain", "Soft"): 1.5,
                    ("🌧️ Heavy Rain", "Medium"): 1.4,
                    ("🌧️ Heavy Rain", "Hard"): 1.45,
                    ("🌧️ Heavy Rain", "Intermediate"): 1.15,
                    ("🌧️ Heavy Rain", "Wet"): 1.0,
                    ("☁️ Cloudy", "Soft"): 1.0,
                    ("☁️ Cloudy", "Medium"): 1.0,
                    ("☁️ Cloudy", "Hard"): 1.05,
                    ("☁️ Cloudy", "Wet"): 1.3,
                    ("☁️ Cloudy", "Intermediate"): 1.2,
                    ("🌬️ Windy", "Soft"): 1.1,
                    ("🌬️ Windy", "Medium"): 1.05,
                    ("🌬️ Windy", "Hard"): 1.0,
                    ("🌬️ Windy", "Wet"): 1.35,
                    ("🌬️ Windy", "Intermediate"): 1.2
                }.get((weather, tyre), 1.0)
                tyre_wear_penalty = 1.0 + ((100.0 - pdata["tyre_condition"]) / 100.0) * 0.1
                fuel_penalty = 1.0
                driver_variance = 1.0 if lobby.get("safety_car_active", False) else random.uniform(variance_min, variance_max)
                lap_time = (base_lap_time * strat_factor * weather_penalty * tyre_wear_penalty * fuel_penalty + pit_penalty) * driver_variance
                if just_pitted:
                    pdata["strategy"] = "Balanced"
                if lobby.get("safety_car_active", False):
                    lap_time *= 1.2  # 20% slower under safety car
                pdata["lap_times"].append(lap_time)
                total_time = sum(pdata["lap_times"])
                pdata["total_time"] = total_time
                player_times[pid] = total_time
                # Note: This is a partial snippet for the debug log line (~512) in race_loop.
                # Replace only the debug log line within the `for pid in lobby["players"]:` loop.
                logger.debug(f"🏎 {pid} (User: {lobby['users'].get(pid, {'name': 'Unknown'}).name}) - Pos: {lobby['position_order'].index(pid)+1 if pid in lobby['position_order'] else 'N/A'}, Strat: {strategy}, Lap: {lap_time:.2f}s, Pit penalty: {pit_penalty}s, Total: {total_time:.2f}s, Fuel: {pdata['fuel']:.1f}%, Tyre: {pdata['tyre_condition']:.1f}%")
            valid_players = [pid for pid in lobby["players"] if not lobby["player_data"].get(pid, {}).get("dnf", False)]
            lobby["position_order"] = sorted(valid_players, key=lambda pid: lobby["player_data"].get(pid, {}).get("total_time", float('inf')))
            # Log position order after update
            logger.info(f"Position order after lap {current_lap}: {[lobby['users'].get(pid, {'name': f'Unknown ({pid})'}).name + f' ({lobby['player_data'][pid]['total_time']:.2f}s)' for pid in lobby['position_order']]}")
            embed = generate_race_status_embed(lobby)
            try:
                msg = await ctx.channel.fetch_message(lobby["status_msg_id"])
                await msg.edit(embed=embed)
            except discord.NotFound:
                logger.warning("Race status message not found, recreating...")
                new_msg = await ctx.send(embed=embed)
                lobby["status_msg_id"] = new_msg.id
            except discord.HTTPException as e:
                logger.error(f"HTTP error updating status message: {e}")
                if e.status != 429:
                    raise
            lobby["current_lap"] += 1
            for pid in lobby["players"]:
                user = lobby["users"].get(pid)
                pdata = lobby["player_data"].get(pid)
                if not user or not pdata:
                    logger.warning(f"Skipping DM update for pid {pid}: user or data missing")
                    continue
                if pdata.get("dnf", False):
                    position = "DNF"
                else:
                    try:
                        position = lobby["position_order"].index(pid) + 1
                    except ValueError:
                        position = "?"
                total = len(lobby["players"])
                fuel = round(pdata.get("fuel", 0.0), 1)
                tyre_cond = round(pdata.get("tyre_condition", 0.0), 1)
                weather_emoji = lobby["weather"]
                safety_car_status = "🚨 Active" if lobby.get("safety_car_active", False) else "Inactive"
                last_sent_lap = pdata.get("last_sent_lap", 0)
                if (current_lap != last_sent_lap or
                    abs(pdata["fuel"] - pdata.get("last_sent_fuel", 100.0)) > 5 or
                    abs(pdata["tyre_condition"] - pdata.get("last_sent_tyre", 100.0)) > 5 or
                    position != pdata.get("last_position", "?")):
                    embed = discord.Embed(
                        title="📊 Strategy Panel (Live)",
                        description=(
                            f"📍 You are currently **P{position}** out of **{total}**.\n"
                            f"🏁 Lap **{current_lap}/{total_laps}**\n"
                            f"Weather: **{weather_emoji}**\n"
                            f"🚨 Safety Car: **{safety_car_status}**\n"
                            f"⛽ Fuel: **{fuel}%**\n"
                            f"🛞 Tyre Condition: **{tyre_cond}%**"
                        ),
                        color=discord.Color.orange()
                    )
                    embed.add_field(
                        name="Strategies",
                        value="⚡ Push\n⚖️ Balanced\n🛟 Save\n🛞 Pit Stop",
                        inline=False
                    )
                    embed.set_footer(text="Use this panel during the race to update your strategy.")
                    dm_msg = pdata.get("dm_msg")
                    if dm_msg:
                        try:
                            await dm_msg.edit(embed=embed)
                            pdata["last_sent_fuel"] = pdata["fuel"]
                            pdata["last_sent_tyre"] = pdata["tyre_condition"]
                            pdata["last_position"] = position
                            pdata["last_sent_lap"] = current_lap
                            logger.debug(f"📨 Updated DM for {user.name} on lap {current_lap}")
                        except (discord.HTTPException, discord.Forbidden, discord.NotFound) as e:
                            logger.warning(f"Failed to update DM for pid {pid}: {e}, recreating DM")
                            try:
                                new_dm = await user.send(embed=embed)
                                pdata["dm_msg"] = new_dm
                                pdata["last_sent_fuel"] = pdata["fuel"]
                                pdata["last_sent_tyre"] = pdata["tyre_condition"]
                                pdata["last_position"] = position
                                pdata["last_sent_lap"] = current_lap
                            except (discord.Forbidden, discord.HTTPException) as e:
                                logger.error(f"Failed to recreate DM for pid {pid}: {e}")
                                pdata["dm_msg"] = None
                    else:
                        try:
                            new_dm = await user.send(embed=embed)
                            pdata["dm_msg"] = new_dm
                            pdata["last_sent_fuel"] = pdata["fuel"]
                            pdata["last_sent_tyre"] = pdata["tyre_condition"]
                            pdata["last_position"] = position
                            pdata["last_sent_lap"] = current_lap
                        except (discord.Forbidden, discord.HTTPException) as e:
                            logger.error(f"Failed to send initial DM for pid {pid}: {e}")
                            pdata["dm_msg"] = None
            elapsed = time.time() - lap_start_time
            await asyncio.sleep(max(0, lap_delay - elapsed))
            logger.debug(f"🏁 Finished lap {lobby['current_lap'] - 1}: Actual time = {elapsed:.2f}s")
        if channel_id not in lobbies:
            return
                # Final results
        final_order = lobby["position_order"]
        embed = discord.Embed(
            title=f"🏆 {lobby['track']} Grand Prix — Results",
            description=f"Weather: {lobby['weather']}",
            color=discord.Color.green()
        )
        podium_emojis = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"}
        leader_time = lobby["player_data"][final_order[0]]["total_time"] if final_order else None
        update_leaderboard = lobby["race_mode"] == "championship"
        for pos, pid in enumerate(final_order, 1):
            user = lobby["users"].get(pid)
            if not user:
                continue
            total_time = lobby["player_data"][pid]["total_time"]
            if pos == 1 or leader_time is None:
                time_display = format_race_time(total_time)
            else:
                gap = total_time - leader_time
                time_display = f"+{gap:.3f}s"
            points = F1_POINTS.get(pos, 0)
            pos_display = podium_emojis.get(pos, f"{pos}.")
            embed.add_field(
                name=f"P{pos} {pos_display}",
                value=f"{user.name} — `{time_display}` — {points} pts",
                inline=True
            )
            profile = get_player_profile(pid)
            profile["points"] += points
            if update_leaderboard:
                profile["tournament_stats"]["points"] += points
                if pos == 1:
                    profile["tournament_stats"]["wins"] += 1
                if pos <= 3:
                    profile["tournament_stats"]["podiums"] += 1
        dnf_players = [pid for pid, pdata in lobby["player_data"].items() if pdata.get("dnf", False)]
        if dnf_players:
            dnf_names = [f"{lobby['users'].get(pid, {'name': f'Unknown ({pid})'}).name} — {lobby['player_data'][pid]['dnf_reason']}" for pid in dnf_players if pid in lobby["users"]]
            embed.add_field(
                name="❌ DNFs",
                value="\n".join(dnf_names) if dnf_names else "No DNFs recorded.",
                inline=False
            )
        if lobby["mode"] == "duo":
            team_points = {}
            for team_idx, team in enumerate(lobby["teams"]):
                team_name = lobby["team_names"].get(team_idx, f"Team {team_idx + 1}")
                team_points[team_name] = sum(F1_POINTS.get(final_order.index(pid) + 1, 0) for pid in team if pid in final_order)
            team_scores = [f"{name} — {points} pts" for name, points in sorted(team_points.items(), key=lambda x: x[1], reverse=True)]
            embed.add_field(
                name="🤝 Team Scores",
                value="\n".join(team_scores) if team_scores else "No team scores.",
                inline=False
            )
        for pid in lobby["players"]:
            pdata = lobby["player_data"].get(pid, {})
            profile = get_player_profile(pid)
            profile["races"] += 1
            if not pdata.get("dnf", False):
                profile["total_time"] += pdata.get("total_time", 0.0)
                pos = final_order.index(pid) + 1 if pid in final_order else None
                if pos == 1:
                    profile["wins"] += 1
                if pos and pos <= 3:
                    profile["podiums"] += 1
            if pdata.get("lap_times", []):
                fastest_lap_in_race = min(pdata["lap_times"])
                if not profile["fastest_lap"] or fastest_lap_in_race < profile["fastest_lap"]:
                    profile["fastest_lap"] = fastest_lap_in_race
                    logger.info(f"🏅 New fastest lap for {pid}: {fastest_lap_in_race:.2f}s")
            if pdata.get("dnf", False):
                profile["dnfs"] += 1
        save_career_stats()
        await safe_send(ctx, embed=embed)
        del lobbies[channel_id]
    except Exception as e:
        logger.error(f"🏃‍♂️ Race loop failed: {e}")
        await safe_send(ctx, "❌ The race crashed! Please try creating a new lobby with `!create`.")
        if channel_id in lobbies:
            del lobbies[channel_id]

def generate_race_status_embed(lobby):
    track = lobby.get("track", "Unknown Track")
    weather = lobby.get("weather", "☀️ Sunny")
    current_lap = lobby.get("current_lap", 1)
    total_laps = TRACKS_INFO.get(track, {"laps": 1})["laps"]
    position_order = lobby.get("position_order", [])
    player_data = lobby.get("player_data", {})
    users = lobby.get("users", {})
    embed = discord.Embed(
        title=f"🏎️ {track} Grand Prix",
        description=(
            f"**Weather:** {weather} • **Lap:** {current_lap}/{total_laps}\n"
            f"**Safety Car:** {'🚨 Active' if lobby.get('safety_car_active', False) else 'Inactive'}"
        ),
        color=discord.Color.red() if "Sunny" in weather else (
            discord.Color.blue() if "Rain" in weather else discord.Color.blurple()
        )
    )
    tyre_emoji = {
        "Soft": "🔴 Soft",
        "Medium": "🟠 Medium",
        "Hard": "⚪ Hard",
        "Intermediate": "🟢 Inter",
        "Wet": "🔵 Wet"
    }
    strat_emoji = {
        "Push": "⚡",
        "Balanced": "⚖️",
        "Save": "🛟",
        "Pit Stop": "🛞"
    }
    if not position_order:
        embed.add_field(name="🏁 Status", value="No active drivers.", inline=False)
        return embed
    leader_time = player_data.get(position_order[0], {}).get("total_time", 0.0) if position_order else 0.0
    for pos, pid in enumerate(position_order, 1):
        if pid not in users or pid not in player_data:
            continue
        user = users[pid]
        pdata = player_data[pid]
        strategy = pdata.get("strategy", "Balanced")
        tyre = pdata.get("tyre", "Medium")
        tyre_display = tyre_emoji.get(tyre, tyre)
        strat_display = strat_emoji.get(strategy, "")
        total_time = pdata.get("total_time", 0.0)
        if pos == 1:
            gap = "—"
        else:
            prev_pid = position_order[pos-2]
            prev_time = player_data.get(prev_pid, {}).get("total_time", 0.0)
            time_gap = total_time - prev_time
            gap = f"+{time_gap:.3f}s"
            logger.debug(f"Gap for {user.name} (P{pos}): {gap}, Total Time: {total_time:.2f}s, Prev Time: {prev_time:.2f}s")
        if strategy == "Pit Stop" and pdata.get("last_pit_lap", 0) != current_lap:
            driver_line = f"**P{pos}** `{user.name}` • 🛞 Pitting..."
        else:
            driver_line = f"**P{pos}** `{user.name}` • {tyre_display} • {strat_display} {strategy} • `{gap}`"
        embed.add_field(name="\u200b", value=driver_line, inline=False)
    dnf_players = [pid for pid, pdata in player_data.items() if pdata.get("dnf", False)]
    if dnf_players:
        dnf_names = [f"{users.get(pid, {'name': f'Unknown ({pid})'}).name} — {player_data[pid]['dnf_reason']}" for pid in dnf_players]
        embed.add_field(name="❌ DNFs", value="\n".join(dnf_names), inline=False)
    embed.set_footer(text="Use your DM strategy panel to make changes during the race.")
    return embed

class StrategyPanelView(View):
    def __init__(self, user_id, channel_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.channel_id = channel_id
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your car, buddy.", ephemeral=True)
            return False
        return True
    @discord.ui.button(label="Push", style=discord.ButtonStyle.danger, emoji="⚡")
    async def push(self, interaction: discord.Interaction, button: Button):
        if self.channel_id in lobbies and self.user_id in lobbies[self.channel_id]["player_data"]:
            lobbies[self.channel_id]["player_data"][self.user_id]["strategy"] = "Push"
            await interaction.response.send_message("⚡ Strategy set to **Push**.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Race or player data not found.", ephemeral=True)
    @discord.ui.button(label="Balanced", style=discord.ButtonStyle.primary, emoji="⚖️")
    async def balanced(self, interaction: discord.Interaction, button: Button):
        if self.channel_id in lobbies and self.user_id in lobbies[self.channel_id]["player_data"]:
            lobbies[self.channel_id]["player_data"][self.user_id]["strategy"] = "Balanced"
            await interaction.response.send_message("⚖️ Strategy set to **Balanced**.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Race or player data not found.", ephemeral=True)
    @discord.ui.button(label="Save", style=discord.ButtonStyle.success, emoji="🛟")
    async def save(self, interaction: discord.Interaction, button: Button):
        if self.channel_id in lobbies and self.user_id in lobbies[self.channel_id]["player_data"]:
            lobbies[self.channel_id]["player_data"][self.user_id]["strategy"] = "Save"
            await interaction.response.send_message("🛟 Strategy set to **Save**.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Race or player data not found.", ephemeral=True)
    @discord.ui.button(label="Pit Stop", style=discord.ButtonStyle.secondary, emoji="🛞")
    async def pit(self, interaction: discord.Interaction, button: Button):
        logger.info(f"Pit button clicked by {self.user_id} in channel {self.channel_id}")
        if self.channel_id not in lobbies or self.user_id not in lobbies[self.channel_id]["player_data"]:
            await interaction.response.send_message("❌ Race or player data not found.", ephemeral=True)
            return
        view = TyreView(self.user_id)
        await interaction.response.send_message("🛠 Choose your tyre set:", view=view, ephemeral=True)
        await view.wait()
        if view.choice:
            pdata = lobbies[self.channel_id]["player_data"][self.user_id]
            current_lap = lobbies[self.channel_id]["current_lap"]
            if pdata["last_pit_lap"] == current_lap:
                logger.warning(f"Pit stop skipped for {self.user_id}: Already pitted on lap {current_lap}")
                await interaction.followup.send("🛞 You already pitted this lap!", ephemeral=True)
                return
            pdata["tyre"] = view.choice
            pdata["strategy"] = "Pit Stop"  # Set strategy to trigger penalty
            logger.info(f"🛞 Pit stop confirmed for {self.user_id}: Tyre={view.choice}, Lap={current_lap}")
            await interaction.followup.send(
                f"✅ Pit stop complete! You chose **{view.choice}** tyres.\n"
                f"⛽ Fuel and 🛞 tyres fully refilled.",
                ephemeral=True
            )

# Replace the `TyreView` class with the following
class TyreView(View):
    def __init__(self, user_id):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.choice = None
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your pit crew, mate.", ephemeral=True)
            return False
        return True
    async def on_timeout(self):
        await self.message.edit(content="🛞 Pit stop cancelled: No tyre selected in time.", view=None)
    async def _select_tyre(self, interaction, tyre):
        self.choice = tyre
        logger.info(f"Tyre selected: {tyre} by {self.user_id}")
        await interaction.response.send_message(f"✅ You chose **{tyre}** tyres!", ephemeral=True)
        self.stop()
    @discord.ui.button(label="Soft", style=discord.ButtonStyle.danger, emoji="🔥")
    async def soft(self, interaction: discord.Interaction, button: Button):
        await self._select_tyre(interaction, "Soft")
    @discord.ui.button(label="Medium", style=discord.ButtonStyle.primary, emoji="⚖️")
    async def medium(self, interaction: discord.Interaction, button: Button):
        await self._select_tyre(interaction, "Medium")
    @discord.ui.button(label="Hard", style=discord.ButtonStyle.secondary, emoji="🧱")
    async def hard(self, interaction: discord.Interaction, button: Button):
        await self._select_tyre(interaction, "Hard")
    @discord.ui.button(label="Intermediate", style=discord.ButtonStyle.success, emoji="🌦️")
    async def intermediate(self, interaction: discord.Interaction, button: Button):
        await self._select_tyre(interaction, "Intermediate")
    @discord.ui.button(label="Wet", style=discord.ButtonStyle.success, emoji="🌧️")
    async def wet(self, interaction: discord.Interaction, button: Button):
        await self._select_tyre(interaction, "Wet")

async def handle_safety_car(ctx, lobby, current_lap, collision_occurred):
    logger.debug(f"handle_safety_car called: active={lobby.get('safety_car_active', False)}, laps={lobby.get('safety_car_laps', 0)}, collision={collision_occurred}")
    if lobby.get("safety_car_active", False):
        if "safety_car_laps" in lobby:
            lobby["safety_car_laps"] = max(0, lobby["safety_car_laps"] - 1)
            logger.debug(f"Safety car active, laps remaining: {lobby['safety_car_laps']}")
            if lobby["safety_car_laps"] == 0:
                lobby["safety_car_active"] = False
                embed = discord.Embed(
                    title="🏎️🏁 Safety Car In!",
                    description=f"✦ The safety car has returned to the pits on Lap {current_lap}! Racing resumes. ✦",
                    color=discord.Color.green()
                )
                embed.set_footer(text="🏆 Adjust your strategy!")
                await safe_send(ctx, embed=embed)
                logger.info(f"Safety car ended on lap {current_lap} in channel {ctx.channel.id}")
        return
    if collision_occurred and current_lap < lobby["laps"] - 5:
        logger.debug(f"Deploying safety car due to collision on lap {current_lap}")
        lobby["safety_car_active"] = True
        lobby["safety_car_laps"] = random.randint(2, 4)
        embed = discord.Embed(
            title="🏎️🏁 Safety Car Deployed!",
            description=f"✦ Collision on Lap {current_lap}! Safety car out for {lobby['safety_car_laps']} laps. ✦",
            color=discord.Color.yellow()
        )
        embed.add_field(
            name="Impact",
            value="⚡ Slower laps\n🛞 No fuel/tyre wear\n🏎️ No overtaking",
            inline=False
        )
        embed.set_footer(text="🏆 Use your DM panel to plan your strategy!")
        await safe_send(ctx, embed=embed)
        logger.info(f"Safety car deployed on lap {current_lap} for {lobby['safety_car_laps']} laps due to collision in channel {ctx.channel.id}")

@bot.command(name="help")
async def help(ctx):
    zcoin_emoji = get_zcoin_emoji(ctx)
    embed = discord.Embed(
        title="🏎️ Formula Z — Help & Guide",
        description="Welcome to Formula Z! Race, strategize, and upgrade your car to dominate the tracks!",
        color=discord.Color.teal()
    )
    embed.add_field(
        name="🏁 Race Commands",
        value=(
            "`!create` – Start a new race lobby\n"
            "`!join` – Join a race lobby\n"
            "`!start` – Start the race (host, 2+ players)\n"
            "`!leave` – Leave the lobby\n"
            "`!tracks` – View all tracks\n"
            "`!set <track>` – Set track (host)\n"
            "`!lobby` – Show lobby details\n"
            "`!setstrat <tyre> <strat>` – Set initial tyre/strategy (e.g., !setstrat Soft Push)"
        ),
        inline=True
    )
    embed.add_field(
        name="👥 Team & Lobby",
        value=(
            "`!cm <solo|duo>` – Set mode (host)\n"
            "`!kick @user` – Kick player (host)\n"
            "`!yeet` – Delete lobby (host)\n"
            "`!swap @user1 @user2` – Swap duo teams (host)\n"
            "`!ctn <number> <name>` – Rename duo team (host)"
        ),
        inline=True
    )
    embed.add_field(
        name="📊 Stats & Economy",
        value=(
            "`!lb` – View leaderboard\n"
            "`!profile` – See career stats\n"
            "`!stats` – Check car stats\n"
            "`!garage` – View and manage car parts\n"
            "`!upgrade <part>` – Upgrade car part (e.g., engine, tyres) for {zcoin_emoji}\n"
            "`!coins` – Check {zcoin_emoji} balance\n"
            "`!daily` – Claim 100 {zcoin_emoji} (24h)\n"
            "`!weekly` – Claim 500 {zcoin_emoji} (7d)\n"
            "`!monthly` – Claim 2000 {zcoin_emoji} (30d)"
        ).format(zcoin_emoji=zcoin_emoji),
        inline=True
    )
    embed.add_field(
        name="🌦️ Weather Tips",
        value=(
            "**☀️ Sunny** – All tyres viable\n"
            "**🌦️ Light Rain** – Intermediate/Wet\n"
            "**🌧️ Heavy Rain** – Wet preferred\n"
            "**☁️ Cloudy** – Mediums stable\n"
            "**🌬️ Windy** – Avoid Soft"
        ),
        inline=True
    )
    embed.add_field(
        name="🛞 Tyres & Strategies",
        value=(
            "**Tyres**:\n"
            "🔴 Soft – Fast, high wear\n"
            "🟠 Medium – Balanced\n"
            "⚪ Hard – Slow, durable\n"
            "🟢 Intermediate – Light rain\n"
            "🔵 Wet – Heavy rain\n\n"
            "**Strategies**:\n"
            "⚡ Push – Fast, high wear\n"
            "⚖️ Balanced – Default\n"
            "🛟 Save – Conserves resources\n"
            "🛞 Pit Stop – Refuel, retyre"
        ),
        inline=True
    )
    embed.add_field(
        name="🎮 Features",
        value=(
            "📊 **Live Panel**: DM updates with position, lap, fuel, tyres, weather.\n"
            "🌦️ **Weather**: Impacts tyre wear and pace.\n"
            "🏎️ **Parts**: Upgrade with {zcoin_emoji} to boost stats.\n"
            "❌ **DNFs**: Fuel/tyre depletion or crashes.\n"
            "🏆 **Results**: 🥇🥈🥉 for top 3, points for top 10."
        ).format(zcoin_emoji=zcoin_emoji),
        inline=True
    )
    embed.set_footer(text="🏁 Use DM panel to adjust strategy during races!")
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    logger.info("Starting bot initialization...")
    load_career_stats()
    migrate_to_car_parts()
    logger.info(f'🚀 {bot.user} has connected to Discord!')
    logger.info(f"Career stats after load: {career_stats}")
    # Start autosave task
    bot.loop.create_task(autosave_career_stats())

async def autosave_career_stats():
    while True:
        await asyncio.sleep(300)  # Autosave every 5 minutes (300 seconds)
        if not career_stats:
            logger.warning("Skipping autosave: career_stats is empty")
            continue
        save_career_stats()
        logger.info("Autosaved career_stats.json (periodic)")

@bot.command()
async def profile(ctx):
    user_id = ctx.author.id
    profile = get_player_profile(user_id)
    embed = discord.Embed(
        title=f"🏎️ {ctx.author.name}'s Career Profile",
        color=discord.Color.blue()
    )
    embed.add_field(name="Races", value=str(profile["races"]), inline=True)
    embed.add_field(name="Wins", value=str(profile["wins"]), inline=True)
    embed.add_field(name="Podiums", value=str(profile["podiums"]), inline=True)
    embed.add_field(name="DNFs", value=str(profile["dnfs"]), inline=True)
    embed.add_field(
        name="Fastest Lap",
        value=format_race_time(profile["fastest_lap"]) if profile["fastest_lap"] else "N/A",
        inline=True
    )
    embed.add_field(name="Points", value=str(profile["points"]), inline=True)
    embed.set_footer(text="Keep racing to climb the leaderboard!")
    await ctx.send(embed=embed)

def save_on_exit():
    save_career_stats()

atexit.register(save_on_exit)

@bot.command(name="lobby")
async def lobby_status(ctx):
    channel_id = ctx.channel.id
    if channel_id not in lobbies:
        embed = discord.Embed(
            title="🏎️ No Active Lobby",
            description="No race lobby in this channel. Create one with `!create [track]`.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    lobby = lobbies[channel_id]
    player_names = [lobby["users"][pid].name for pid in lobby["players"] if pid in lobby["users"]]
    players_text = "\n".join([f"🏎️ {name}" for name in player_names]) if player_names else "No players yet."
    if lobby["mode"] == "duo" and lobby["teams"]:
        team_texts = []
        for idx, team in enumerate(lobby["teams"]):
            team_name = lobby["team_names"].get(idx, f"Team {idx + 1}")
            team_players = [lobby["users"][pid].name for pid in team if pid in lobby["users"]]
            team_texts.append(f"**{team_name}**: {', '.join(team_players)}")
        teams_text = "\n".join(team_texts)
    else:
        teams_text = "Solo mode — no teams."
    embed = discord.Embed(
        title=f"🏎️ {lobby['track']} Lobby",
        description=f"**Host**: {lobby['users'][lobby['host']].name}\n**Status**: {lobby['status'].capitalize()}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Players", value=players_text, inline=True)
    embed.add_field(name="Teams", value=teams_text, inline=True)
    embed.add_field(
        name="Track Info",
        value=(
            f"**Track**: {lobby['track']}\n"
            f"**Weather**: {lobby['weather']}\n"
            f"**Conditions**:\n"
            f"  ⚡ Speed: {lobby['conditions']['speed']}\n"
            f"  🛞 Accel: {lobby['conditions']['acceleration']}\n"
            f"  🏎️ Overtake: {lobby['conditions']['overtaking']}\n"
            f"  🔄 Corners: {lobby['conditions']['corners']}\n"
            f"**Mode**: {lobby['race_mode'].capitalize()}"
        ),
        inline=False
    )
    embed.set_footer(text="Join with `!join` or start with `!start` (host only).")
    await ctx.send(embed=embed)

@bot.command()
async def cm(ctx, mode: str = None):
    channel_id = ctx.channel.id
    user_id = ctx.author.id
    if channel_id not in lobbies:
        await ctx.send("❌ No active race lobby in this channel. Create one with `!create`.")
        return
    lobby = lobbies[channel_id]
    if user_id != lobby["host"]:
        await ctx.send("🚫 Only the game host can change the race mode.")
        return
    if lobby["status"] != "waiting":
        await ctx.send("🚫 You can't change the mode after the race has started.")
        return
    if not mode or mode.lower() not in ["solo", "duo"]:
        await ctx.send("❌ Specify a valid mode: `!cm solo` or `!cm duo`.")
        return
    mode = mode.lower()
    if mode == lobby["mode"]:
        await ctx.send(f"🏁 The lobby is already in **{mode}** mode.")
        return
    if mode == "duo":
        if len(lobby["players"]) < 2:
            await ctx.send("❌ Need at least 2 players to form teams in duo mode.")
            return
        if len(lobby["players"]) % 2 != 0:
            await ctx.send("❌ Duo mode requires an even number of players.")
            return
        shuffled_players = random.sample(lobby["players"], len(lobby["players"]))
        lobby["teams"] = [shuffled_players[i:i+2] for i in range(0, len(shuffled_players), 2)]
        lobby["team_names"] = {i: f"Team {i+1}" for i in range(len(lobby["teams"]))}  # Initialize team names
        lobby["mode"] = "duo"
        team_display = []
        for i, team in enumerate(lobby["teams"], 1):
            team_names = []
            for pid in team:
                user = lobby["users"].get(pid)
                if not user:
                    try:
                        user = await bot.fetch_user(pid)
                        lobby["users"][pid] = user
                    except (discord.NotFound, discord.HTTPException):
                        logger.warning(f"Failed to fetch user {pid} for team display")
                        team_names.append(f"Unknown ({pid})")
                        continue
                team_names.append(user.name)
            team_display.append(f"**Team {i}**: {team_names[0]} & {team_names[1]}")
        embed = discord.Embed(
            title="🤝 Duo Mode Activated",
            description="Players have been randomly paired into teams!",
            color=discord.Color.blue()
        )
        embed.add_field(name="Teams", value="\n".join(team_display), inline=False)
        embed.set_footer(text="Use !start to begin the race!")
        await ctx.send(embed=embed)
    else:
        lobby["mode"] = "solo"
        lobby["teams"] = []
        embed = discord.Embed(
            title="🏎️ Solo Mode Activated",
            description="The lobby is now set to individual racing.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Use !start to begin the race!")
        await ctx.send(embed=embed)

@bot.command()
async def kick(ctx, member: discord.Member):
    channel_id = ctx.channel.id
    user_id = ctx.author.id
    if channel_id not in lobbies:
        embed = discord.Embed(
            title="❌ No Lobby Found",
            description="There’s no active race lobby in this channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    lobby = lobbies[channel_id]
    if user_id != lobby["host"]:
        embed = discord.Embed(
            title="🚫 Permission Denied",
            description="Only the host can kick players from the lobby.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    if lobby["status"] != "waiting":
        embed = discord.Embed(
            title="🚫 Race In Progress",
            description="You can’t kick players after the race has started.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    target_id = member.id
    if target_id == user_id:
        embed = discord.Embed(
            title="🙃 Invalid Action",
            description="You can’t kick yourself from the lobby!",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return
    if target_id not in lobby["players"]:
        embed = discord.Embed(
            title="❌ Player Not Found",
            description=f"{member.name} is not in this race lobby.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    lobby["players"].remove(target_id)
    lobby["users"].pop(target_id, None)
    if lobby["mode"] == "duo":
        if len(lobby["players"]) % 2 != 0:
            lobby["mode"] = "solo"
            lobby["teams"] = []
            embed = discord.Embed(
                title="✅ Player Kicked",
                description=f"{member.name} was kicked from the lobby.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Mode Update",
                value="Odd number of players after kick. Switched to **solo** mode.",
                inline=False
            )
            await ctx.send(embed=embed)
        else:
            shuffled_players = random.sample(lobby["players"], len(lobby["players"]))
            lobby["teams"] = [shuffled_players[i:i+2] for i in range(0, len(shuffled_players), 2)]
            lobby["team_names"] = {i: f"Team {i+1}" for i in range(len(lobby["teams"]))}  # Reinitialize team names
            team_display = []
            for i, team in enumerate(lobby["teams"], 1):
                team_names = [lobby["users"].get(pid, {"name": f"Unknown ({pid})"}).name for pid in team]
                team_display.append(f"**Team {i}**: {team_names[0]} & {team_names[1]}")
            embed = discord.Embed(
                title="✅ Player Kicked",
                description=f"{member.name} was kicked from the lobby.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="🤝 Teams Reorganized",
                value="\n".join(team_display),
                inline=False
            )
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="✅ Player Kicked",
            description=f"{member.name} was kicked from the lobby.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    if not lobby["players"]:
        embed = discord.Embed(
            title="🏁 Lobby Closed",
            description="No players left after the kick. The lobby has been closed.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        del lobbies[channel_id]
        return

@bot.command()
async def yeet(ctx):
    channel_id = ctx.channel.id
    user_id = ctx.author.id
    if channel_id not in lobbies:
        embed = discord.Embed(
            title="❌ No Lobby Found",
            description="There’s no active race lobby in this channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    lobby = lobbies[channel_id]
    if user_id != lobby["host"]:
        embed = discord.Embed(
            title="🚫 Permission Denied",
            description="Only the host can yeet the lobby.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    if lobby["status"] != "waiting":
        embed = discord.Embed(
            title="🚫 Race In Progress",
            description="You can’t yeet the lobby after the race has started.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    del lobbies[channel_id]
    embed = discord.Embed(
        title="💥 Lobby Yeeted",
        description="The race lobby has been canceled!",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Use !create to start a new lobby.")
    await ctx.send(embed=embed)

@bot.command()
async def swap(ctx, member1: discord.Member, member2: discord.Member):
    channel_id = ctx.channel.id
    user_id = ctx.author.id
    if channel_id not in lobbies:
        embed = discord.Embed(
            title="❌ No Lobby Found",
            description="There’s no active race in this channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    lobby = lobbies[channel_id]
    if user_id != lobby["host"]:
        embed = discord.Embed(
            title="🚫 Permission Denied",
            description="Only the host can swap players between teams.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    if lobby["status"] != "waiting":
        embed = discord.Embed(
            title="🚫 Race In Progress",
            description="You can’t swap players after the race has started.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    if lobby["mode"] != "duo":
        embed = discord.Embed(
            title="🚫 Invalid Mode",
            description="Swap is only available in Duo mode. Use `!cm duo` to switch modes.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    pid1 = member1.id
    pid2 = member2.id
    if pid1 not in lobby["players"] or pid2 not in lobby["players"]:
        embed = discord.Embed(
            title="❌ Player Not Found",
            description="One or both players are not in the lobby.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    if pid1 == pid2:
        embed = discord.Embed(
            title="🙃 Invalid Action",
            description="You can’t swap the same player with themselves!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    team1_idx = None
    team2_idx = None
    pid1_pos = None
    pid2_pos = None
    for i, team in enumerate(lobby["teams"]):
        for j, pid in enumerate(team):
            if pid == pid1:
                team1_idx = i
                pid1_pos = j
            if pid == pid2:
                team2_idx = i
                pid2_pos = j
    if team1_idx is None or team2_idx is None:
        embed = discord.Embed(
            title="❌ Swap Failed",
            description="Could not find both players in teams.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    if team1_idx == team2_idx:
        embed = discord.Embed(
            title="🚫 Same Team",
            description="Players are on the same team. No swap needed.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    lobby["teams"][team1_idx][pid1_pos], lobby["teams"][team2_idx][pid2_pos] = (
        lobby["teams"][team2_idx][pid2_pos], lobby["teams"][team1_idx][pid1_pos]
    )
    team_display = []
    for i, team in enumerate(lobby["teams"], 1):
        team_names = [lobby["users"].get(pid, {"name": f"Unknown ({pid})"}).name for pid in team]
        team_display.append(f"Team {i}: {team_names[0]} & {team_names[1]}")
    embed = discord.Embed(
        title="🤝 Players Swapped",
        description=f"{member1.name} and {member2.name} have been swapped between teams!",
        color=discord.Color.blue()
    )
    embed.add_field(name="Teams", value="\n".join(team_display), inline=False)
    embed.set_footer(text="Use !lobby to view the updated lobby.")
    await ctx.send(embed=embed)

@bot.command(name="lb")
async def leaderboard(ctx):
    if not career_stats:
        embed = discord.Embed(
            title="🏆 Formula Z Leaderboard",
            description="🚩 No championship races recorded yet! Start a race with `!create` and use `!tm` for championship mode.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url="https://i.imgur.com/8zX0J5g.png")
        embed.set_footer(text="🏎️ Race to dominate the championship!")
        await ctx.send(embed=embed)
        return
    sorted_players = sorted(
        career_stats.items(),
        key=lambda x: (-x[1]["tournament_stats"]["points"], x[1]["races"])
    )
    zcoin_emoji = get_zcoin_emoji(ctx)
    leaderboard_lines = []
    number_emojis = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"}
    for rank, (user_id, stats) in enumerate(sorted_players, 1):
        if rank > 10:
            break
        try:
            user = await bot.fetch_user(user_id)
            name = user.name
        except (discord.NotFound, discord.HTTPException):
            logger.warning(f"Failed to fetch user {user_id}")
            name = f"Unknown ({user_id})"
        points = stats["tournament_stats"]["points"]
        if points == 0:
            continue
        emoji = number_emojis.get(rank, f"{rank}.")
        leaderboard_lines.append(f"{emoji} **{name}** — {points} pts")
    zcoin_emoji = get_zcoin_emoji(ctx)
    embed = discord.Embed(
        title="🏆 Formula Z Leaderboard",
        description="\n".join(leaderboard_lines) if leaderboard_lines else "No championship points recorded yet!",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url="https://i.imgur.com/8zX0J5g.png")
    embed.set_footer(text=f"ZCoin: {zcoin_emoji} | Compete in championship races to climb the ranks!")
    await ctx.send(embed=embed)

@bot.command()
async def setstrat(ctx, tyre: str = None, strat: str = None):
    channel_id = ctx.channel.id
    user_id = ctx.author.id
    if channel_id not in lobbies:
        await ctx.send("❌ No active race lobby in this channel.")
        return
    lobby = lobbies[channel_id]
    if lobby["status"] != "waiting":
        await ctx.send("🚫 You can only set your strategy before the race starts.")
        return
    if user_id not in lobby["players"]:
        await ctx.send("🙃 You're not in this race lobby. Use `!join` first.")
        return
    valid_tyres = ["Soft", "Medium", "Hard", "Intermediate", "Wet"]
    valid_strats = ["Push", "Balanced", "Save"]
    if not tyre or tyre not in valid_tyres:
        await ctx.send(f"⚠️ Invalid tyre. Choose from: {', '.join(valid_tyres)}")
        return
    if not strat or strat not in valid_strats:
        await ctx.send(f"⚠️ Invalid strategy. Choose from: {', '.join(valid_strats)}")
        return
    if "initial_settings" not in lobby:
        lobby["initial_settings"] = {}
    lobby["initial_settings"][user_id] = {"tyre": tyre, "strategy": strat}
    await ctx.send(f"✅ {ctx.author.mention} set initial strategy: **{tyre}** tyres, **{strat}** strategy.")

@bot.command(name="ctn")
async def change_team_name(ctx, team_number: int, *, custom_name: str):
    channel_id = ctx.channel.id
    if channel_id not in lobbies:
        await safe_send(ctx, "❌ No lobby exists in this channel. Use `!create` to start one.")
        return
    lobby = lobbies[channel_id]
    if ctx.author.id != lobby["host"]:
        await safe_send(ctx, "❌ Only the lobby host can change team names.")
        return
    if lobby["mode"] != "duo":
        await safe_send(ctx, "❌ Team names can only be changed in duo mode.")
        return
    if team_number < 1 or team_number > len(lobby["teams"]):
        await safe_send(ctx, f"❌ Invalid team number. Choose a number between 1 and {len(lobby['teams'])}.")
        return
    if len(custom_name) > 30:
        await safe_send(ctx, "❌ Team name must be 30 characters or less.")
        return
    lobby["team_names"][team_number - 1] = custom_name
    logger.info(f"Team {team_number} renamed to '{custom_name}' by host {ctx.author.id} in channel {channel_id}")
    await safe_send(ctx, f"✅ Team {team_number} renamed to **{custom_name}**!")

@bot.command()
async def coins(ctx):
    user_id = ctx.author.id
    profile = get_player_profile(user_id)
    zcoin_emoji = get_zcoin_emoji(ctx)
    embed = discord.Embed(
        title=f"💰 {ctx.author.name}'s Zcoin Balance",
        description=f"You have **{profile['zcoins']}** {zcoin_emoji}.",
        color=discord.Color.gold()
    )
    embed.set_footer(text="Claim more with !daily, !weekly, or !monthly")
    await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    user_id = ctx.author.id
    profile = get_player_profile(user_id)
    zcoin_emoji = get_zcoin_emoji(ctx)
    current_time = time.time()
    cooldown = 24 * 3600  # 24 hours
    if current_time - profile["last_daily"] < cooldown:
        remaining = cooldown - (current_time - profile["last_daily"])
        await ctx.send(f"⏳ Wait **{format_cooldown(remaining)}** to claim your next daily reward!")
        return
    profile["zcoins"] += 100
    profile["last_daily"] = current_time
    save_career_stats()
    logger.info(f"User {user_id} claimed 100 Zcoins (daily)")
    embed = discord.Embed(
        title="🎉 Daily Reward Claimed!",
        description=f"You received **100** {zcoin_emoji}!",
        color=discord.Color.green()
    )
    embed.set_footer(text="Come back tomorrow for more!")
    await ctx.send(embed=embed)

@bot.command()
async def weekly(ctx):
    user_id = ctx.author.id
    profile = get_player_profile(user_id)
    zcoin_emoji = get_zcoin_emoji(ctx)
    current_time = time.time()
    cooldown = 7 * 24 * 3600  # 7 days
    if current_time - profile["last_weekly"] < cooldown:
        remaining = cooldown - (current_time - profile["last_weekly"])
        await ctx.send(f"⏳ Wait **{format_cooldown(remaining)}** to claim your next weekly reward!")
        return
    profile["zcoins"] += 500
    profile["last_weekly"] = current_time
    save_career_stats()
    logger.info(f"User {user_id} claimed 500 Zcoins (weekly)")
    embed = discord.Embed(
        title="🎉 Weekly Reward Claimed!",
        description=f"You received **500** {zcoin_emoji}!",
        color=discord.Color.green()
    )
    embed.set_footer(text="Come back next week for more!")
    await ctx.send(embed=embed)

@bot.command()
async def monthly(ctx):
    user_id = ctx.author.id
    profile = get_player_profile(user_id)
    zcoin_emoji = get_zcoin_emoji(ctx)
    current_time = time.time()
    cooldown = 30 * 24 * 3600  # 30 days
    if current_time - profile["last_monthly"] < cooldown:
        remaining = cooldown - (current_time - profile["last_monthly"])
        await ctx.send(f"⏳ Wait **{format_cooldown(remaining)}** to claim your next monthly reward!")
        return
    profile["zcoins"] += 2000
    profile["last_monthly"] = current_time
    save_career_stats()
    logger.info(f"User {user_id} claimed 2000 Zcoins (monthly)")
    embed = discord.Embed(
        title="🎉 Monthly Reward Claimed!",
        description=f"You received **2000** {zcoin_emoji}!",
        color=discord.Color.green()
    )
    embed.set_footer(text="Come back next month for more!")
    await ctx.send(embed=embed)

from discord.ui import View, Button

class StatsView(View):
    def __init__(self, user_id: int, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.user_id = user_id  # Store the user who ran the command

    @discord.ui.button(label="View Stats", style=discord.ButtonStyle.primary, emoji="📊")
    async def view_stats_button(self, interaction: discord.Interaction, button: Button):
        # Check if the user clicking the button is the same as the command user
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This button is not for you!", ephemeral=True)
            return

        # Fetch profile and calculate stats (same as original)
        user_id = interaction.user.id
        profile = get_player_profile(user_id)
        stats = {
            "top_speed": 0,
            "acceleration": 0,
            "overtaking": 0,
            "cornering": 0,
            "tyre_management": 0,
            "reliability": 0
        }
        scaling_factor = 1.0  # No scaling factor, as requested
        stats["top_speed"] += (profile["car_parts"]["engine"] - 5) / 5 * 8 * scaling_factor
        stats["acceleration"] += (profile["car_parts"]["engine"] - 5) / 5 * 4 * scaling_factor
        stats["acceleration"] += (profile["car_parts"]["gearbox"] - 5) / 5 * 4 * scaling_factor
        stats["overtaking"] += (profile["car_parts"]["aero"] - 5) / 5 * 6 * scaling_factor
        stats["cornering"] += (profile["car_parts"]["aero"] - 5) / 5 * 4 * scaling_factor
        stats["cornering"] += (profile["car_parts"]["chassis"] - 5) / 5 * 2 * scaling_factor
        stats["cornering"] += (profile["car_parts"]["suspension"] - 5) / 5 * 4 * scaling_factor
        stats["tyre_management"] += (profile["car_parts"]["tyres"] - 5) / 5 * 8 * scaling_factor
        stats["tyre_management"] += (profile["car_parts"]["suspension"] - 5) / 5 * 4 * scaling_factor
        stats["reliability"] += (profile["car_parts"]["chassis"] - 5) / 5 * 6 * scaling_factor
        stats["reliability"] += (profile["car_parts"]["gearbox"] - 5) / 5 * 4 * scaling_factor
        embed = discord.Embed(
            title=f"📊 {interaction.user.name}'s Stats",
            description="✦ Your car’s performance stats based on current parts ✦",
            color=discord.Color.blue()
        )
        embed.add_field(name="⚡ Top Speed", value=f"{stats['top_speed']:.1f}", inline=True)
        embed.add_field(name="🛞 Acceleration", value=f"{stats['acceleration']:.1f}", inline=True)
        embed.add_field(name="🏎️ Overtaking", value=f"{stats['overtaking']:.1f}", inline=True)
        embed.add_field(name="🔄 Cornering", value=f"{stats['cornering']:.1f}", inline=True)
        embed.add_field(name="🛟 Tyre Management", value=f"{stats['tyre_management']:.1f}", inline=True)
        embed.add_field(name="🔧 Reliability", value=f"{stats['reliability']:.1f}", inline=True)
        embed.set_footer(text="Upgrade your parts with `!upgrade` to improve stats!")

        # Send the stats embed privately to the user who clicked the button
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command(name="stats")
async def stats(ctx):
    try:
        # Create a view with the button, restricted to the user who ran the command
        view = StatsView(user_id=ctx.author.id, timeout=300)  # 5-minute timeout

        # Send initial public message with the button
        embed = discord.Embed(
            title="📊 Stats Request",
            description="Click the button below to view your stats privately.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, view=view)

    except discord.errors.Forbidden:
        await ctx.send("🚫 I don’t have permission to send messages here. Please check my permissions or try in a DM.")
    except Exception as e:
        logger.error(f"Stats command error: {e}")
        await ctx.send("❌ An error occurred while processing your request. Try again or contact support.")

@bot.command(name="upgrade")
async def upgrade(ctx, part: str):
    user_id = ctx.author.id
    profile = get_player_profile(user_id)
    part = part.lower()
    valid_parts = ["engine", "aero", "tyres", "chassis", "gearbox", "suspension"]
    if part not in valid_parts:
        embed = discord.Embed(
            title="❌ Invalid Part",
            description=f"Choose a valid part to upgrade: {', '.join(valid_parts)}.",
            color=discord.Color.red()
        )
        await ctx.author.send(embed=embed)
        await ctx.send("Check your DMs for the upgrade result!")
        return
    part_level = profile["car_parts"][part]
    if part_level >= 100:
        embed = discord.Embed(
            title="❌ Max Level Reached",
            description=f"Your {part} is already at the maximum level (100)!",
            color=discord.Color.red()
        )
        await ctx.author.send(embed=embed)
        await ctx.send("Check your DMs for the upgrade result!")
        return
    # Calculate cost based on number of upgrades for this part
    upgrade_count = profile["part_upgrade_counts"][part]
    cost = 500 + (upgrade_count * 100)  # First upgrade: 500, then +100 per upgrade
    zcoin_emoji = get_zcoin_emoji(ctx)
    if profile["zcoins"] < cost:
        embed = discord.Embed(
            title="❌ Not Enough Zcoins",
            description=f"You need {cost} {zcoin_emoji} to upgrade your {part} to level {part_level + 5}. You have {profile['zcoins']} {zcoin_emoji}.",
            color=discord.Color.red()
        )
        await ctx.author.send(embed=embed)
        await ctx.send("Check your DMs for the upgrade result!")
        return
    # Calculate stats before upgrade
    stats_before = {
        "top_speed": 0,
        "acceleration": 0,
        "overtaking": 0,
        "cornering": 0,
        "tyre_management": 0,
        "reliability": 0
    }
    scaling_factor = 1.0 
    stats_before["top_speed"] += (profile["car_parts"]["engine"] - 5) / 5 * 8 * scaling_factor
    scaling_factor = 1.0 
    stats_before["acceleration"] += (profile["car_parts"]["engine"] - 5) / 5 * 4 * scaling_factor
    scaling_factor = 1.0 
    stats_before["acceleration"] += (profile["car_parts"]["gearbox"] - 5) / 5 * 4 * scaling_factor
    scaling_factor = 1.0 
    stats_before["overtaking"] += (profile["car_parts"]["aero"] - 5) / 5 * 6 * scaling_factor
    scaling_factor = 1.0
    stats_before["cornering"] += (profile["car_parts"]["aero"] - 5) / 5 * 4 * scaling_factor
    scaling_factor = 1.0 
    stats_before["cornering"] += (profile["car_parts"]["chassis"] - 5) / 5 * 2 * scaling_factor
    scaling_factor = 1.0 
    stats_before["cornering"] += (profile["car_parts"]["suspension"] - 5) / 5 * 4 * scaling_factor
    scaling_factor = 1.0 
    stats_before["tyre_management"] += (profile["car_parts"]["tyres"] - 5) / 5 * 8 * scaling_factor
    scaling_factor = 1.0 
    stats_before["tyre_management"] += (profile["car_parts"]["suspension"] - 5) / 5 * 4 * scaling_factor
    scaling_factor = 1.0 
    stats_before["reliability"] += (profile["car_parts"]["chassis"] - 5) / 5 * 6 * scaling_factor
    scaling_factor = 1.0 
    stats_before["reliability"] += (profile["car_parts"]["gearbox"] - 5) / 5 * 4 * scaling_factor
    # Apply upgrade
    profile["zcoins"] -= cost
    profile["car_parts"][part] = min(100, part_level + 5)  # Upgrade by 5 levels, cap at 100
    profile["part_upgrade_counts"][part] += 1  # Increment upgrade count
    # Calculate stats after upgrade
    stats_after = {
        "top_speed": 0,
        "acceleration": 0,
        "overtaking": 0,
        "cornering": 0,
        "tyre_management": 0,
        "reliability": 0
    }
    scaling_factor = 1.0 
    stats_after["top_speed"] += (profile["car_parts"]["engine"] - 5) / 5 * 8 * scaling_factor
    scaling_factor = 1.0 
    stats_after["acceleration"] += (profile["car_parts"]["engine"] - 5) / 5 * 4 * scaling_factor
    scaling_factor = 1.0 
    stats_after["acceleration"] += (profile["car_parts"]["gearbox"] - 5) / 5 * 4 * scaling_factor
    scaling_factor = 1.0 
    stats_after["overtaking"] += (profile["car_parts"]["aero"] - 5) / 5 * 6 * scaling_factor
    scaling_factor = 1.0
    stats_after["cornering"] += (profile["car_parts"]["aero"] - 5) / 5 * 4 * scaling_factor
    scaling_factor = 1.0 
    stats_after["cornering"] += (profile["car_parts"]["chassis"] - 5) / 5 * 2 * scaling_factor
    scaling_factor = 1.0 
    stats_after["cornering"] += (profile["car_parts"]["suspension"] - 5) / 5 * 4 * scaling_factor
    scaling_factor = 1.0 
    stats_after["tyre_management"] += (profile["car_parts"]["tyres"] - 5) / 5 * 8 * scaling_factor
    scaling_factor = 1.0 
    stats_after["tyre_management"] += (profile["car_parts"]["suspension"] - 5) / 5 * 4 * scaling_factor
    scaling_factor = 1.0
    stats_after["reliability"] += (profile["car_parts"]["chassis"] - 5) / 5 * 6 * scaling_factor
    scaling_factor = 1.0 
    stats_after["reliability"] += (profile["car_parts"]["gearbox"] - 5) / 5 * 4 * scaling_factor
    # Calculate stat differences
    stat_changes = {}
    for stat in stats_before:
        change = stats_after[stat] - stats_before[stat]
        if change != 0:
            stat_changes[stat] = change
    # Calculate next upgrade cost
    next_upgrade_count = profile["part_upgrade_counts"][part]
    next_cost = 500 + (next_upgrade_count * 100)
    # Save changes
    save_career_stats()
    # Prepare embed
    embed = discord.Embed(
        title=f"✅ {part.capitalize()} Upgraded!",
        description=f"Your {part} is now at **level {profile['car_parts'][part]}**!\nRemaining balance: {profile['zcoins']} {zcoin_emoji}",
        color=discord.Color.green()
    )
    # Add stat changes to embed
    if stat_changes:
        stat_lines = []
        for stat, change in stat_changes.items():
            stat_name = " ".join(word.capitalize() for word in stat.split("_"))
            stat_lines.append(f"**{stat_name}**: +{change:.1f}")
        embed.add_field(
            name="📈 Stat Increases",
            value="\n".join(stat_lines),
            inline=False
        )
    # Add next upgrade cost
    if profile["car_parts"][part] < 100:
        embed.add_field(
            name="💰 Next Upgrade",
            value=f"Cost for {part.capitalize()} (to level {min(100, profile['car_parts'][part] + 5)}): **{next_cost}** {zcoin_emoji}",
            inline=False
        )
    else:
        embed.add_field(
            name="🏁 Max Level",
            value=f"Your {part} has reached the maximum level!",
            inline=False
        )
    embed.set_footer(text="Check your stats with `!stats` or garage with `!garage`.")
    await ctx.author.send(embed=embed)
    await ctx.send("Check your DMs for the upgrade result!")

class GarageView(View):
    def __init__(self, user_id: int, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.user_id = user_id  # Store the user who ran the command

    @discord.ui.button(label="View Garage", style=discord.ButtonStyle.primary, emoji="🏎️")
    async def view_garage_button(self, interaction: discord.Interaction, button: Button):
        # Check if the user clicking the button is the same as the command user
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This button is not for you!", ephemeral=True)
            return

        # Fetch profile and build garage embed (same as original)
        user_id = interaction.user.id
        profile = get_player_profile(user_id)
        parts = profile["car_parts"]
        zcoin_emoji = get_zcoin_emoji(interaction)
        embed = discord.Embed(
            title=f"🏎️ {interaction.user.name}'s Garage",
            description="✦ Your F1 car’s components. Upgrade to boost performance! ✦",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="🛠 Engine",
            value=f"Level: {parts['engine']}/100\n*+8 Top Speed, +4 Acceleration per 5 levels (scales with engine level)*",
            inline=True
        )
        embed.add_field(
            name="✈️ Aerodynamics",
            value=f"Level: {parts['aero']}/100\n*+6 Overtaking, +4 Cornering per 5 levels (scales with engine level)*",
            inline=True
        )
        embed.add_field(
            name="🛞 Tyres",
            value=f"Level: {parts['tyres']}/100\n*+8 Tyre Management per 5 levels (scales with engine level)*",
            inline=True
        )
        embed.add_field(
            name="🏎️ Chassis",
            value=f"Level: {parts['chassis']}/100\n*+6 Reliability, +2 Cornering per 5 levels (scales with engine level)*",
            inline=True
        )
        embed.add_field(
            name="⚙️ Gearbox",
            value=f"Level: {parts['gearbox']}/100\n*+4 Acceleration, +4 Reliability per 5 levels (scales with engine level)*",
            inline=True
        )
        embed.add_field(
            name="🔧 Suspension",
            value=f"Level: {parts['suspension']}/100\n*+4 Cornering, +4 Tyre Management per 5 levels (scales with engine level)*",
            inline=True
        )
        embed.add_field(
            name="💰 Balance",
            value=f"{profile['zcoins']} {zcoin_emoji}",
            inline=False
        )
        embed.set_footer(text="Use `!upgrade <part>` to improve your car (e.g., `!upgrade engine`)")

        # Send the garage embed privately to the user who clicked the button
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command(name="garage")
async def garage(ctx):
    try:
        # Create a view with the button, restricted to the user who ran the command
        view = GarageView(user_id=ctx.author.id, timeout=300)  # 5-minute timeout

        # Send initial public message with the button
        embed = discord.Embed(
            title="🏎️ Garage Request",
            description="Click the button below to view your garage privately.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, view=view)

    except discord.errors.Forbidden:
        await ctx.send("🚫 I don’t have permission to send messages here. Please check my permissions or try in a DM.")
    except Exception as e:
        logger.error(f"Garage command error: {e}")
        await ctx.send("❌ An error occurred while processing your request. Try again or contact support.")

@bot.command()
async def tm(ctx):
    user_id = ctx.author.id
    if user_id not in AUTHORIZED_TM_USERS:
        embed = discord.Embed(
            title="🏎️ Permission Denied!",
            description="You are not authorized to use this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    channel_id = ctx.channel.id
    if channel_id not in lobbies:
        embed = discord.Embed(
            title="🏎️ No Lobby Found!",
            description="No active race in this channel. Use `!create` to start one.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    lobby = lobbies[channel_id]
    if lobby["host"] != user_id:
        embed = discord.Embed(
            title="🏎️ Permission Denied!",
            description="Only the host can set the race mode.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    if lobby["status"] != "waiting":
        embed = discord.Embed(
            title="🏎️ Race In Progress!",
            description="You can’t change the race mode after the race has started.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    # Toggle race mode between "casual" and "championship"
    new_mode = "casual" if lobby["race_mode"] == "championship" else "championship"
    lobby["race_mode"] = new_mode
    embed = discord.Embed(
        title="🏎️ Race Mode Updated!",
        description=f"Lobby set to **{new_mode.capitalize()}** mode. {'Leaderboard stats will be updated.' if new_mode == 'championship' else 'Leaderboard stats will not be updated.'}",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)



