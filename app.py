import datetime
import discord
from discord.ext import commands
import random
import asyncio
from discord.ui import View, Button
import json
import atexit

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


lobbies = {}

career_stats = {}  

default_player_profile = {
    "races": 0,
    "wins": 0,
    "podiums": 0,
    "dnfs": 0,
    "fastest_lap": None,
    "total_time": 0.0
}
GAME_MODES = {
    "solos": {
        "min_players": 2,
        "max_players": 20,
        "team_size": 1
    },
    "duos": {
        "min_players": 4,
        "max_players": 20,
        "team_size": 2,
        "require_even": True
    }
}

def get_player_profile(user_id):
    if user_id not in career_stats:
        career_stats[user_id] = default_player_profile.copy()
    return career_stats[user_id]

def save_career_stats():
    with open("career_stats.json", "w") as f:
        json.dump(career_stats, f)

def load_career_stats():
    global career_stats
    try:
        with open("career_stats.json", "r") as f:
            career_stats = json.load(f)
    except FileNotFoundError:
        career_stats = {}  



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

        weather_window = {
            "start": start,
            "end": end,
            "new_weather": new_weather
        }

    lobbies[channel_id] = {
        "host": user_id,
        "track": track_name,
        "weather": initial_weather,
        "players": [user_id],
        "status": "waiting",
        "mode": "solos",  
        "teams": {}       
    }

    
    embed = discord.Embed(
        title="🏁 New Race Lobby Created!",
        description=f"{ctx.author.mention} has created a race lobby in this channel.",
        color=discord.Color.green()
    )
    embed.add_field(name="Track", value=track_name, inline=True)
    embed.add_field(name="Weather", value=initial_weather, inline=True)
    embed.add_field(name="Length", value=f"{track_info['length_km']} km", inline=True)
    embed.add_field(name="Laps", value=f"{track_info['laps']}", inline=True)

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
        await ctx.send("❌ There's no race lobby in this channel.")
        return

    lobby = lobbies[channel_id]

    if user_id != lobby["host"]:
        await ctx.send("🚫 Only the host can start the race.")
        return

    if lobby["status"] != "waiting":
        await ctx.send("⚠️ This race has already started.")
        return

    if len(lobby["players"]) < 2:
        await ctx.send("❌ You need at least 2 players to start the race.")
        return
    
    if lobby["mode"] == "duos":
        if len(lobby["players"]) % 2 != 0:
            await ctx.send("❌ Duos mode requires an even number of players.")
            return
        
        if not lobby.get("teams"):
            _generate_teams(lobby)  
    
    lobby["status"] = "in_progress"
    lobby["current_lap"] = 1
    lobby["position_order"] = random.sample(lobby["players"], len(lobby["players"]))  
    track = TRACKS_INFO[lobby["track"]]
    total_laps = track["laps"]

    
    weather = random.choice(["Sunny", "Rainy", "Cloudy", "Windy"])
    lobby["weather"] = weather

    
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
                "dnf_reason": None
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
                pdata = lobby["player_data"][pid]
                pdata["dm_msg"] = dm_msg

            except discord.Forbidden:
                await ctx.send(f"⚠️ {user.mention} has DMs disabled.")

        except Exception as e:
            print(f"❌ Error creating or sending strategy panel for user {pid}: {e}")

    
    lights_gif_embed = discord.Embed(
        title="🔴🔴🔴🔴🟢 Lights Out!",
        description="Get ready to race...",
        color=discord.Color.red()
    )
    lights_gif_embed.set_image(url="https://media.tenor.com/RtrDuGASCoMAAAAM/f1.gif")  

    await ctx.send(embed=lights_gif_embed)


    await asyncio.sleep(7)  # 6 seconds is typical for race lights


    embed = generate_race_status_embed(lobby)
    msg = await ctx.send(embed=embed)
    lobby["status_msg_id"] = msg.id


    bot.loop.create_task(race_loop(ctx, channel_id, msg, total_laps))

