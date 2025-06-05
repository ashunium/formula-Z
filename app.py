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
    "Australia": {"length_km": 5.278, "laps": 58, "lap_record_sec": 96.5},
    "China": {"length_km": 5.451, "laps": 56, "lap_record_sec": 92.7},
    "Japan": {"length_km": 5.807, "laps": 53, "lap_record_sec": 87.6},
    "Bahrain": {"length_km": 5.412, "laps": 57, "lap_record_sec": 93.8},
    "Saudi Arabia": {"length_km": 6.174, "laps": 50, "lap_record_sec": 90.0},
    "Miami": {"length_km": 5.412, "laps": 57, "lap_record_sec": 91.8},
    "Imola": {"length_km": 4.909, "laps": 63, "lap_record_sec": 93.2},
    "Monaco": {"length_km": 3.337, "laps": 78, "lap_record_sec": 73.3},
    "Spain": {"length_km": 4.655, "laps": 66, "lap_record_sec": 85.5},
    "Canada": {"length_km": 4.361, "laps": 70, "lap_record_sec": 69.0},
    "Austria": {"length_km": 4.318, "laps": 71, "lap_record_sec": 67.2},
    "UK": {"length_km": 5.891, "laps": 52, "lap_record_sec": 90.3},
    "Belgium": {"length_km": 7.004, "laps": 44, "lap_record_sec": 102.0},
    "Hungary": {"length_km": 4.381, "laps": 70, "lap_record_sec": 71.5},
    "Netherlands": {"length_km": 4.259, "laps": 72, "lap_record_sec": 67.1},
    "Monza": {"length_km": 5.793, "laps": 53, "lap_record_sec": 83.6},
    "Azerbaijan": {"length_km": 6.003, "laps": 51, "lap_record_sec": 95.0},
    "Singapore": {"length_km": 5.063, "laps": 61, "lap_record_sec": 88.0},
    "Austin": {"length_km": 5.513, "laps": 56, "lap_record_sec": 85.7},
    "Mexico": {"length_km": 4.304, "laps": 71, "lap_record_sec": 67.6},
    "Brazil": {"length_km": 4.309, "laps": 71, "lap_record_sec": 73.0},
    "Las Vegas": {"length_km": 6.12, "laps": 50, "lap_record_sec": 89.5},
    "Qatar": {"length_km": 5.38, "laps": 57, "lap_record_sec": 91.2},
    "Abu Dhabi": {"length_km": 5.281, "laps": 55, "lap_record_sec": 90.6}
}

WEATHER_OPTIONS = ["☀️ Sunny", "🌦️ Light Rain", "🌧️ Heavy Rain", "☁️ Cloudy", "🌬️ Windy"]

F1_POINTS = {
    1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1
}

lobbies = {}
career_stats = {}
default_player_profile = {
    "races": 0, "wins": 0, "podiums": 0, "dnfs": 0, "fastest_lap": None, "total_time": 0.0, "points": 0, "skill_rating": 50, "ZCoins": 0, "last_daily": 0.0, "last_weekly": 0.0, "last_monthly": 0.0
}

def get_zcoin_emoji(guild):
    return guild.get_emoji(1379843253641285723) or "🪙"

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
    if "points" not in career_stats[user_id]:
        career_stats[user_id]["points"] = 0
    save_career_stats()
    return career_stats[user_id]

def save_player_profile(user_id, profile):
    career_stats[user_id] = profile
    save_career_stats()

def save_career_stats():
    try:
        with open("career_stats.json", "w") as f:
            json.dump(career_stats, f, indent=2)
        logger.info("💾 Saved career_stats.json")
    except (IOError, OSError) as e:
        logger.error(f"Failed to save career_stats.json: {e}")

