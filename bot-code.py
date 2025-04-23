import discord
from discord.ext import commands
from datetime import datetime

# Create an instance of a bot
bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

# Store assignments in a dictionary
assignments = {}

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.command()
async def add_assignment(ctx, assignment_name: str, deadline: str, *details: str):
    """Command to add a new assignment."""
    deadline_date = datetime.strptime(deadline, "%Y-%m-%d %H:%M")
    details = " ".join(details)
    assignments[assignment_name] = {"deadline": deadline_date, "details": details}
    await ctx.send(f"Assignment '{assignment_name}' added with a deadline on {deadline_date}.\nDetails: {details}")

@bot.command()
async def show_assignments(ctx):
    """Command to show all assignments and their deadlines."""
    if not assignments:
        await ctx.send("No assignments added yet.")
        return

    response = "Here are your assignments:\n"
    for assignment, info in assignments.items():
        response += f"**{assignment}** - Deadline: {info['deadline']} | Details: {info['details']}\n"
    
    await ctx.send(response)

@bot.command()
async def remove_assignment(ctx, assignment_name: str):
    """Command to remove an assignment."""
    if assignment_name in assignments:
        del assignments[assignment_name]
        await ctx.send(f"Assignment '{assignment_name}' has been removed.")
    else:
        await ctx.send(f"Assignment '{assignment_name}' not found.")

# Run the bot using your bot's token
bot.run('1364586484082016347')
