import discord
from discord import app_commands, Embed, Color
from discord.ext import commands
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from enum import Enum

# --- Configuration ---
load_dotenv()

# --- Constants ---
ASSIGNMENTS_FILE = "data/assignments.json"
DATE_FORMAT = "%Y-%m-%d %H:%M"
DATE_FORMAT_HUMAN = "YYYY-MM-DD HH:MM (e.g., 2023-12-31 23:59)"
DEFAULT_COLOR = Color.blue()
MAX_ASSIGNMENTS_DISPLAY = 10

class TimeFormat(Enum):
    SHORT = 1
    LONG = 2
    RELATIVE = 3

# --- Data Storage ---
class AssignmentManager:
    @staticmethod
    def ensure_data_dir():
        os.makedirs("data", exist_ok=True)

    @staticmethod
    def load_assignments() -> Dict[str, Any]:
        AssignmentManager.ensure_data_dir()
        if os.path.exists(ASSIGNMENTS_FILE):
            with open(ASSIGNMENTS_FILE, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    @staticmethod
    def save_assignments(data: Dict[str, Any]) -> None:
        AssignmentManager.ensure_data_dir()
        with open(ASSIGNMENTS_FILE, "w") as f:
            json.dump(data, f, default=str)

    @staticmethod
    def format_deadline(deadline_str: str, style: TimeFormat = TimeFormat.LONG) -> str:
        deadline = datetime.fromisoformat(deadline_str)
        if style == TimeFormat.SHORT:
            return deadline.strftime(DATE_FORMAT)
        elif style == TimeFormat.LONG:
            return deadline.strftime("%A, %B %d %Y at %H:%M")
        else:
            now = datetime.now()
            delta = deadline - now
            if delta < timedelta(0):
                return f"{abs(delta.days)} days ago"
            elif delta < timedelta(days=1):
                return "Today"
            elif delta < timedelta(days=2):
                return "Tomorrow"
            else:
                return f"In {delta.days} days"

# --- Bot Setup ---
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Events ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Command sync error: {e}")

# --- Utility Functions ---
def create_embed(title: str, description: str = "", color: Color = DEFAULT_COLOR) -> Embed:
    return Embed(title=title, description=description, color=color)

def format_assignment(name: str, data: Dict[str, Any]) -> str:
    deadline = AssignmentManager.format_deadline(data["deadline"], TimeFormat.RELATIVE)
    details = data.get("details", "No details provided")
    return f"**{name}**\n⏰ {deadline}\n📝 {details}\n"

# --- Commands ---
@bot.tree.command(name="assignment_add", description=f"Add a new assignment (Date format: {DATE_FORMAT_HUMAN})")
@app_commands.describe(
    name="Name of the assignment",
    deadline=f"Due date ({DATE_FORMAT_HUMAN})",
    details="Additional details (optional)",
    priority="Priority level (1-5, optional)"
)
async def add_assignment(
    interaction: discord.Interaction,
    name: str,
    deadline: str,
    details: Optional[str] = None,
    priority: Optional[int] = 3
):
    try:
        deadline_date = datetime.strptime(deadline, DATE_FORMAT)
        assignments = AssignmentManager.load_assignments()
        
        assignments[name] = {
            "deadline": deadline_date.isoformat(),
            "details": details or "",
            "priority": min(max(1, priority), 5),
            "added_by": interaction.user.id,
            "added_at": datetime.now().isoformat()
        }
        
        AssignmentManager.save_assignments(assignments)
        
        embed = create_embed(
            "✅ Assignment Added",
            f"Successfully added **{name}**",
            Color.green()
        )
        embed.add_field(
            name="Due Date",
            value=AssignmentManager.format_deadline(deadline_date.isoformat(), TimeFormat.LONG),
            inline=False
        )
        if details:
            embed.add_field(name="Details", value=details, inline=False)
        embed.add_field(name="Priority", value="⭐" * priority, inline=False)
        embed.set_footer(text=f"Added by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=False)
        
    except ValueError:
        embed = create_embed(
            "❌ Invalid Date Format",
            f"Please use this exact format: `{DATE_FORMAT_HUMAN}`\nExample: `2023-12-31 23:59`",
            Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="assignment_list", description="List all upcoming assignments")
@app_commands.describe(
    show_all="Show all assignments including past ones (default: False)",
    limit="Maximum number of assignments to show"
)
async def list_assignments(
    interaction: discord.Interaction,
    show_all: bool = False,
    limit: int = MAX_ASSIGNMENTS_DISPLAY
):
    assignments = AssignmentManager.load_assignments()
    if not assignments:
        embed = create_embed(
            "📭 No Assignments",
            "You haven't added any assignments yet.",
            Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    now = datetime.now()
    upcoming = []
    past = []
    
    for name, data in assignments.items():
        deadline = datetime.fromisoformat(data["deadline"])
        if deadline >= now:
            upcoming.append((name, data, deadline))
        else:
            past.append((name, data, deadline))

    # Sort by deadline
    upcoming.sort(key=lambda x: x[2])
    past.sort(key=lambda x: x[2])
    
    assignments_to_show = upcoming + (past if show_all else [])
    
    if not assignments_to_show:
        embed = create_embed(
            "📭 No Upcoming Assignments",
            "All your assignments are completed!",
            Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    assignments_to_show = assignments_to_show[:limit]
    
    embed = create_embed(
        "📝 Your Assignments",
        f"Showing {len(assignments_to_show)} assignments",
        Color.gold()
    )
    
    for name, data, _ in assignments_to_show:
        embed.add_field(
            name=name,
            value=format_assignment(name, data),
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=False)

@bot.tree.command(name="assignment_remove", description="Remove an assignment")
@app_commands.describe(name="Name of the assignment to remove")
async def remove_assignment(interaction: discord.Interaction, name: str):
    assignments = AssignmentManager.load_assignments()
    if name in assignments:
        del assignments[name]
        AssignmentManager.save_assignments(assignments)
        embed = create_embed(
            "🗑️ Assignment Removed",
            f"**{name}** has been successfully removed.",
            Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
    else:
        embed = create_embed(
            "❌ Assignment Not Found",
            f"Couldn't find an assignment named **{name}**.",
            Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Run Bot ---
if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))