async def race_loop(ctx, channel_id, status_msg, total_laps):
    lap_delay = 5  

    while channel_id in lobbies:
        lobby = lobbies[channel_id]
        current_lap = lobby["current_lap"]

    
        window = lobby.get("weather_window", {})
        start = window.get("start")
        end = window.get("end")
        new_weather = window.get("new_weather")
        initial_weather = lobby.get("initial_weather", lobby["weather"])

    
        if start and end and start <= current_lap <= end:
            if lobby["weather"] != new_weather:
                lobby["weather"] = new_weather
                await ctx.send(f"Weather has changed to **{new_weather}** on Lap {current_lap}!")
        elif lobby["weather"] != initial_weather:
            lobby["weather"] = initial_weather
            await ctx.send(f"Weather has returned to **{initial_weather}** on Lap {current_lap}!")

        if current_lap > total_laps:
            break

        await asyncio.sleep(lap_delay)
    

        base_lap_time = TRACKS_INFO[lobby["track"]]["lap_record_sec"] * 1.10
        weather = lobby["weather"]
        player_times = {}

        for pid in lobby["players"]:
            pdata = lobby["player_data"][pid]
            if pdata.get("dnf", False):
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
            else:
                just_pitted = False  


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

            else:  # Dry weather (Sunny, Cloudy, Windy)
                if tyre == "Wet":
                    tyre_wear *= 1.6  
                elif tyre == "Intermediate":
                    tyre_wear *= 1.3  

                pdata["fuel"] = max(pdata.get("fuel", 100.0) - fuel_usage, 0)
                pdata["tyre_condition"] = max(pdata.get("tyre_condition", 100.0) - tyre_wear, 0)

            if pdata["fuel"] <= 0 or pdata["tyre_condition"] <= 0:
                pdata["dnf"] = True
                pdata["dnf_lap"] = current_lap
                print(f"💀 {pid} DNFed on lap {current_lap}")
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

                ("🌦️ Light Rain", "Soft"): 1.35,
                ("🌦️ Light Rain", "Medium"): 1.25,
                ("🌦️ Light Rain", "Hard"): 1.30,
                ("🌦️ Light Rain", "Intermediate"): 1.00,  
                ("🌦️ Light Rain", "Wet"): 1.10,           

                ("🌧️ Heavy Rain", "Soft"): 1.50,
                ("🌧️ Heavy Rain", "Medium"): 1.40,
                ("🌧️ Heavy Rain", "Hard"): 1.45,
                ("🌧️ Heavy Rain", "Intermediate"): 1.15,  
                ("🌧️ Heavy Rain", "Wet"): 1.00,           

                ("☁️ Cloudy", "Soft"): 1.00,
                ("☁️ Cloudy", "Medium"): 1.00,
                ("☁️ Cloudy", "Hard"): 1.00,
                ("☁️ Cloudy", "Wet"): 1.30,
                ("☁️ Cloudy", "Intermediate"): 1.10,

                ("🌬️ Windy", "Soft"): 1.10,
                ("🌬️ Windy", "Medium"): 1.05,
                ("🌬️ Windy", "Hard"): 1.00,
                ("🌬️ Windy", "Wet"): 1.35,
                ("🌬️ Windy", "Intermediate"): 1.20
            }.get((weather, tyre), 1.15)


            
            tyre_wear_penalty = 1 + ((100 - pdata["tyre_condition"]) / 100) * 0.10  # up to +10%
            fuel_penalty = 1 + ((100 - pdata["fuel"]) / 100) * 0.05  # up to +5%


            driver_variance = random.uniform(0.985, 1.015)  
            lap_time = (base_lap_time * strat_factor * weather_penalty * tyre_wear_penalty * fuel_penalty + pit_penalty) * driver_variance


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

    
        final_order = lobby["position_order"]
    embed = discord.Embed(
        title=f"🏁 Race Finished — {lobby['track']}",
        description=f"**Weather:** {lobby['weather']} • **Mode:** {lobby['mode'].title()}",
        color=discord.Color.gold()
    )

    # Point system
    POINT_SYSTEM = {
        1: 25, 2: 18, 3: 15, 4: 12, 5: 10,
        6: 8, 7: 6, 8: 4, 9: 2, 10: 1
    }

    def format_race_time(seconds):
        minutes, secs = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        millis = int((secs % 1) * 1000)
        return f"{int(hours)}:{int(minutes):02}:{int(secs):02}.{millis:03}"

    leader_time = lobby["player_data"][final_order[0]]["total_time"] if final_order else 0

    if lobby["mode"] == "solos":
        # Solo race results (unchanged)
        podium_emojis = ["🥇", "🥈", "🥉"]
        for pos, pid in enumerate(final_order, start=1):
            user = lobby["users"][pid]
            pdata = lobby["player_data"][pid]
            total_time = pdata["total_time"]

            if pos == 1:
                time_display = format_race_time(total_time)
            else:
                gap = total_time - leader_time
                time_display = f"+{gap:.3f}s"

            medal = podium_emojis[pos-1] if pos <= 3 else f"{pos}️⃣"
            points = POINT_SYSTEM.get(pos, 0)
            embed.add_field(
                name=f"{medal} {user.display_name}",
                value=f"`{time_display}` • {points} pts",
                inline=False
            )

    else:
        # Duos race results WITH TIME GAPS
        team_results = {}
        
        # Calculate team points and gather time data
        for pos, pid in enumerate(final_order, start=1):
            team_id = next((tid for tid, pids in lobby["teams"].items() if pid in pids), None)
            if team_id:
                points = POINT_SYSTEM.get(pos, 0)
                total_time = lobby["player_data"][pid]["total_time"]
                
                if team_id not in team_results:
                    team_results[team_id] = {
                        "points": 0,
                        "members": [],
                        "best_pos": pos
                    }
                team_results[team_id]["points"] += points
                team_results[team_id]["members"].append({
                    "id": pid,
                    "position": pos,
                    "time": total_time,
                    "gap": total_time - leader_time
                })

        # Sort teams by total points (then by best single position)
        sorted_teams = sorted(
            team_results.items(),
            key=lambda x: (-x[1]["points"], x[1]["best_pos"])
        )

        # Display team results with individual time gaps
        for team_pos, (team_id, data) in enumerate(sorted_teams, start=1):
            member_lines = []
            for member in sorted(data["members"], key=lambda x: x["position"]):
                user = lobby["users"][member["id"]]
                time_display = (
                    format_race_time(member["time"]) if member["position"] == 1 
                    else f"+{member['gap']:.3f}s"
                )
                member_lines.append(
                    f"P{member['position']} {user.display_name} • `{time_display}` • {POINT_SYSTEM.get(member['position'], 0)} pts"
                )

            medal = "🥇" if team_pos == 1 else ("🥈" if team_pos == 2 else ("🥉" if team_pos == 3 else f"{team_pos}."))
            embed.add_field(
                name=f"{medal} Team {team_id} • {data['points']} pts",
                value="\n".join(member_lines),
                inline=False
            )
             # Handle DNFs
    dnfs = [pid for pid in lobby["players"] if lobby["player_data"][pid].get("dnf", False)]
    if dnfs:
        dnf_list = []
        for pid in dnfs:
            user = lobby["users"][pid]
            dnf_lap = lobby["player_data"][pid].get("dnf_lap", "?")
            dnf_list.append(f"{user.display_name} (Lap {dnf_lap})")
            
            # Update career stats for DNFs
            profile = get_player_profile(pid)
            profile["dnfs"] += 1

        embed.add_field(
            name="❌ DNFs",
            value="\n".join(dnf_list),
            inline=False
        )


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

    
    visible_players = position_order + [pid for pid in lobby["players"] if pid not in position_order]

    for pos, pid in enumerate(visible_players):
        if pid not in users or pid not in player_data:
            continue

        user = users[pid]
        pdata = player_data[pid]

        if pdata.get("dnf", False):
            continue  


        user = users[pid]
        pdata = player_data[pid]
        strategy = pdata.get("strategy", "Balanced")
        tyre = pdata.get("tyre", "Medium")

        tyre_display = tyre_emoji.get(tyre, tyre)
        strat_display = strat_emoji.get(strategy, "")

        total_time = pdata["total_time"]
        if pos == 0:
            gap = "—"
        else:
            time_gap = total_time - leader_time
            gap = f"+{time_gap:.3f}s"

        
        if strategy == "Pit Stop" and pdata.get("last_pit_lap", 0) != current_lap:
            driver_line = f"**P{pos+1}** `{user.display_name}` • 🛞 Pitting..."
        else:
            driver_line = f"**P{pos+1}** `{user.display_name}` • {tyre_display} • {strat_display} {strategy} • `{gap}`"

        embed.add_field(name="\u200b", value=driver_line, inline=False)

    
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

        
            pdata["tyre"] = view.choice

        
            pdata["fuel"] = 100.0
            pdata["tyre_condition"] = 100.0

        
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


