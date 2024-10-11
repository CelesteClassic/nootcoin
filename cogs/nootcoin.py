from discord.ext import commands
import discord

import random
import aiosqlite
import time
import numpy as np
import json
import io
import math

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw 
import textwrap

MINE_COOLDOWN = 4*60

rm_data = (
    ("100m", 0.95, 0.9),
    ("200m", 0.9, 0.0),
    ("300m", 0.95, 0.9),
    ("400m", 0.8, 0.75),
    ("500m", 0.9, 0.75),
    ("600m", 0.95, 0.0),
    ("700m", 0.8, 0.75),
    ("800m", 0.95, 0.0),
    ("900m", 0.75, 0.75),
    ("1000m", 0.75, 0.0),
    ("1100m", 0.9, 0.0),
    ("Old Site", 0.99, 0.75),
    ("1300m", 0.75, 0.75),
    ("1400m", 0.8, 0.9),
    ("1500m", 0.9, 0.9),
    ("1600m", 0.75, 0.0),
    ("1700m", 0.85, 0.75),
    ("1800m", 0.75, 0.0),
    ("1900m", 0.85, 0.75),
    ("2000m", 0.9, 0.0),
    ("2100m", 0.75, 0.0),
    ("2200m", 1.0, 0.0),
    ("2300m", 0.9, 0.5),
    ("2400m", 0.85, 0.0),
    ("2500m", 0.75, 0.5),
    ("2600m", 0.75, 0.5),
    ("2700m", 0.85, 0.0),
    ("2800m", 0.75, 0.5),
    ("2900m", 0.85, 0.5),
    ("3000m", 0.75, 0.5),
    ("Summit", 0.0, 0.0),
)

with open("fish.json") as f:
    fish_collec = json.load(f)


fish_rarity = {"common":[], "uncommon":[], "rare":[], "legendary":[], "mythic":[]}
for i, fish in enumerate(fish_collec):
    fish['id'] = i
    
    fish_rarity[fish["rarity"]].append(fish)

death_messages = {
    "common": [
        "failed a spike clip",
        "hit the bottom boundary",
        "missed a dash and died",
        "tried to spike jump with even parity",
        "died to a spike",
        "dashed into a spike (accidentally)",
        "missed balloon respawn timing"
    ],
    "uncommon": [
        'lied to a spike', 
        'dashed into a spike (intentionally)', 
        'tried to spike jump with odd parity', 
        'hit the top boundary',
        'then your controller died', 
        'activated Explorer Mode', 
        'failed your conquest', 
        'went to Helleste', 
        'starved to death', 
        'died to fall damage', 
        'overflowed dash_effect_time', 
        'got stuck in a blockclip',
        'invalidated the run',
        'got interrupted by mom'
    ],
    "rare": [
        'broke rule 0', 
        'missed the deeper intricacies', 
        'got banned from the server', 
        'had to end your stream', 
        'forgot to delete the blue pixel', 
        'deleted SSFC', 
        'saw a lizard instead of a cat', 
        'got the Nice Cream ending', 
        'got turned into a marketable plushie', 
        'heard the penguins call...', 
        'meant bruh', 
        'was not like the other girls', 
        'oh no lol you bruh', 
        'was so fat, you are die'
    ]
}

rarity_colors = {
    "mythic": 0x00E436,
    "legendary": 0xFFA300,
    "rare": 0xFF77A8,
    "uncommon": 0x29ADFF,
    "common": 0xC2C3C7
}

sgn = lambda x: 1 if x > 0 else -1 if x < 0 else 0

def play_cc(bet, gemskip):
  multiplier = 0.2
  fruits = 0
  for rm, (rm_name, p_level, p_fruit) in enumerate(rm_data):
    # berries
    if random.random() < p_fruit:
      fruits += 1
      multiplier += 0.05
    # beating the level
    p_continue = (0.5 * p_level if rm > 21 else 0.6 + 0.4 * p_level) if gemskip else p_level
    if random.random() < p_continue:
      multiplier += (1.25 + 0.25 * (rm - 22) if rm > 21 else 0.02) if gemskip else 0.10
    else:
      # run over
      multiplier = max(0, multiplier + 0.5 * sgn(multiplier - 1))
      return rm, rm_name, gemskip, fruits, round(bet * multiplier)