def load_career_stats():
    global career_stats
    try:
        if os.path.exists("career_stats.json"):
            with open("career_stats.json", "r") as f:
                data = json.load(f)
                career_stats = {int(k): v for k, v in data.items()}
                for profile in career_stats.values():
                    if "points" not in profile:
                        profile["points"] = 0
                logger.info("✅ Loaded career_stats.json")
        else:
            career_stats = {}
            logger.info("ℹ️ career_stats.json not found, starting fresh")
    except json.JSONDecodeError:
        logger.error("⚠️ Corrupt career_stats.json, starting fresh")
        career_stats = {}
    except Exception as e:
        logger.error(f"❌ Error loading career_stats.json: {e}")
        career_stats = {}

def format_race_time(seconds):
    if not seconds:
        return "N/A"
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    millis = int((secs % 1) * 1000)
    return f"{int(hours)}:{int(minutes):02}:{int(secs):02}.{millis:03}"

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
        "host": user_id, "track": track_name, "weather": initial_weather, "initial_weather": initial_weather,
        "weather_window": weather_window, "players": [user_id], "users": {user_id: ctx.author},
        "status": "waiting", "mode": "solo", "teams": [], "team_names": {}
    }
    embed = discord.Embed(
        title="🏁 New Race Lobby Created!", description=f"{ctx.author.mention} has created a race lobby in this channel.",
        color=discord.Color.green()
    )
    embed.add_field(name="Track", value=track_name, inline=True)
    embed.add_field(name="Weather", value=initial_weather, inline=True)
    embed.add_field(name="Length", value=f"{track_info['length_km']} km", inline=True)
    embed.add_field(name="Laps", value=f"{track_info['laps']}", inline=True)
    embed.add_field(name="Mode", value="Solo", inline=True)
    if weather_window:
        embed.add_field(
            name="🌦️ Weather Forecast",
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
    lobby["track"] = track_name
    track_info = TRACKS_INFO[track_name]
    embed = discord.Embed(
        title="✅ Track Updated", description=f"Track set to **{track_name}** by {ctx.author.mention}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Length", value=f"{track_info['length_km']} km", inline=True)
    embed.add_field(name="Laps", value=f"{track_info['laps']}", inline=True)
    embed.add_field(name="Lap Record", value=f"{track_info['lap_record_sec']} sec", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def tracks(ctx):
    track_list = sorted(TRACKS_INFO.keys())
    track_display = "\n".join([f"• {track}" for track in track_list])
    embed = discord.Embed(
        title="🏁 Available F1 Tracks", description=track_display, color=discord.Color.gold()
    )
    embed.set_footer(text=f"Total Tracks: {len(track_list)} — Use !set <trackname> to select one")
    await ctx.send(embed=embed)

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
                "last_position": "?",
                "skill_rating": get_player_profile(pid)["skill_rating"]
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
            incident_chance = 0.99  # Set to 0.05 for production
            if random.random() < incident_chance and not lobby.get("safety_car_laps", 0) and lobby.get("status") == "in_progress":
                logger.debug(f"🎲 Incident triggered on lap {current_lap} with {incident_chance*100}% chance")
                valid_players = [pid for pid in lobby["players"] if not lobby["player_data"].get(pid, {}).get("dnf", False)]
                if valid_players:
                    pid = random.choice(valid_players)  # Pick one player for the incident
                    strategy = lobby["player_data"][pid].get("strategy", "Balanced")
                    incident_type = random.choices(
                        ["collision", "mechanical", "safety_car", "red_flag"],
                        weights=[0.5, 0.3, 0.15, 0.05] if strategy == "Push" else [0.4, 0.3, 0.2, 0.1]
                    )[0]
                    logger.debug(f"Incident for {pid}: Type={incident_type}, Strategy={strategy}")
                    if incident_type == "collision" and not lobby["player_data"][pid].get("dnf", False):
                        lobby["player_data"][pid]["dnf"] = True
                        lobby["player_data"][pid]["dnf_reason"] = "Collision"
                        profile = get_player_profile(pid)
                        profile["ZCoins"] += 5
                        save_player_profile(pid, profile)
                        user = lobby["users"].get(pid)
                        await safe_send(ctx, f"💥 **Crash!** `{user.name}` has DNF'd due to a collision! (+5 {get_zcoin_emoji(ctx.guild)} ZC)")
                    elif incident_type == "mechanical" and not lobby["player_data"][pid].get("dnf", False):
                        lobby["player_data"][pid]["dnf"] = True
                        lobby["player_data"][pid]["dnf_reason"] = "Mechanical Failure"
                        profile = get_player_profile(pid)
                        profile["ZCoins"] += 5
                        save_player_profile(pid, profile)
                        user = lobby["users"].get(pid)
                        await safe_send(ctx, f"🔧 **Mechanical Failure!** `{user.name}` has DNF'd! (+5 {get_zcoin_emoji(ctx.guild)} ZC)")
                    elif incident_type == "safety_car" and not lobby.get("safety_car_laps", 0):
                        lobby["safety_car_laps"] = random.randint(1, 3)
                        await safe_send(ctx, f"🚨 **Safety Car Deployed!** Slower laps for {lobby['safety_car_laps']} laps.")
                    elif incident_type == "red_flag":
                        lobby["status"] = "red_flag"
                        for pid in lobby["players"]:
                            if pid in lobby["users"]:
                                user = lobby["users"][pid]
                                await user.send("⛔ **Red Flag!** Race paused. Adjust your strategy in the panel.")
                        await safe_send(ctx, "⛔ **Red Flag!** Race paused. Host, use `!resume` to continue.")
                        return  # Exit race_loop until resumed
                
            track = lobby.get("track")
            if track in TRACKS_INFO:
                base_lap_time = TRACKS_INFO[track]["lap_record_sec"] * 1.1
            else:
                logger.error(f"Invalid track {track} in lobby {channel_id}")
                base_lap_time = 100.0
            weather = lobby["weather"]
            player_times = {}
            for pid in lobby["position_order"]:  # Changed from lobby["players"]
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
                if last_pit_lap == current_lap:
                    pit_penalty = 25.0
                    logger.info(f"🛞 PIT STOP TRIGGERED for {pid} on lap {current_lap} (P{lobby['position_order'].index(pid)+1})")
                    logger.debug(f"Before reset: Fuel={pdata.get('fuel')}, Tyre condition={pdata.get('tyre_condition')}")
                    pdata["fuel"] = 100.0
                    pdata["tyre_condition"] = 100.0
                    pdata["strategy"] = "Balanced"
                    logger.debug(f"After reset: Fuel={pdata['fuel']}, Tyre condition={pdata['tyre_condition']}")
                    just_pitted = True
                if lobby["position_order"].index(pid) == 0:  # Debug for P1
                    logger.debug(f"P1 {pid}: last_pit_lap={last_pit_lap}, pit_penalty={pit_penalty}, strategy={strategy}")
                if not just_pitted:
                    fuel_usage = {"Push": 6.0, "Balanced": 4.0, "Save": 2.0}.get(strategy, 4.0)
                    base_wear = {"Push": 8.0, "Balanced": 5.0, "Save": 3.0}.get(strategy, 5.0)
                    tyre_type_wear = {
                        "Soft": 1.3,
                        "Medium": 1.0,
                        "Hard": 0.7,
                        "Intermediate": 1.1,
                        "Wet": 0.9
                    }.get(tyre, 1.0)
                    tyre_wear = base_wear * tyre_type_wear
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
                    logger.debug(f"🔧 Degradation - Fuel Usage: {fuel_usage}, Tyre Wear: {tyre_wear}, Weather: {weather}")
                    prev_fuel = pdata.get("fuel", 100.0)
                    prev_tyre = pdata.get("tyre_condition", 100.0)
                    pdata["fuel"] = max(prev_fuel - fuel_usage, 0.0)
                    pdata["tyre_condition"] = max(prev_tyre - tyre_wear, 0.0)
                    logger.debug(f"Updated: Fuel {prev_fuel} -> {pdata['fuel']}, Tyre {prev_tyre} -> {pdata['tyre_condition']}")
                if pdata.get("fuel", 0.0) <= 0 or pdata.get("tyre_condition", 0.0) <= 0:
                    pdata["dnf"] = True
                    pdata["dnf_reason"] = "Out of fuel" if pdata.get("fuel", 0.0) <= 0 else "Tyres worn out"
                    logger.info(f"💀 DNF: {pid} DNFed on lap {current_lap}: {pdata['dnf_reason']}")
                    if pid in lobby["users"]:
                        await safe_send(ctx, f"❌ `{lobby['users'][pid].name}` DNFed: {pdata['dnf_reason']}!")
                    else:
                        logger.warning(f"User {pid} not found in lobby during DNF")

                if lobby.get("safety_car_laps", 0) > 0:
                    strat_factor = {
                        "Push": 0.95 * 1.2,
                        "Balanced": 1.0 * 1.2,
                        "Save": 1.05 * 1.2,
                        "Pit Stop": 1.15 * 1.2
                    }  # Slow all strategies
                    lobby["safety_car_laps"] -= 1
                    if lobby["safety_car_laps"] == 0:
                        await safe_send(ctx, "🏁 **Safety Car In!** Normal racing resumes.")
                else:
                    strat_factor = {
                        "Push": 0.95,
                        "Balanced": 1.0,
                        "Save": 1.05,
                        "Pit Stop": 1.15
                    }
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
                fuel_penalty = 1.0 + ((100.0 - pdata["fuel"]) / 100.0) * 0.05
                skill_rating = pdata.get("skill_rating", 50)
                driver_variance = random.uniform(0.98, 1.02) * (1 - (skill_rating - 50) / 1000)  # Higher skill → faster
                lap_time = (base_lap_time * strat_factor[strategy] * weather_penalty * tyre_wear_penalty * fuel_penalty + pit_penalty) * driver_variance
                pdata["lap_times"].append(lap_time)
                pdata["total_time"] += lap_time
                player_times[pid] = pdata["total_time"]
                logger.debug(f"🏎 {pid} - Strat: {strategy}, Lap: {lap_time:.2f}, Total: {pdata['total_time']:.2f}, Fuel: {pdata['fuel']:.1f}%, Tyre: {pdata['tyre_condition']:.1f}%")
            valid_players = [pid for pid in lobby["players"] if not lobby["player_data"].get(pid, {}).get("dnf", False)]
            lobby["position_order"] = sorted(valid_players, key=lambda pid: lobby["player_data"].get(pid, {}).get("total_time", float('inf')))
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
                        except (discord.HTTPException, discord.Forbidden) as e:
                            logger.warning(f"Failed to update DM for pid {pid}: {e}")
                            pdata["dm_msg"] = None
            elapsed = time.time() - lap_start_time
            await asyncio.sleep(max(0, lap_delay - elapsed))
            logger.debug(f"🏁 Finished lap {lobby['current_lap'] - 1}: Actual time = {elapsed:.2f}s")
        if channel_id not in lobbies:
            return
        final_order = lobby["position_order"]
        embed = discord.Embed(
            title=f"🏆 {lobby['track']} Grand Prix — Results",
            description=f"Weather: {lobby['weather']}",
            color=discord.Color.green()
        )
        podium_emojis = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"}
        leader_time = lobby["player_data"][final_order[0]]["total_time"] if final_order else None
        # ... earlier race_loop code ...
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
            zcoins = 50 if pos == 1 else 30 if pos == 2 else 20 if pos == 3 else 0
            zcoins += 10  # Participation
            pos_display = podium_emojis.get(pos, f"{pos}.")
            embed.add_field(
                name=f"P{pos} {pos_display}",
                value=f"{user.name} — `{time_display}` — {points} pts — +{zcoins} {get_zcoin_emoji(ctx.guild)} ZC",
                inline=True
            )
            profile = get_player_profile(pid)
            profile["points"] += points
            profile["ZCoins"] += zcoins
            profile["skill_rating"] = profile.get("skill_rating", 50)
            if pos == 1:
                profile["skill_rating"] = min(100, profile["skill_rating"] + 5)  # Win
            elif pos <= 3:
                profile["skill_rating"] = min(100, profile["skill_rating"] + 2)  # Podium
            save_player_profile(pid, profile)

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
                team_points[team_idx] = sum(F1_POINTS.get(final_order.index(pid) + 1, 0) for pid in team if pid in final_order)
            team_scores = [
                f"{lobby.get('team_names', {}).get(idx + 1, f'Team {idx + 1}')} — {points} pts"
                for idx, points in sorted(team_points.items(), key=lambda x: x[1], reverse=True)
            ]
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
                profile["skill_rating"] = profile.get("skill_rating", 50)
                profile["skill_rating"] = max(1, profile["skill_rating"] - 2)  # DNF
            if pid not in final_order[:3]:  # Only add participation ZCoins for non-podium players
                profile["ZCoins"] += 10
                save_player_profile(pid, profile)
        save_career_stats()
        await safe_send(ctx, embed=embed)
        del lobbies[channel_id]
# ... exception handling ...
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
        description=f"**Weather:** {weather} • **Lap:** {current_lap}/{total_laps}",
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
        # Determine team name based on actual team assignment
        if lobby["mode"] == "duo":
            team_name = "Unknown Team"
            for i, team in enumerate(lobby.get("teams", []), 1):
                if pid in team:
                    team_name = lobby.get("team_names", {}).get(i, f"Team {i}")
                    break
        else:
            team_name = user.name  # Use player name in solo mode
        if strategy == "Pit Stop" and pdata.get("last_pit_lap", 0) != current_lap:
            driver_line = f"**P{pos}** `{user.name}` • 🛞 Pitting..."
        else:
            driver_line = f"**P{pos}** `{user.name}` • {tyre_display} • {strat_display} {strategy} • `{gap}`"
        embed.add_field(name="\u200b", value=driver_line, inline=False)
    dnf_players = [pid for pid, pdata in player_data.items() if pdata.get("dnf", False)]
    if dnf_players:
        dnf_names = [users.get(pid, {"name": f"Unknown ({pid})"}).name for pid in dnf_players]
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
            pdata["fuel"] = 100.0
            pdata["tyre_condition"] = 100.0
            pdata["last_pit_lap"] = current_lap
            pdata["strategy"] = "Balanced"
            logger.info(f"🛞 Pit stop for {self.user_id}: Tyre={view.choice}, Lap={current_lap}")
            await interaction.followup.send(
                f"✅ Pit stop complete! You chose **{view.choice}** tyres.\n"
                f"⛽ Fuel and 🛞 tyres fully refilled.",
                ephemeral=True
            )

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
    async def _select_tyre(self, interaction, tyre):
        self.choice = tyre
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

@bot.command(name="help")
async def help(ctx):
    embed = discord.Embed(
        title="🏎️ Formula Z — Help & Guide",
        description="Welcome to the race! Here's how to play and make smart decisions.",
        color=discord.Color.teal()
    )
    embed.add_field(
        name="Commands and Gameplay",
        value=(
            "`!create` – Start a new race lobby\n"
            "`!join` – Join a race lobby\n"
            "`!start` – Start the race (host only, 2+ players)\n"
            "`!leave` – Leave the race\n"
            "`!tracks` – See all tracks\n"
            "`!set <track>` – (Host only) Set a specific track\n"
            "`!kick @user` – (Host only) Kick a racer from the lobby\n"
            "`!yeet` – (Host only) Yeet the race lobby\n"
            "`!cm <solo> or <duo>` – (Host only) Set race mode to solo or duo\n"
            "`!swap @user1 @user2` – (Host only) Swap two players' positions in the lobby\n"
            "`!lb` – View the global leaderboard\n"
            "`!profile` – View your career stats: points, races, wins, podiums, DNFs, fastest lap\n"
            "`!lobby` – Check all racers in the lobby\n"
            "`!setstrat <tyre> <strat>` – Set your initial strat before the race, eg: !setstrat Soft Push\n"
        ),
        inline=False
    )
    embed.add_field(
        name="🌦️ Weather Tips",
        value=(
            "**☀️ Sunny** – All tyres work well\n"
            "**🌧️ Rainy** – Use **Wet** or **Intermediate** tyres\n"
            "**☁️ Cloudy** – Mediums are stable\n"
            "**🌬️ Windy** – Soft tyres can be risky"
        ),
        inline=False
    )
    embed.add_field(
        name="🛞 Tyres & 📊 Strategy",
        value=(
            "**Tyres**:\n"
            "🔴 Soft – Fastest, wears quickly\n"
            "🟠 Medium – Balanced\n"
            "⚪ Hard – Durable, slowest\n"
            "🟢 Intermediate – Light rain\n"
            "🔵 Wet – Heavy rain\n\n"
            "**Strategies**:\n"
            "⚡ Push – High speed\n"
            "⚖️ Balanced – Safe default\n"
            "🛟 Save – Preserves tyres\n"
            "🛞 Pit Stop – Change tyres (adds pit delay)"
        ),
        inline=False
    )
    embed.add_field(
        name="🎮 Gameplay Features",
        value=(
            "- **Strategy Panel**: Live DM updates with position, lap, fuel, tyres, weather. Use buttons: ⚡ Push, ⚖️ Balanced, 🛟 Save, 🛞 Pit Stop.\n"
            "- **Weather**: Affects tyre wear and lap times.\n"
            "- **DNFs**: Players out of fuel/tyres listed in results with reasons.\n"
            "- **Results**: Finishers (🥇🥈🥉 for top 3, 4️⃣-🔟 for others) + DNFs."
        ),
        inline=False
    )
    embed.set_footer(text="Use your DM panel to adjust strategy during the race.")
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    load_career_stats()
    logger.info(f'🚀 {bot.user} has connected to Discord!')

@bot.command()
async def profile(ctx, user: discord.User = None):
    target_user = user if user else ctx.author
    user_id = target_user.id
    profile = get_player_profile(user_id)
    embed = discord.Embed(
        title=f"🏎️ {target_user.name}'s Career Profile",
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
    embed.add_field(name="Skill Rating", value=str(profile["skill_rating"]), inline=True)
    embed.set_footer(text="Keep racing to climb the leaderboard!")
    await ctx.send(embed=embed)

def save_on_exit():
    save_career_stats()

atexit.register(save_on_exit)

@bot.command(name="lobby")
async def lobby(ctx):
    user_id = ctx.author.id
    lobby_found = None
    for channel_id, lobby in lobbies.items():
        if user_id in lobby["players"]:
            lobby_found = lobby
            break
    if not lobby_found:
        await ctx.send("❌ You are not currently in any active race lobby.")
        return
    if "current_lap" in lobby_found and lobby_found["current_lap"] > 0:
        await ctx.send("❌ The race has already started! You cannot check the lobby now.")
        return
    track = lobby_found["track"]
    weather = lobby_found["weather"]
    if "users" not in lobby_found:
        lobby_found["users"] = {ctx.author.id: ctx.author}
    embed = discord.Embed(
        title=f"🏎️ {track} Grand Prix Lobby",
        description=f"**Weather:** {weather} • **Mode:** {lobby_found['mode'].capitalize()}",
        color=discord.Color.blue()
    )
    
    if lobby_found["mode"] == "duo":
        team_display = []
        for i, team in enumerate(lobby_found["teams"], 1):
            team_names = []
            for pid in team:
                user = lobby_found["users"].get(pid)
                if not user:
                    try:
                        user = await bot.fetch_user(pid)
                        lobby_found["users"][pid] = user
                    except (discord.NotFound, discord.HTTPException):
                        logger.warning(f"Failed to fetch user {pid} for lobby display")
                        team_names.append(f"Unknown ({pid})")
                        continue
                team_names.append(user.name)
            if team_names:
                team_name = lobby_found.get("team_names", {}).get(i, f"Team {i}")
                team_display.append(f"**{team_name}**: {', '.join(team_names)}")
        if team_display:
            embed.add_field(
                name="🤝 Teams in Lobby",
                value="\n".join(team_display),
                inline=False
            )
        else:
            embed.add_field(
                name="🤝 Teams in Lobby",
                value="No teams assigned yet.",
                inline=False
            )
    
    player_names = []
    for pid in lobby_found["players"]:  # Use players list directly, not position_order
        user = lobby_found["users"].get(pid)
        if not user:
            try:
                user = await bot.fetch_user(pid)
                lobby_found["users"][pid] = user
            except (discord.NotFound, discord.HTTPException):
                logger.warning(f"Failed to fetch user {pid} for lobby display")
                player_names.append(f"Unknown ({pid})")
                continue
        player_names.append(user.name)
    embed.add_field(
        name="🏁 Players in Lobby",
        value="\n".join(player_names) if player_names else "No players yet.",
        inline=False
    )
    
    embed.add_field(name="🚦 Race Status", value="**Waiting for all players to ready up!**", inline=False)
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
            team_display.append(f"**Team {i}**: {', '.join(team_names)}")
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
            title="🏆 Leaderboard",
            description="No players have raced yet. Start a race with `!create`!",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return
    sorted_players = sorted(
        career_stats.items(),
        key=lambda x: (-x[1]["points"], x[1]["races"])
    )
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
        emoji = number_emojis.get(rank, f"{rank}.")
        leaderboard_lines.append(f"{emoji} `{name}` — {stats['points']} points")
    embed = discord.Embed(
        title="🏆 Leaderboard",
        description="\n".join(leaderboard_lines) if leaderboard_lines else "No rankings yet!",
        color=discord.Color.red()
    )
    embed.set_footer(text="Race to earn points and climb the leaderboard!")
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

@bot.command()
async def ctn(ctx, team_number: int = None, *, custom_name: str = None):
    channel_id = ctx.channel.id
    user_id = ctx.author.id
    if channel_id not in lobbies:
        await ctx.send("❌ No active race lobby in this channel.")
        return
    lobby = lobbies[channel_id]
    if lobby["host"] != user_id:
        await ctx.send("🚫 Only the host can change team names.")
        return
    if lobby["status"] != "waiting":
        await ctx.send("🚫 Team names can only be changed before the race starts.")
        return
    if team_number is None or team_number < 1 or team_number > 10:
        await ctx.send("⚠️ Invalid team number. Choose a number between 1 and 10.")
        return
    if custom_name is None or len(custom_name.strip()) == 0:
        await ctx.send("⚠️ Invalid team name. Provide a non-empty team name.")
        return
    if len(custom_name) > 50:
        await ctx.send("⚠️ Team name too long. Keep it under 50 characters.")
        return
    if "team_names" not in lobby:
        lobby["team_names"] = {}
    lobby["team_names"][team_number] = custom_name.strip()
    await ctx.send(f"✅ Team {team_number} name set to **{custom_name.strip()}**.")

@bot.command()
async def resume(ctx):
    if ctx.channel.id not in lobbies or lobbies[ctx.channel.id]["host"] != ctx.author.id:
        await ctx.send("🚫 Only the host can resume the race.")
        return
    lobby = lobbies[ctx.channel.id]
    if lobby["status"] != "red_flag":
        await ctx.send("❌ No red flag to resume from.")
        return
    lobby["status"] = "racing"
    await ctx.send("🏁 **Race Resumed!**")
    await race_loop(ctx, ctx.channel.id, lobby["status_msg_id"], TRACKS_INFO[lobby["track"]]["laps"])

@bot.command(name="coins")
async def coins(ctx):
    user_id = ctx.author.id
    profile = get_player_profile(user_id)
    embed = discord.Embed(
        title=f"🪙 {ctx.author.name}'s ZCoins",
        description=f"**ZCoins**: {profile['ZCoins']} {get_zcoin_emoji(ctx.guild)} ZC",
        color=discord.Color.gold()
    )
    embed.set_footer(text="Earn more by racing! Shop and upgrades coming soon!")
    await ctx.send(embed=embed)

import time

@bot.command(name="daily")
async def daily(ctx):
    user_id = ctx.author.id
    profile = get_player_profile(user_id)
    current_time = time.time()
    cooldown = 24 * 3600
    last_daily = profile.get("last_daily", 0.0)
    if current_time - last_daily < cooldown:
        remaining = int(cooldown - (current_time - last_daily))
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        await ctx.send(f"⏳ You've already claimed your daily reward! Try again in {hours}h {minutes}m.")
        return
    profile["ZCoins"] += 50
    profile["last_daily"] = current_time
    save_player_profile(user_id, profile)
    embed = discord.Embed(
        title="🎉 Daily Reward Claimed!",
        description=f"You received **50 {get_zcoin_emoji(ctx.guild)} ZC**! Check your balance with `!coins`.",
        color=discord.Color.green()
    )
    embed.set_footer(text="Come back tomorrow for more!")
    await ctx.send(embed=embed)

@bot.command(name="weekly")
async def weekly(ctx):
    user_id = ctx.author.id
    profile = get_player_profile(user_id)
    current_time = time.time()
    cooldown = 7 * 24 * 3600
    last_weekly = profile.get("last_weekly", 0.0)
    if current_time - last_weekly < cooldown:
        remaining = int(cooldown - (current_time - last_weekly))
        days = remaining // (24 * 3600)
        hours = (remaining % (24 * 3600)) // 3600
        await ctx.send(f"⏳ You've already claimed your weekly reward! Try again in {days}d {hours}h.")
        return
    profile["ZCoins"] += 200
    profile["last_weekly"] = current_time
    save_player_profile(user_id, profile)
    embed = discord.Embed(
        title="🏆 Weekly Reward Claimed!",
        description=f"You received **200 {get_zcoin_emoji(ctx.guild)} ZC**! Check your balance with `!coins`.",
        color=discord.Color.green()
    )
    embed.set_footer(text="Come back next week for more!")
    await ctx.send(embed=embed)

@bot.command(name="monthly")
async def monthly(ctx):
    user_id = ctx.author.id
    profile = get_player_profile(user_id)
    current_time = time.time()
    cooldown = 30 * 24 * 3600
    last_monthly = profile.get("last_monthly", 0.0)
    if current_time - last_monthly < cooldown:
        remaining = int(cooldown - (current_time - last_monthly))
        days = remaining // (24 * 3600)
        hours = (remaining % (24 * 3600)) // 3600
        await ctx.send(f"⏳ You've already claimed your monthly reward! Try again in {days}d {hours}h.")
        return
    profile["ZCoins"] += 500
    profile["last_monthly"] = current_time
    save_player_profile(user_id, profile)
    embed = discord.Embed(
        title="🌟 Monthly Reward Claimed!",
        description=f"You received **500 {get_zcoin_emoji(ctx.guild)} ZC**! Check your balance with `!coins`.",
        color=discord.Color.green()
    )
    embed.set_footer(text="Come back next month for more!")
    await ctx.send(embed=embed)


