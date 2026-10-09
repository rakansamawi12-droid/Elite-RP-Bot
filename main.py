import os
import random
import datetime
import threading
import discord
from discord.ext import commands
from flask import Flask, render_template_string, request, redirect, url_for

# ==========================================
# 1. DISCORD BOT SETUP & INTENTS
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="#", intents=intents, help_command=None)

# Global Settings & Data Storage
bot_config = {
    "prefix": "#",
    "auto_role": "Member",
    "log_channel_id": 0,
    "welcome_message": "Welcome to the server! Use #id to view your profile card.",
    "anti_link": True
}

user_xp = {}
user_credits = {}
user_rep = {}
user_id_cards = {}
custom_shortcuts = {}

@bot.event
async def on_ready():
    print(f"🤖 ProBot Clone online as {bot.user.name} (ID: {bot.user.id})")

# --- Event Listener for Auto-Moderation & Custom Shortcuts ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    # Anti-Link Protection
    if bot_config["anti_link"] and "discord.gg/" in message.content.lower() and not message.author.guild_permissions.administrator:
        await message.delete()
        duration = datetime.timedelta(minutes=10)
        await message.author.timeout(duration, reason="Automated Anti-Link Protection")
        await message.channel.send(f"⚠️ {message.author.mention} was timed out for 10 minutes (Discord links are forbidden).", delete_after=5)
        return

    # Custom Shortcut Execution
    prefix = bot_config["prefix"]
    if message.content.startswith(prefix):
        cmd_trigger = message.content.split()[0][len(prefix):].lower()
        if cmd_trigger in custom_shortcuts:
            data = custom_shortcuts[cmd_trigger]
            required_role = data["role"]
            user_roles = [r.name for r in message.author.roles]
            
            if required_role.lower() == "everyone" or required_role in user_roles or message.author.guild_permissions.administrator:
                await message.channel.send(data["response"])
            else:
                await message.channel.send(f"❌ You need the **{required_role}** role to use this shortcut!", delete_after=5)
            return

    # Automated XP
    user_xp[message.author.id] = user_xp.get(message.author.id, 0) + random.randint(5, 15)
    await bot.process_commands(message)

# --- 2. GULFBOT / PROBOT IDENTITY SYSTEM (#id) ---
@bot.command(aliases=["identity"])
async def id(ctx, member: discord.Member = None):
    member = member or ctx.author
    card = user_id_cards.get(member.id, {})
    bio = card.get("bio", "No bio set yet. Use `#setbio <text>` to add one!")
    title = card.get("title", "Member")
    age = card.get("age", "N/A")
    country = card.get("country", "N/A")
    
    xp = user_xp.get(member.id, 0)
    level = xp // 100
    credits_bal = user_credits.get(member.id, 0)
    rep = user_rep.get(member.id, 0)

    embed = discord.Embed(
        title=f"🆔 Identity Card — {member.display_name}",
        description=f"*{title}*\n\n📝 **Bio:**\n{bio}",
        color=discord.Color.from_rgb(88, 101, 242)
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="🎂 Age", value=f"`{age}`", inline=True)
    embed.add_field(name="🌍 Country", value=f"`{country}`", inline=True)
    embed.add_field(name="⭐ Rep", value=f"`+{rep}`", inline=True)
    embed.add_field(name="📊 Level", value=f"`Level {level}` (`{xp} XP`)", inline=True)
    embed.add_field(name="💳 Credits", value=f"`${credits_bal:,}`", inline=True)
    embed.add_field(name="📅 Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
    embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command()
async def setbio(ctx, *, bio_text: str):
    if len(bio_text) > 150:
        await ctx.send("❌ Bio must be 150 characters or less.")
        return
    if ctx.author.id not in user_id_cards:
        user_id_cards[ctx.author.id] = {}
    user_id_cards[ctx.author.id]["bio"] = bio_text
    await ctx.send(f"✅ Bio updated for {ctx.author.mention}!")

@bot.command()
async def setid(ctx, age: str, country: str, *, title: str = "Member"):
    if ctx.author.id not in user_id_cards:
        user_id_cards[ctx.author.id] = {}
    user_id_cards[ctx.author.id]["age"] = age
    user_id_cards[ctx.author.id]["country"] = country
    user_id_cards[ctx.author.id]["title"] = title
    await ctx.send(f"✅ Identity updated! Age: `{age}` | Country: `{country}` | Title: `{title}`")

# --- 3. CUSTOM SHORTCUT COMMANDS ---
@bot.command()
@commands.has_permissions(administrator=True)
async def addcmd(ctx, name: str, role_name: str, *, response: str):
    cmd_name = name.lower().lstrip("#")
    custom_shortcuts[cmd_name] = {"role": role_name, "response": response}
    await ctx.send(f"✅ Created shortcut `#{cmd_name}` for role **{role_name}**!")

@bot.command()
@commands.has_permissions(administrator=True)
async def delcmd(ctx, name: str):
    cmd_name = name.lower().lstrip("#")
    if cmd_name in custom_shortcuts:
        del custom_shortcuts[cmd_name]
        await ctx.send(f"🗑️ Deleted shortcut `#{cmd_name}`.")

@bot.command()
async def cmds(ctx):
    if not custom_shortcuts:
        await ctx.send("📜 No custom shortcuts created yet.")
        return
    embed = discord.Embed(title="⚡ Custom Role Shortcuts", color=discord.Color.gold())
    for name, data in custom_shortcuts.items():
        embed.add_field(name=f"#{name}", value=f"🔒 Role: `{data['role']}`\n💬 Response: {data['response']}", inline=False)
    await ctx.send(embed=embed)

# --- 4. TICKET SYSTEM ---
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(" Closing ticket in 3 seconds...")
        await discord.utils.sleep_until(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=3))
        await interaction.channel.delete()