def PIL_to_discord(img):
    with io.BytesIO() as image_binary:
        img.save(image_binary, 'PNG')
        image_binary.seek(0)
        file = discord.File(fp=image_binary, filename='image.png')

        return file
    
class NootCoin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_load(self):
        self.db = await aiosqlite.connect("nootcoin.db")
        await self.db.execute("CREATE TABLE IF NOT EXISTS nootcoin (user_id INTEGER PRIMARY KEY, coins INTEGER);")
        await self.db.execute("CREATE TABLE IF NOT EXISTS collectables (user_id INTEGER PRIMARY KEY, fish TEXT, fish_count TEXT);")
        await self.db.execute("CREATE TABLE IF NOT EXISTS global_stats (coins_generated INTEGER, coins_spent INTEGER, coins_lost INTEGER);")
        #await self.db.execute("INSERT OR IGNORE INTO global_stats VALUES (0,0,0)")
        await self.db.commit()

        self.cooldowns = {}


    async def get_coins(self, user_id):
        cursor = await self.db.execute(f"SELECT coins FROM nootcoin WHERE user_id = {user_id}")
        value = await cursor.fetchone()

        coins = 0
        if value:
            coins = value[0]

        return coins

    async def get_fish(self, user_id):
        cursor = await self.db.execute(f"SELECT fish FROM collectables WHERE user_id = {user_id}")
        value = (await cursor.fetchone())
        if not value:
            return []

        value = value[0]

        fish_ids = list(map(lambda x: int(x), value.split(";")))
        return fish_ids

    async def get_fish_count(self, user_id):
        cursor = await self.db.execute(f"SELECT fish_count FROM collectables WHERE user_id = {user_id}")
        value = (await cursor.fetchone())
        if not value:
            return []

        value = value[0]
        if not value:
            return []

        fish_counts = {}
        for s in value.split(";"):
            vals = s.split(":")
            fish = int(vals[0])
            count = int(vals[1])
            fish_counts[fish] = count
        return fish_counts

    def fish_count_to_db(self, fish_counts):
        s = ""
        for fish, count in fish_counts.items():
            s += f"{fish}:{count};"

        if s != "":
            return s[:-1]
        else: return ""

    @commands.command(name='mine')
    async def mine(self, ctx):
        """Mine NootCoin!"""
        if (ctx.author.id in self.cooldowns):
            if (time.time() < self.cooldowns[ctx.author.id]):
                await ctx.reply(f"You are too tired to mine! You can mine again <t:{int(self.cooldowns[ctx.author.id])}:R>")
                return
        coins = random.randrange(20, 50)
        
        ignored = await self.db.execute(f"INSERT OR IGNORE INTO nootcoin VALUES ({ctx.author.id}, {coins})")
        if ignored.rowcount == 0:
            await self.db.execute(f"UPDATE nootcoin SET coins = coins + {coins} WHERE user_id = {ctx.author.id}")
        await self.db.execute(f"UPDATE global_stats SET coins_generated = coins_generated + {coins}")
        await self.db.commit()

        await ctx.reply(f"You mined **{coins}** <:nootcoin:1223140368602894408> <:yadelie:642375995961114636> (Balance: {await self.get_coins(ctx.author.id)} <:nootcoin:1223140368602894408>)")

        self.cooldowns[ctx.author.id] = time.time() + MINE_COOLDOWN

    @commands.command(name='balance', usage='[user]')
    async def balance(self, ctx, user: discord.Member=None):
        """Check your NootCoin balance"""
        user_id = ctx.author.id
        name_msg = "You have"
        if user:
            user_id = user.id
            name_msg = f"{user.name} has"

        coins = await self.get_coins(user_id)

        if (coins == 0): 
            await ctx.reply(f"{name_msg} **0** <:nootcoin:1223140368602894408> <:sadelie:642376004853039114>")
        else:
            await ctx.reply(f"{name_msg} **{coins}** <:nootcoin:1223140368602894408>")

    
    @balance.error
    async def balance_error(self, ctx, error: discord.DiscordException):
        if isinstance(error, commands.errors.MemberNotFound):
            await ctx.reply("Invalid user!")

    @commands.command(usage="<amount to bet> [normal,gemskip]")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def climb(self, ctx, bet: int | str, mode: str="normal"):
        """Climb Mt Celeste for profit"""
        gemskip = mode == "gemskip" or mode == "gs" or mode == "gimkip"
        
        coins = await self.get_coins(ctx.author.id)

        if isinstance(bet, str):
            if bet == "all":
                bet = coins
            else:
                raise commands.errors.BadArgument

        if (coins < bet):
            await ctx.reply("You don't have enough money to bet!")
            return
        if (bet <= 0):
            await ctx.reply("Please bet a valid amount!")
            return

        choice_category = random.random()
        cause = random.choice(death_messages["common"])
        if (choice_category < 0.05):
            cause = random.choice(death_messages["rare"])
        elif (choice_category < 0.20 + 0.05):
            cause = random.choice(death_messages["uncommon"])


        rm, rm_name, _, fruits, payout = play_cc(bet, gemskip)

        embed = discord.Embed(color=0x29ADFF, title="Mt. Celeste climbing results", description=f"You reached **{rm_name}** and {cause}.")

        if (rm_name == "Summit"):
            embed = discord.Embed(color=0x00E436, title="Mt. Celeste climbing results", description=f"You reached the Summit! Congratulations!")

        profit = payout-bet

        embed.add_field(name="Gemskip?", value="Yes" if gemskip else "No")
        embed.add_field(name="Berries", value=fruits)
        embed.add_field(name="Profit", value=f"**{profit}** <:nootcoin:1223140368602894408>")
        
        
        ignored = await self.db.execute(f"INSERT OR IGNORE INTO nootcoin VALUES ({ctx.author.id}, {coins})")
        if ignored.rowcount == 0:
            await self.db.execute(f"UPDATE nootcoin SET coins = coins + {profit} WHERE user_id = {ctx.author.id}")
        if profit > 0:
            await self.db.execute(f"UPDATE global_stats SET coins_generated = coins_generated + {profit}")
        elif profit < 0:
            await self.db.execute(f"UPDATE global_stats SET coins_lost = coins_lost + {-profit}")
        await self.db.commit()

        embed.add_field(name="Balance", value=f"**{coins+profit}** <:nootcoin:1223140368602894408>")
        
        await ctx.reply(embed=embed)

    @climb.error
    async def climb_error(self, ctx, error: discord.DiscordException):
        if isinstance(error, commands.errors.MissingRequiredArgument) or isinstance(error, commands.errors.BadArgument):
            embed = discord.Embed(color=0x29ADFF, title="Climb Mt. Celeste!", description="You can bet <:nootcoin:1223140368602894408> and even try your luck with gemskip!")
            embed.add_field(name="Usage", value="$climb <amount to bet, or \"all\"> [normal,gemskip]")
            embed.add_field(name="Example", value="$climb 50")
            await ctx.reply(embed=embed)
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.reply("You're going too fast! Try again in a few seconds")
        else:
            await ctx.reply("An unknown error occurred! <@107860065402245120>")
            raise error

    @commands.command(usage="[page]", aliases=["lb"])
    async def leaderboard(self, ctx, page: int = 1):

        lb_size = 15

        if (page < 1):
            raise commands.errors.BadArgument

        cursor = await self.db.execute(f"SELECT * FROM nootcoin ORDER BY coins DESC")

        people = await cursor.fetchall()

        max_pages = math.ceil(len(people)/lb_size)

        if (page > max_pages):
            raise commands.errors.BadArgument

        page -= 1

        people = people[page*lb_size:(page*lb_size)+lb_size]

        lb_str = ""
        for i, user in enumerate(people, start=1+page*lb_size):
            if i == 1:
                lb_str += "<:swagdelie:644306789420105728> "
            elif i == 2:
                lb_str += "<:slidelie:689342365013639198> "
            elif i == 3:
                lb_str += "<:yadelie:642375995961114636> "

            username = (await self.bot.fetch_user(user[0])).name
            username = discord.utils.escape_markdown(username)

            lb_str += f"{i}. {username} - {user[1]} <:nootcoin:1223140368602894408>\n"
        
        embed = discord.Embed(color=0xFFEC27, title="<:nootcoin:1223140368602894408> Leaderboard", description=lb_str)
        embed.set_footer(text=f"Page {page+1}/{max_pages}\nNext Page: $leaderboard {page+2}")
        await ctx.send(embed=embed)

    @commands.command()
    async def fish(self, ctx):

        coins = await self.get_coins(ctx.author.id)
        if (coins < 100):
            await ctx.send("You need 100 <:nootcoin:1223140368602894408> to fish!")
            return
        
        await self.db.execute(f"UPDATE nootcoin SET coins = coins - 100 WHERE user_id = {ctx.author.id}")
        await self.db.execute(f"UPDATE global_stats SET coins_spent = coins_spent + 100")
        fish_obj = random.choice(fish_rarity["common"])
        rarity_rand = random.random()

        mythic_chance = 0.001
        if (rarity_rand < mythic_chance):
            fish_obj = random.choice(fish_rarity["mythic"])
        elif (rarity_rand < 0.02+mythic_chance):
            fish_obj = random.choice(fish_rarity["legendary"])
        elif (rarity_rand < 0.13+0.02+mythic_chance):
            fish_obj = random.choice(fish_rarity["rare"])
        elif (rarity_rand < 0.35+0.15+mythic_chance):
            fish_obj = random.choice(fish_rarity["uncommon"])

        fish = fish_obj["id"]

        is_repeat = False

        ignored = await self.db.execute(f"INSERT OR IGNORE INTO collectables VALUES ({ctx.author.id}, {fish}, \"{fish}:1\")")

        item_count = None

        if ignored.rowcount == 0:
            # was ignored
            fish_counts = await self.get_fish_count(ctx.author.id)
            if (fish in await self.get_fish(ctx.author.id)):
                
                if fish not in fish_counts:
                    fish_counts[fish] = 2
                else:
                    fish_counts[fish] += 1
                is_repeat = True
                item_count = fish_counts[fish]
            else:
                await self.db.execute(f"UPDATE collectables SET fish = fish || \";{fish}\" WHERE user_id = {ctx.author.id}")
                fish_counts[fish] = 1
                
            await self.db.execute(f"UPDATE collectables SET fish_count = \"{self.fish_count_to_db(fish_counts)}\" WHERE user_id = {ctx.author.id}")
        await self.db.commit()
        
        embed = discord.Embed(color=rarity_colors[fish_obj["rarity"]], title=f"You caught: {fish_obj['name']}!")
        embed.description = f"*{fish_obj['rarity'].capitalize()}*\n\n"
        embed.description += fish_obj['description']

        if is_repeat:
            embed.description += f"\n\n*You already have this! You now have {item_count}!*"


        fish_img = Image.open(f"fish/{fish_obj['file']}")
        fish_img = fish_img.resize((128,128), Image.NEAREST)

        file = PIL_to_discord(fish_img)

        embed.set_image(url="attachment://image.png")

        await ctx.reply(file=file,embed=embed)

    async def show_item(self, ctx, item, all_fish):
        fish_obj = None
        fish_counts = await self.get_fish_count(ctx.author.id)

        count = 1

        for fish in all_fish:
            if fish_collec[fish]["name"].lower() == item.lower():
                fish_obj = fish_collec[fish]
                if fish_counts:
                    if fish in fish_counts:
                        count = fish_counts[fish]

        if not fish_obj:
            await ctx.reply(f"Could not find \"{item}\" in your collection")
            return


        embed = discord.Embed(color=rarity_colors[fish_obj["rarity"]], title=f"{fish_obj['name']}")
        embed.description = f"*{fish_obj['rarity'].capitalize()}*\n\n"
        embed.description += fish_obj['description']
        embed.description += f"\n\nYou have: **{count}**"
        fish_img = Image.open(f"fish/{fish_obj['file']}")
        fish_img = fish_img.resize((128,128), Image.NEAREST)

        file = PIL_to_discord(fish_img)

        embed.set_image(url="attachment://image.png")

        await ctx.reply(file=file, embed=embed)

    @commands.command(usage="[page]")
    async def collection(self, ctx, *, page: int | str = None):
        all_user_fish_unsorted = await self.get_fish(ctx.author.id)

        item_to_show = None

        if not page:
            page = 1
        elif isinstance(page, str):
            await self.show_item(ctx, page, all_user_fish_unsorted)
            return

        if page < 1:
            await ctx.reply("Invalid page!")
            return

        all_user_fish = []
        for rarity in rarity_colors.keys():
            for fish in all_user_fish_unsorted:
                if fish_collec[fish]["rarity"] == rarity:
                    all_user_fish.append(fish)

        page -= 1
        user_fish = all_user_fish[page*(7*4):page*(7*4)+7*4]

        if user_fish == []:
            await ctx.reply("You have nothing here <:sadelie:642376004853039114>")
            return

        im = Image.new("RGBA", size=(128*7+16*7, 128*5))

        for i, fish_id in enumerate(user_fish):
            fish_obj = fish_collec[fish_id]

            fish_img = Image.open(f"fish/{fish_obj['file']}")
            fish_img = fish_img.resize((128,128), Image.NEAREST)
            fish_pos = ((i%7)*144, (i//7)*144)
            im.paste(fish_img, fish_pos)

        for i, fish_id in enumerate(user_fish):
            fish_obj = fish_collec[fish_id]

            draw = ImageDraw.Draw(im)
            font = ImageFont.truetype("pico-8.ttf", 16)


            text_pos = (((i%7)*144), ((i//7)*144)+108)

            lines = textwrap.wrap(fish_obj["name"], width=10)

            base_h = text_pos[1]

            for i, line in enumerate(lines):

                w = draw.textlength(line, font=font)
                h = i*18

                x = ((10 - w) / 2)+text_pos[0]+60
                y = h+base_h

                draw.text((x-3, y), line, font=font, fill=(0,0,0))
                draw.text((x+3, y), line, font=font, fill=(0,0,0))
                draw.text((x, y-3), line, font=font, fill=(0,0,0))
                draw.text((x, y+3), line, font=font, fill=(0,0,0))

                draw.text((x-3, y-3), line, font=font, fill=(0,0,0))
                draw.text((x+3, y-3), line, font=font, fill=(0,0,0))
                draw.text((x-3, y+3), line, font=font, fill=(0,0,0))
                draw.text((x+3, y+3), line, font=font, fill=(0,0,0))
                draw.text((x, y), line, font=font, fill=f"#{hex(rarity_colors[fish_obj['rarity']])[2:].zfill(6)}")
                
        file = PIL_to_discord(im)
        embed = discord.Embed(color=0x83769C, title="Your collection", description=f"Total caught: {len(all_user_fish)}/{len(fish_collec)-1}")
        
        embed.set_footer(text=f"Page {page+1}/{math.ceil(len(all_user_fish)/(7*4))}\nNext Page: $collection {page+2}\nShow item: $collection (item name)")
        embed.set_image(url="attachment://image.png")

        await ctx.reply(file=file,embed=embed)

    @commands.command()
    async def stats(self, ctx):
        """ Shows global NootCoin statistics! """
        cursor = await self.db.execute("SELECT * FROM global_stats")
        values = (await cursor.fetchall())[0]

        embed = discord.Embed(color=0x29ADFF, title="Global <:nootcoin:1223140368602894408> Stats")
        embed.add_field(name="<:nootcoin:1223140368602894408> Generated", value=values[0], inline=False)
        embed.add_field(name="<:nootcoin:1223140368602894408> Spent fishing", value=values[1], inline=False)
        embed.add_field(name="<:nootcoin:1223140368602894408> Lost while climbing", value=values[2], inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(NootCoin(bot))
