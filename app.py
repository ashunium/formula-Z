import discord
from discord.ext import commands
import random
import asyncio
from discord.ui import View, Button
import json
import atexit
import os

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
    1: 25,
    2: 18,
    3: 15,
    4: 12,
    5: 10,
    6: 8,
    7: 6,
    8: 4,
    9: 2,
    10: 1
}

# Global in-memory race sessions indexed by channel id
lobbies = {}

career_stats = {}  # Keeps career stats for each player

default_player_profile = {
    "races": 0,
    "wins": 0,
    "podiums": 0,
    "dnfs": 0,
    "fastest_lap": None,
    "total_time": 0.0,
    "points": 0
}

def get_player_profile(user_id):
    if user_id not in career_stats:
        career_stats[user_id] = default_player_profile.copy()
    else:
        # Ensure existing profile has 'points' key
        if "points" not in career_stats[user_id]:
            career_stats[user_id]["points"] = 0
    save_career_stats()
    return career_stats[user_id]

def save_career_stats():
    try:
        with open("career_stats.json", "w") as f:
            json.dump(career_stats, f, indent=2)
        print("💾 Saved career_stats.json")
    except Exception as e:
        print(f"❌ Error saving career_stats.json: {e}")

def load_career_stats():
    global career_stats
    try:
        if os.path.exists("career_stats.json"):
            with open("career_stats.json", "r") as f:
                data = json.load(f)
                career_stats = {int(k): v for k, v in data.items()}  # Convert keys to int
                # Ensure all profiles have 'points'
                for profile in career_stats.values():
                    if "points" not in profile:
                        profile["points"] = 0
                print("✅ Loaded career_stats.json")
        else:
            career_stats = {}
            print("ℹ️ career_stats.json not found, starting fresh")
    except json.JSONDecodeError:
        print("⚠️ Corrupt career_stats.json, starting fresh")
        career_stats = {}
    except Exception as e:
        print(f"❌ Error loading career_stats.json: {e}")
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

    # 40% chance to have mid-race weather change
    has_weather_change = random.random() < 0.4

    weather_window = {}
    if has_weather_change:
        total_laps = track_info["laps"]
        start = random.randint(total_laps // 3, total_laps // 2)
        end = random.randint(start + 3, min(total_laps, start + 10))

        # Choose a different weather than initial
        new_weather = random.choice([w for w in WEATHER_OPTIONS if w != initial_weather])

        weather_window = {
            "start": start,
            "end": end,
            "new_weather": new_weather
        }

    lobbies[channel_id] = {
        "host": user_id,
        "track": track_name,
        "weather": initial_weather,
        "initial_weather": initial_weather,
        "weather_window": weather_window,
        "players": [user_id],
        "users": {user_id: ctx.author},
        "status": "waiting",
        "mode": "solo",  # Default to solo mode
        "teams": []  # Empty teams for solo mode
    }

    # Inform about weather change if it exists
    embed = discord.Embed(
        title="🏁 New Race Lobby Created!",
        description=f"{ctx.author.mention} has created a race lobby in this channel.",
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

    # Validate the track name
    if track_name not in TRACKS_INFO:
        # Suggest closest matching tracks (optional, basic)
        possible_tracks = [t for t in TRACKS_INFO if track_name.lower() in t.lower()]
        suggestion = f" Did you mean: {', '.join(possible_tracks)}?" if possible_tracks else ""
        await ctx.send(f"⚠️ Invalid track name.{suggestion}")
        return

    # Update track
    lobby["track"] = track_name
    track_info = TRACKS_INFO[track_name]

    embed = discord.Embed(
        title="✅ Track Updated",
        description=f"Track set to **{track_name}** by {ctx.author.mention}",
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
        title="🏁 Available F1 Tracks",
        description=track_display,
        color=discord.Color.gold()
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

    # ✅ Prevent leaving after the race has started
    if lobby["status"] != "waiting":
        await ctx.send("🚫 You can't leave the race after it has started!")
        return

    lobby["players"].remove(user_id)

    # If host left
    if user_id == lobby["host"]:
        await ctx.send("⚠️ The host left. Race lobby is closed.")
        del lobbies[channel_id]
        return

    # If no players left
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

    # Init race state
    lobby["status"] = "in_progress"
    lobby["current_lap"] = 1
    lobby["position_order"] = random.sample(lobby["players"], len(lobby["players"]))  # Random grid
    track = TRACKS_INFO[lobby["track"]]
    total_laps = track["laps"]

    # Use weather from !create (emoji-prefixed)
    weather = lobby["weather"]

    # Initialize player data and send strategy panels
    lobby["player_data"] = {}
    lobby["users"] = {}

    for pid in lobby["players"]:
        try:
            user = await bot.fetch_user(pid)
            print(f"✅ Successfully fetched user {pid}: {user.display_name}")
            lobby["users"][pid] = user
            lobby["player_data"][pid] = {
                "strategy": "Balanced",
                "tyre": "Medium",
                "last_pit_lap": 0,
                "total_time": 0.0,
                "fuel": 100.0,
                "tyre_condition": 100.0,
                "dnf": False,
                "dnf_reason": None,
                "lap_times": []  # Initialize lap_times
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
            print(f"❌ Error creating or sending strategy panel for user {pid}: {e}")

    # Initial race embed
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
    lap_delay = 20  

    while channel_id in lobbies:
        lobby = lobbies[channel_id]
        current_lap = lobby["current_lap"]

        # Weather switch logic (window-based)
        window = lobby.get("weather_window", {})
        start = window.get("start")
        end = window.get("end")
        new_weather = window.get("new_weather")
        initial_weather = lobby.get("initial_weather", lobby["weather"])

        # Decide current weather
        if start and end and start <= current_lap <= end:
            if lobby["weather"] != new_weather:
                lobby["weather"] = new_weather
                embed = discord.Embed(
                    title="🌦️ Weather Update",
                    description=f"Weather has changed to **{new_weather}** on Lap {current_lap}!",
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)
        elif lobby["weather"] != initial_weather:
            lobby["weather"] = initial_weather
            embed = discord.Embed(
                title="🌦️ Weather Update",
                description=f"Weather has returned to **{initial_weather}** on Lap {current_lap}!",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)

        if current_lap > total_laps:
            break

        await asyncio.sleep(lap_delay)

        base_lap_time = TRACKS_INFO[lobby["track"]]["lap_record_sec"] * 1.10
        weather = lobby["weather"]
        player_times = {}

        for pid in lobby["players"]:
            pdata = lobby["player_data"][pid]
            if pdata.get("dnf", False):
                print(f"⏖ Skipping DNF player {pid}")
                continue

            strategy = pdata["strategy"]
            tyre = pdata["tyre"]
            just_pitted = False
            pit_penalty = 0
            last_pit_lap = pdata.get("last_pit_lap", -2)

            if strategy == "Pit Stop" and last_pit_lap != current_lap:
                pit_penalty = 3.0  
                pdata["last_pit_lap"] = current_lap
                print(f"🛞 PIT STOP TRIGGERED for {pid} on lap {current_lap}")
                print(f"Before reset: Fuel={pdata.get('fuel')}, Tyre condition={pdata.get('tyre_condition')}")
                pdata["fuel"] = 100.0
                pdata["tyre_condition"] = 100.0
                print(f"After reset: Fuel={pdata.get('fuel')}, Tyre condition={pdata.get('tyre_condition')}")
                pdata["strategy"] = "Balanced"
                just_pitted = True

            if not just_pitted:
                fuel_usage = {"Push": 6.0, "Balanced": 4.0, "Save": 2.0}.get(strategy, 4.0)
                base_wear = {"Push": 8.0, "Balanced": 5.0, "Save": 3.0}.get(strategy, 5.0)
                tyre_type_wear = {
                    "Soft": 1.3,
                    "Medium": 1.0,
                    "Hard": 0.7,
                    "Intermediate": 1.1,
                    "Wet": 0.9
                }.get(pdata["tyre"], 1.0)
                tyre_wear = base_wear * tyre_type_wear
                if weather == "🌧️ Light Rain":
                    if tyre == "Intermediate":
                        tyre_wear *= 0.85
                    elif tyre == "Wet":
                        tyre_wear *= 1.15
                elif weather == "🌧️ Heavy Rain":
                    if tyre == "Intermediate":
                        tyre_wear *= 1.10
                    elif tyre == "Wet":
                        tyre_wear *= 0.75
                else:  # Dry weather (Sunny, Cloudy, Windy)
                    if tyre == "Wet":
                        tyre_wear *= 1.6
                    elif tyre == "Intermediate":
                        tyre_wear *= 1.3
                print(f"🔧 Degradation - Fuel Usage: {fuel_usage}, Tyre Wear: {tyre_wear}, Weather: {weather}")
                prev_fuel = pdata.get("fuel", 100.0)
                prev_tyre = pdata.get("tyre_condition", 100.0)
                pdata["fuel"] = max(prev_fuel - fuel_usage, 0)
                pdata["tyre_condition"] = max(prev_tyre - tyre_wear, 0)
                print(f"Updated - Fuel: {prev_fuel} -> {pdata['fuel']}, Tyre: {prev_tyre} -> {pdata['tyre_condition']}")

            if pdata["fuel"] <= 0 or pdata["tyre_condition"] <= 0:
                pdata["dnf"] = True
                pdata["dnf_reason"] = "Out of fuel" if pdata["fuel"] <= 0 else "Tyres worn out"
                print(f"💀 {pid} DNFed on lap {current_lap}: {pdata['dnf_reason']}")
                embed = discord.Embed(
                    title="❌ DNF",
                    description=f"{lobby['users'][pid].mention} DNFed: {pdata['dnf_reason']}!",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                continue

            strat_factor = {
                "Push": 0.95,
                "Balanced": 1.00,
                "Save": 1.05,
                "Pit Stop": 1.30
            }.get(strategy, 1.00)

            weather_penalty = {
                ("☀️ Sunny", "Soft"): 1.00,
                ("☀️ Sunny", "Medium"): 1.02,
                ("☀️ Sunny", "Hard"): 1.04,
                ("☀️ Sunny", "Wet"): 1.40,
                ("☀️ Sunny", "Intermediate"): 1.25,
                ("🌧️ Light Rain", "Soft"): 1.35,
                ("🌧️ Light Rain", "Medium"): 1.25,
                ("🌧️ Light Rain", "Hard"): 1.30,
                ("🌧️ Light Rain", "Intermediate"): 1.00,
                ("🌧️ Light Rain", "Wet"): 1.10,
                ("🌧️ Heavy Rain", "Soft"): 1.50,
                ("🌧️ Heavy Rain", "Medium"): 1.40,
                ("🌧️ Heavy Rain", "Hard"): 1.45,
                ("🌧️ Heavy Rain", "Intermediate"): 1.15,
                ("🌧️ Heavy Rain", "Wet"): 1.00,
                ("☁️ Cloudy", "Soft"): 1.00,
                ("☁️ Cloudy", "Medium"): 1.00,
                ("☁️ Cloudy", "Hard"): 1.00,
                ("☁️ Cloudy", "Wet"): 1.0,
                ("☁️ Cloudy", "Intermediate"): 1.0,
                ("🌬️ Windy", "Soft"): 1.0,
                ("🌬️ Windy", "Medium"): 1.05,
                ("🌬️ Windy", "Hard"): 1.00,
                ("🌬️ Windy", "Wet"): 1.35,
                ("🌬️ Windy", "Intermediate"): 1.20
            }.get((weather, tyre), 1.0)

            tyre_wear_penalty = 1 + ((100 - pdata["tyre_condition"]) / 100) * 0.10
            fuel_penalty = 1 + ((100 - pdata["fuel"]) / 100) * 0.05

            driver_variance = random.uniform(0.98, 1.02)
            lap_time = (base_lap_time * strat_factor * weather_penalty * tyre_wear_penalty * fuel_penalty + pit_penalty) * driver_variance

            # Store lap time
            pdata["lap_times"] = pdata.get("lap_times", []) + [lap_time]

            pdata["total_time"] += lap_time
            player_times[pid] = pdata["total_time"]

            print(f"🏎️ {pid} - Strat: {strategy}, Lap: {round(lap_time, 2)}, Total: {round(pdata['total_time'], 2)}, Fuel: {round(pdata['fuel'], 1)}%, Tyre: {round(pdata['tyre_condition'], 1)}%")

        lobby["current_lap"] += 1

        valid_players = [pid for pid in lobby["players"] if not lobby["player_data"][pid].get("dnf", False)]

        lobby["position_order"] = sorted(valid_players, key=lambda pid: lobby["player_data"][pid]["total_time"])

        embed = generate_race_status_embed(lobby)

        try:
            msg = await ctx.channel.fetch_message(lobby["status_msg_id"])
            await msg.edit(embed=embed)
        except discord.NotFound:
            await ctx.send("⚠️ Race status message not found. Ending race.")
            break

        for pid in lobby["players"]:
            user = lobby["users"].get(pid)
            pdata = lobby["player_data"].get(pid)
            if not user or not pdata:
                continue

            if pdata.get("dnf", False):
                position = "DNF"
            else:
                try:
                    position = lobby["position_order"].index(pid) + 1
                except ValueError:
                    position = "?"

            total = len(lobby["players"])
            fuel = round(pdata.get("fuel", 0), 1)
            tyre_cond = round(pdata.get("tyre_condition", 0), 1)

            weather_emoji = lobby["weather"]
            embed = discord.Embed(
                title="📊 Strategy Panel (Live)",
                description=(
                    f"📍 You are currently **P{position}** out of **{total}**.\n"
                    f"🏁 Lap **{current_lap}/{total_laps}**\n"
                    f"🌤️ Weather: **{weather_emoji}**\n"
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

            try:
                dm_msg = pdata.get("dm_msg")
                if dm_msg:
                    await dm_msg.edit(embed=embed)
            except Exception as e:
                print(f"⚠️ Failed to update DM for {user.display_name}: {e}")

            embed = discord.Embed(
                title=f"🏁 {lobby['track']} Grand Prix — Results",
                description=f"Weather: {weather_emoji.get(lobby['weather'], '')} {lobby['weather']}",
                color=discord.Color.green()
            )
            podium_emojis = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"}
            leader_time = lobby["player_data"][final_order[0]]["total_time"] if final_order else None

    for pos, pid in enumerate(final_order, 1):
        user = lobby["users"].get(pid)
        if not user:
            continue
        total_time = lobby["player_data"][pid]["total_time"]
        if pos == 1:
            time_display = format_race_time(total_time)
        else:
            gap = total_time - leader_time
            time_display = f"+{gap:.3f}s"
        points = F1_POINTS.get(pos, 0)
        pos_display = podium_emojis.get(pos, f"{pos}.")
        embed.add_field(
            name=pos_display,
            value=f"{user.display_name} — `{time_display}` — {points} pts",
            inline=False
        )
    # Update career stats with points
        profile = get_player_profile(pid)
        profile["points"] += points
    if lobby["mode"] == "duo":
        team_points = {}

    for team_idx, team in enumerate(lobby["teams"]):
        team_points[team_idx] = sum(F1_POINTS.get(final_order.index(pid) + 1, 0) for pid in team if pid in final_order)
        team_scores = [f"Team {idx + 1} - {points} pts" for idx, points in sorted(team_points.items())]
        embed.add_field(
            name="Team Score",
            value="\n".join(team_scores),
            inline=False
                )
    # Update stats for all players (including DNFs)
    for pid in lobby["players"]:
        pdata = lobby["player_data"][pid]
        profile = get_player_profile(pid)
        profile["races"] += 1
        if not pdata.get("dnf", False):
            profile["total_time"] += pdata["total_time"]
            pos = final_order.index(pid) + 1 if pid in final_order else None
            if pos == 1:
                profile["wins"] += 1
            if pos and pos <= 3:
                profile["podiums"] += 1
        if pdata.get("lap_times"):
            fastest_lap_in_race = min(pdata["lap_times"])
            if not profile["fastest_lap"] or fastest_lap_in_race < profile["fastest_lap"]:
                profile["fastest_lap"] = fastest_lap_in_race
                print(f"🏁 New fastest lap for {pid}: {fastest_lap_in_race:.2f}s")
        if pdata.get("dnf", False):
            profile["dnfs"] += 1
        pdata["lap_times"] = []

    save_career_stats()
    await ctx.send(embed=embed)
    del lobbies[channel_id]

def generate_race_status_embed(lobby):
    track = lobby["track"]
    weather = lobby["weather"]
    current_lap = lobby["current_lap"]
    total_laps = TRACKS_INFO[track]["laps"]
    position_order = lobby["position_order"]
    player_data = lobby["player_data"]
    users = lobby["users"]

    weather_emojis = {
        "Sunny": "☀️",
        "Light Rain": "🌦️",
        "Heavy Rain": "🌧️",
        "Cloudy": "☁️",
        "Windy": "🌬️"
    }

    weather_display = f"{weather_emojis.get(weather, '')} {weather}"
    embed = discord.Embed(
        title=f"🏎️ {track} Grand Prix",
        description=f"**Weather:** {weather_display} • **Lap:** {current_lap}/{total_laps}",
        color=discord.Color.red() if weather == "Sunny" else (
            discord.Color.blue() if weather == "Rainy" else discord.Color.blurple()
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
        return embed  # Nothing to show yet

    leader_time = player_data[position_order[0]]["total_time"]

    # Show all players: position_order first, then DNFs not in it
    visible_players = position_order + [pid for pid in lobby["players"] if pid not in position_order]

    for pos, pid in enumerate(position_order, 1):  # Only non-DNFs, start pos at 1
        if pid not in users or pid not in player_data:
            continue
        user = users[pid]
        pdata = player_data[pid]
        strategy = pdata.get("strategy", "Balanced")
        tyre = pdata.get("tyre", "Medium")
        tyre_display = tyre_emoji.get(tyre, tyre)
        strat_display = strat_emoji.get(strategy, "")
        total_time = pdata["total_time"]
        if pos == 1:
            gap = "—"
        else:
        # Gap to the driver immediately ahead
            prev_pid = position_order[pos-2]  # pos-1 is index, pos-2 is prev driver
            prev_time = player_data[prev_pid]["total_time"]
            time_gap = total_time - prev_time
            gap = f"+{time_gap:.3f}s"
        if strategy == "Pit Stop" and pdata.get("last_pit_lap", 0) != current_lap:
            driver_line = f"**P{pos}** `{user.display_name}` • 🛞 Pitting..."
        else:
            driver_line = f"**P{pos}** `{user.display_name}` • {tyre_display} • {strat_display} {strategy} • `{gap}`"
        embed.add_field(name="\u200b", value=driver_line, inline=False)

    # Add DNF list
    dnf_players = [pid for pid, pdata in player_data.items() if pdata.get("dnf", False)]
    if dnf_players:
        dnf_names = [users[pid].display_name for pid in dnf_players]
        embed.add_field(name="❌ DNFs", value="\n".join(dnf_names), inline=False)

    embed.set_footer(text="Use your DM strategy panel to make changes during the race.")
    return embed

class StrategyPanelView(View):
    def __init__(self, user_id, channel_id):
        super().__init__(timeout=None)  # This view stays active the whole race
        self.user_id = user_id
        self.channel_id = channel_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your car, buddy.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Push", style=discord.ButtonStyle.danger, emoji="⚡")
    async def push(self, interaction: discord.Interaction, button: Button):
        lobbies[self.channel_id]["player_data"][self.user_id]["strategy"] = "Push"
        await interaction.response.send_message("⚡ Strategy set to **Push**.", ephemeral=True)

    @discord.ui.button(label="Balanced", style=discord.ButtonStyle.primary, emoji="🚗")
    async def balanced(self, interaction: discord.Interaction, button: Button):
        lobbies[self.channel_id]["player_data"][self.user_id]["strategy"] = "Balanced"
        await interaction.response.send_message("🚗 Strategy set to **Balanced**.", ephemeral=True)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.success, emoji="🛟")
    async def save(self, interaction: discord.Interaction, button: Button):
        lobbies[self.channel_id]["player_data"][self.user_id]["strategy"] = "Save"
        await interaction.response.send_message("🛟 Strategy set to **Save**.", ephemeral=True)

    @discord.ui.button(label="Pit Stop", style=discord.ButtonStyle.secondary, emoji="🛞")
    async def pit(self, interaction: discord.Interaction, button: Button):
        view = TyreView(self.user_id)
        await interaction.response.send_message("🛠 Choose your tyre set:", view=view, ephemeral=True)
        await view.wait()

        if view.choice:
            pdata = lobbies[self.channel_id]["player_data"][self.user_id]

        # ✅ Update tyre choice
            pdata["tyre"] = view.choice

        # ✅ Refill fuel and tyre condition
            pdata["fuel"] = 100.0
            pdata["tyre_condition"] = 100.0

        # ✅ Track pit stop and set default strategy
            pdata["last_pit_lap"] = lobbies[self.channel_id]["current_lap"]
            pdata["strategy"] = "Balanced"

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
        # Only allow the correct user to interact
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

    # How to Play
    embed.add_field(
        name="🕹️ How to Play",
        value=(
            "`!create` – Start a new race lobby\n"
            "`!join` – Join a race lobby\n"
            "`!start` – Start the race (host only, 2+ players)\n"
            "`!leave` – Leave the race\n"
            "`!tracks` – See all tracks\n"
            "`!set <track>` – (Host only) Set a specific track"
        ),
        inline=False
    )

    # Weather and Tyre Effects (simplified)
    embed.add_field(
        name="🌦️ Weather Tips",
        value=(
            "**Sunny** – All tyres work well\n"
            "**Rainy** – Use **Wet** or **Intermediate** tyres\n"
            "**Cloudy** – Mediums are stable\n"
            "**Windy** – Soft tyres can be risky"
        ),
        inline=False
    )

    # Tyres and Strategy
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

    embed.set_footer(text="Use your DM panel to adjust strategy during the race.")
    await ctx.send(embed=embed)

# Add this to the bottom of your file
@bot.event
async def on_ready():
    load_career_stats()  # This will load the career stats from the file
    print(f'{bot.user} has connected to Discord!')

@bot.command()
async def profile(ctx):
    user_id = ctx.author.id
    profile = get_player_profile(user_id)

    embed = discord.Embed(
        title=f"🏎️ {ctx.author.display_name}'s Career Profile",
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
    
    # Initialize users if missing
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
                    except discord.NotFound:
                        print(f"⚠️ User {pid} not found for lobby display")
                        continue
                team_names.append(user.display_name)
            if team_names:
                team_display.append(f"**Team {i}**: {team_names[0]} & {team_names[1]}")
        embed.add_field(
            name="🤝 Teams in Lobby",
            value="\n".join(team_display) if team_display else "No teams assigned yet.",
            inline=False
        )
    else:  # Solo mode
        player_names = []
        player_list = lobby_found.get("position_order", lobby_found["players"])
        for pid in player_list:
            user = lobby_found["users"].get(pid)
            if not user:
                try:
                    user = await bot.fetch_user(pid)
                    lobby_found["users"][pid] = user
                except discord.NotFound:
                    print(f"⚠️ User {pid} not found for lobby display")
                    continue
            if "position_order" in lobby_found:
                player_names.append(f"{user.display_name} - P{lobby_found['position_order'].index(pid)+1}")
            else:
                player_names.append(f"{user.display_name}")
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

        # Randomly pair players into teams
        shuffled_players = random.sample(lobby["players"], len(lobby["players"]))
        lobby["teams"] = [shuffled_players[i:i+2] for i in range(0, len(shuffled_players), 2)]
        lobby["mode"] = "duo"

        # Display teams
        team_display = []
        for i, team in enumerate(lobby["teams"], 1):
            team_names = [lobby["users"].get(pid, await bot.fetch_user(pid)).display_name for pid in team]
            team_display.append(f"**Team {i}**: {team_names[0]} & {team_names[1]}")
        
        embed = discord.Embed(
            title="🤝 Duo Mode Activated",
            description="Players have been randomly paired into teams!",
            color=discord.Color.blue()
        )
        embed.add_field(name="Teams", value="\n".join(team_display), inline=False)
        embed.set_footer(text="Use !start to begin the race!")
        await ctx.send(embed=embed)

    else:  # mode == "solo"
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
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    if target_id not in lobby["players"]:
        embed = discord.Embed(
            title="❌ Player Not Found",
            description=f"{member.mention} is not in this race lobby.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    lobby["players"].remove(target_id)
    lobby["users"].pop(target_id, None)

    # Handle duo mode: re-pair teams if needed
    if lobby["mode"] == "duo":
        if len(lobby["players"]) % 2 != 0:
            # Odd number of players: reset to solo mode
            lobby["mode"] = "solo"
            lobby["teams"] = []
            embed = discord.Embed(
                title="✅ Player Kicked",
                description=f"{member.mention} was kicked from the lobby.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Mode Update",
                value="Odd number of players after kick. Switched to **solo** mode.",
                inline=False
            )
            await ctx.send(embed=embed)
        else:
            # Re-pair teams randomly
            shuffled_players = random.sample(lobby["players"], len(lobby["players"]))
            lobby["teams"] = [shuffled_players[i:i+2] for i in range(0, len(shuffled_players), 2)]
            team_display = []
            for i, team in enumerate(lobby["teams"], 1):
                team_names = [lobby["users"][pid].display_name for pid in team]
                team_display.append(f"**Team {i}**: {team_names[0]} & {team_names[1]}")
            embed = discord.Embed(
                title="✅ Player Kicked",
                description=f"{member.mention} was kicked from the lobby.",
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
            description=f"{member.mention} was kicked from the lobby.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    # Check if lobby is empty
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
            title="🚫⚖ Permission Denied",
            description="Only the host can swap players between teams.",          
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    if lobby["status"] != "waiting":
        embed = discord.Embed(
            title="🚫⚖️‍♂️ Race In Progress",
            description="You can’t swap players after the race has started.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    if lobby["mode"] != "duo":
        embed = discord.Embed(
            title="🚫⚖️‍♂️ Invalid Mode",
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
            title="🙃⚖️‍♂️ Invalid Action",
            description="You can’t swap the same player with themselves!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Find teams containing the players
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
            title="❌⚖️‍♂️ Swap Failed",
            description="Could not find both players in teams.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    if team1_idx == team2_idx:
        embed = discord.Embed(
            title="🚫⚖️‍♂️ Same Team",
            description="Players are on the same team. No swap needed.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Swap players
    lobby["teams"][team1_idx][pid1_pos], lobby["teams"][team2_idx][pid2_pos] = (
        lobby["teams"][team2_idx][pid2_pos],
        lobby["teams"][team1_idx][pid1_pos]
    )

    # Display updated teams
    team_display = []
    for i, team in enumerate(lobby["teams"], 1):
        team_names = [lobby["users"][pid].display_name for pid in team]
        team_display.append(f"**Team {i}**: {team_names[0]} & {team_names[1]}")

    embed = discord.Embed(
        title="🤝⚖️‍♂️ Players Swapped",
        description=f"{member1.mention} and {member2.mention} have been swapped between teams!",
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

    # Sort players by points (desc), then races (asc) for ties
    sorted_players = sorted(
        career_stats.items(),
        key=lambda x: (-x[1]["points"], x[1]["races"])
    )

    # Build leaderboard (top 10 or fewer)
    leaderboard_lines = []
    for rank, (user_id, stats) in enumerate(sorted_players[:10], 1):
        try:
            user = await bot.fetch_user(user_id)
            name = user.display_name
        except discord.NotFound:
            name = f"Unknown User ({user_id})"
        points = stats["points"]
        races = stats["races"]
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}️"
        leaderboard_lines.append(f"{medal} `{name}` — **{points} pts** ({races} races)")

    embed = discord.Embed(
        title="🏆 Formula Z Leaderboard",
        description="\n".join(leaderboard_lines) or "No data available.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Points based on F1 scoring system. Race to climb the ranks!")
    await ctx.send(embed=embed)