class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Open Ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="Tickets") or await guild.create_category("Tickets")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", category=category, overwrites=overwrites)
        embed = discord.Embed(title=f"🎫 Support Ticket — {interaction.user.display_name}", description="Welcome to support! Describe your issue clearly.", color=discord.Color.green())
        await channel.send(embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_tickets(ctx):
    embed = discord.Embed(title="📩 Support Tickets", description="Click the button below to open a ticket.", color=discord.Color.blurple())
    await ctx.send(embed=embed, view=TicketPanel())

# --- 5. ECONOMY & MODERATION COMMANDS ---
@bot.command()
async def daily(ctx):
    reward = random.randint(300, 700)
    user_credits[ctx.author.id] = user_credits.get(ctx.author.id, 0) + reward
    await ctx.send(f"💰 **{ctx.author.display_name}**, you claimed **+{reward}** credits!")

@bot.command()
async def credits(ctx, member: discord.Member = None):
    member = member or ctx.author
    bal = user_credits.get(member.id, 0)
    await ctx.send(f"💳 **{member.display_name}**'s Balance: **${bal:,}** credits")

@bot.command()
@commands.has_permissions(clear_messages=True)
async def clear(ctx, amount: int = 10):
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Deleted **{len(deleted) - 1}** messages.", delete_after=3)

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int = 10, *, reason="No reason provided"):
    duration = datetime.timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await ctx.send(f"⏱️ **{member.display_name}** was timed out for **{minutes}m**.")

# ==========================================
# 6. FLASK WEB DASHBOARD
# ==========================================
app = Flask(__name__)
app.secret_key = "secret_key_dashboard"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ProBot Web Dashboard</title>
    <style>
        * { box-sizing: border-box; font-family: sans-serif; }
        body { background: #0f1319; color: #fff; margin: 0; padding: 20px; }
        .card { background: #171d25; border-radius: 10px; padding: 20px; margin-bottom: 20px; }
        h1 { color: #5865f2; }
        input[type="text"] { width: 100%; padding: 10px; margin: 8px 0; background: #0f1319; color: #fff; border: 1px solid #232d39; border-radius: 5px; }
        .btn { background: #5865f2; color: #fff; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; }
    </style>
</head>
<body>
    <h1>🤖 ProBot Web Dashboard</h1>
    <form action="/update" method="POST">
        <div class="card">
            <h3>Settings</h3>
            <label>Prefix</label>
            <input type="text" name="prefix" value="{{ config.prefix }}">
            <label>Auto-Role</label>
            <input type="text" name="auto_role" value="{{ config.auto_role }}">
            <button type="submit" class="btn">Save Settings</button>
        </div>
    </form>
</body>
</html>
"""

@app.route("/")
def dashboard():
    return render_template_string(HTML_TEMPLATE, config=bot_config)

@app.route("/update", methods=["POST"])
def update():
    bot_config["prefix"] = request.form.get("prefix", "#")
    bot_config["auto_role"] = request.form.get("auto_role", "Member")
    bot.command_prefix = bot_config["prefix"]
    return redirect(url_for("dashboard"))

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# 7. RUNNING BOTH WEB DASHBOARD & BOT
# ==========================================
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    token = os.environ.get('TOKEN', 'PASTE_YOUR_BOT_TOKEN_HERE')
    bot.run(token)