@bot.event
async def on_ready():
    load_career_stats()  # This will load the career stats from the file
    print(f'{bot.user} has connected to Discord!')

@bot.command()
async def profile(ctx, member: discord.Member = None):
    user = member or ctx.author
    user_id = user.id

    profile = get_player_profile(user_id)

    def format_race_time(seconds):
        if seconds == 0:
            return "—"
        minutes, secs = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        millis = int((secs % 1) * 1000)
        return f"{int(hours)}:{int(minutes):02}:{int(secs):02}.{millis:03}"

    
    average_time = profile["total_time"] / profile["races"] if profile["races"] > 0 else 0
    fastest_lap = format_race_time(profile["fastest_lap"]) if profile["fastest_lap"] else "—"

    embed = discord.Embed(
        title=f"🏁 {user.display_name}'s Racing Profile",
        color=discord.Color.gold()
    )

    embed.add_field(name="Races", value=profile["races"])
    embed.add_field(name="Wins", value=profile["wins"])
    embed.add_field(name="Podiums", value=profile["podiums"])
    embed.add_field(name="DNFs", value=profile["dnfs"], inline=False)

    embed.add_field(name="Total Time", value=format_race_time(profile["total_time"]))
    embed.add_field(name="Avg Race Time", value=format_race_time(average_time))
    embed.add_field(name="Fastest Lap", value=fastest_lap)

    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx):
    """Displays a clean, formatted leaderboard of top racers."""
    if not career_stats:
        embed = discord.Embed(
            title="🏆 F1 Leaderboard",
            description="No race data yet! Start racing with `!create`.",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    sorted_stats = sorted(
        career_stats.items(),
        key=lambda x: (
            -x[1].get("wins", 0),
            -x[1].get("podiums", 0),
            -x[1].get("races", 0)
        )
    )

    embed = discord.Embed(
        title="🏆 Formula Z Global Leaderboard",
        color=discord.Color.gold()
    )
    embed.set_image(url="https://montreal.citynews.ca/wp-content/blogs.dir/sites/19/2021/12/Max-Verstappen.png")  

    leaderboard_text = []
    medal_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    for idx, (user_id, stats) in enumerate(sorted_stats[:10], 1):  
        try:
            user = await bot.fetch_user(int(user_id))
            name = user.display_name
        except:
            name = f"Unknown ({user_id})"

        medal = medal_emojis[idx-1] if idx <= 10 else f"{idx}."
        
        line = (
            f"{medal} **{name}**\n"
            f"`🏁 {stats.get('wins',0)} wins` | "
            f"`🥈 {stats.get('podiums',0)} podiums` | "
            f"`🏎️ {stats.get('races',0)} races`"
        )
        leaderboard_text.append(line)

    embed.description = "\n\n".join(leaderboard_text)
    
    # Add win percentage for top 3
    if len(sorted_stats) >= 1:
        top = sorted_stats[0][1]
        if top.get('races', 0) > 0:
            win_rate = (top['wins'] / top['races']) * 100
            embed.add_field(
                name="👑 Champion Stats",
                value=f"Win Rate: {win_rate:.1f}%\nFastest Lap: {top.get('fastest_lap', 'N/A')}s",
                inline=False
            )
    await ctx.send(embed=embed)

@bot.command(aliases=['ch'])
async def changehost(ctx, new_host: discord.Member):
    """Transfer host privileges to another player (Host only)"""
    channel_id = ctx.channel.id
    
    if channel_id not in lobbies:
        await ctx.send("❌ No active race lobby in this channel.")
        return
    
    lobby = lobbies[channel_id]
    
    if ctx.author.id != lobby["host"]:
        await ctx.send("🚫 Only the current host can transfer host privileges.")
        return
    
    if new_host.id not in lobby["players"]:
        await ctx.send(f"❌ {new_host.mention} is not in this race.")
        return
    
    old_host = lobby["host"]
    lobby["host"] = new_host.id
    
    embed = discord.Embed(
        title="👑 Host Changed",
        description=f"{ctx.author.mention} has transferred host privileges to {new_host.mention}.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)  
async def forcehost(ctx, new_host: discord.Member):
    """Forcefully change host (Admin only)"""
    channel_id = ctx.channel.id
    
    if channel_id not in lobbies:
        await ctx.send("❌ No active race lobby in this channel.")
        return
    
    lobby = lobbies[channel_id]
    
    # Check if new host is in the race
    if new_host.id not in lobby["players"]:
        await ctx.send(f"❌ {new_host.mention} is not in this race.")
        return
    
    # Change host
    old_host = lobby["host"]
    lobby["host"] = new_host.id
    
    embed = discord.Embed(
        title="⚡ Host Changed (Admin Override)",
        description=f"{ctx.author.mention} has assigned {new_host.mention} as the new host.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

@bot.command()
async def kick(ctx, member: discord.Member):
    """Kick a player from the race (Host only)"""
    channel_id = ctx.channel.id
    
    if channel_id not in lobbies:
        await ctx.send("❌ No active race lobby in this channel.")
        return
    
    lobby = lobbies[channel_id]
    
    # Check if command user is host
    if ctx.author.id != lobby["host"]:
        await ctx.send("🚫 Only the host can kick players.")
        return
    
    # Check if member is in the race
    if member.id not in lobby["players"]:
        await ctx.send(f"❌ {member.mention} is not in this race.")
        return
    
    # Cannot kick yourself
    if member.id == ctx.author.id:
        await ctx.send("🤨 You can't kick yourself. Use `!leave` instead.")
        return
    
    # Remove player
    lobby["players"].remove(member.id)
    
    # If kicked player was in position_order, remove them
    if member.id in lobby.get("position_order", []):
        lobby["position_order"].remove(member.id)
    
    # If kicked player had player_data, remove it
    if member.id in lobby.get("player_data", {}):
        del lobby["player_data"][member.id]
    
    embed = discord.Embed(
        title="🚪 Player Kicked",
        description=f"{member.mention} has been removed from the race by {ctx.author.mention}.",
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)
@bot.command(aliases=['cm'])
async def changemode(ctx, mode: str = None):
    """Switch between Solos (1-player teams) and Duos (2-player teams)"""
    channel_id = ctx.channel.id
    
    if channel_id not in lobbies:
        await ctx.send("❌ No active lobby in this channel.")
        return
    
    lobby = lobbies[channel_id]
    
    # Only host can change mode
    if ctx.author.id != lobby["host"]:
        await ctx.send("🚫 Only the host can change game mode.")
        return
    
    # Check if race already started
    if lobby["status"] != "waiting":
        await ctx.send("⚠️ Cannot change mode after race has started.")
        return
    
    mode = mode.lower() if mode else None
    
    # Validate mode
    if mode not in GAME_MODES:
        valid_modes = ", ".join(GAME_MODES.keys())
        await ctx.send(f"❌ Invalid mode. Choose: {valid_modes}")
        return
    
    # Check player count requirements
    min_players = GAME_MODES[mode]["min_players"]
    if len(lobby["players"]) < min_players:
        await ctx.send(f"❌ Need at least {min_players} players for {mode} mode.")
        return
    
    # For duos: enforce even number of players
    if mode == "duos" and len(lobby["players"]) % 2 != 0:
        await ctx.send("❌ Duos mode requires an even number of players.")
        return
    
    # Update mode and auto-generate teams if switching to duos
    lobby["mode"] = mode
    if mode == "duos":
        _generate_teams(lobby)  # Randomly assign teams
    
    embed = discord.Embed(
        title=f"🔄 Mode Changed → {mode.upper()}",
        description=f"Host {ctx.author.mention} set the mode to **{mode}**.",
        color=discord.Color.blurple()
    )
    
    if mode == "duos":
        embed.add_field(
            name="Teams",
            value=_format_teams(lobby),
            inline=False
        )
        embed.set_footer(text="Use !swap to adjust teams.")
    
    await ctx.send(embed=embed)

def _generate_teams(lobby):
    """Randomly assign teams for duos mode"""
    players = lobby["players"].copy()
    random.shuffle(players)
    
    lobby["teams"] = {}
    for i in range(0, len(players), 2):
        team_id = i // 2 + 1
        lobby["teams"][team_id] = players[i:i+2]

def _format_teams(lobby):
    """Format teams for display in embeds"""
    return "\n".join(
        f"**Team {team_id}:** {', '.join([f'<@{pid}>' for pid in players])}"
        for team_id, players in lobby["teams"].items()
    )

@bot.command()
async def swap(ctx, player1: discord.Member, player2: discord.Member):
    """Swap two players between teams (Host only)"""
    channel_id = ctx.channel.id
    
    if channel_id not in lobbies:
        await ctx.send("❌ No active lobby in this channel.")
        return
    
    lobby = lobbies[channel_id]
    
    # Only host can swap
    if ctx.author.id != lobby["host"]:
        await ctx.send("🚫 Only the host can swap players.")
        return
    
    # Check if in duos mode
    if lobby["mode"] != "duos":
        await ctx.send("❌ Team swapping only works in Duos mode.")
        return
    
    # Find which teams the players are in
    team1_id = next((tid for tid, pids in lobby["teams"].items() if player1.id in pids), None)
    team2_id = next((tid for tid, pids in lobby["teams"].items() if player2.id in pids), None)
    
    if not team1_id or not team2_id:
        await ctx.send("❌ One or both players not found in teams.")
        return
    
    # Perform swap
    lobby["teams"][team1_id].remove(player1.id)
    lobby["teams"][team2_id].remove(player2.id)
    lobby["teams"][team1_id].append(player2.id)
    lobby["teams"][team2_id].append(player1.id)
    
    embed = discord.Embed(
        title="🔄 Players Swapped",
        description=(
            f"{player1.mention} ↔️ {player2.mention}\n\n"
            f"**Updated Teams:**\n{_format_teams(lobby)}"
        ),
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)
@bot.command()
async def racers(ctx):
    """Show all racers in the lobby (team-wise in Duos mode)"""
    channel_id = ctx.channel.id
    
    if channel_id not in lobbies:
        await ctx.send("❌ No active race lobby in this channel.")
        return
    
    lobby = lobbies[channel_id]
    players = lobby["players"]
    
    # Fetch all usernames (handle deleted users gracefully)
    player_names = []
    for player_id in players:
        try:
            user = await bot.fetch_user(player_id)
            player_names.append(user.display_name)
        except:
            player_names.append(f"Unknown ({player_id})")
    
    embed = discord.Embed(
        title=f"🏎️ Racers in Lobby ({len(players)}/{GAME_MODES[lobby['mode']]['max_players']})",
        color=discord.Color.blue()
    )
    
    if lobby["mode"] == "solos":
        # Solos mode: Simple list
        embed.description = "\n".join(
            f"🏁 {name}" 
            for name in player_names
        )
        embed.set_footer(text="Solos Mode • Every racer for themselves!")
    else:
        # Duos mode: Team display
        if not lobby.get("teams"):
            _generate_teams(lobby)  # Auto-generate if missing
            
        for team_id, player_ids in lobby["teams"].items():
            teammates = []
            for pid in player_ids:
                try:
                    user = await bot.fetch_user(pid)
                    teammates.append(user.display_name)
                except:
                    teammates.append(f"Unknown ({pid})")
            
            embed.add_field(
                name=f"🚗 Team {team_id}",
                value=" • ".join(teammates),
                inline=False
            )
        embed.set_footer(text="Duos Mode • Team up for victory!")
    
    # Show host
    try:
        host_user = await bot.fetch_user(lobby["host"])
        embed.set_author(name=f"Host: {host_user.display_name}")
    except:
        pass
    
    await ctx.send(embed=embed)
def save_on_exit():
    save_career_stats()

atexit.register(save_on_exit)
