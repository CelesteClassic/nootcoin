from discord.ext import commands
import discord


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    async def is_mod(ctx):
        return ctx.author.guild_permissions.manage_channels

    @commands.is_owner()
    @commands.command(name='reload', hidden=True, usage='<extension>')
    async def _reload(self, ctx, ext):
        """Reloads an extension"""
        try:
            await self.bot.reload_extension(f'cogs.{ext}')
            await ctx.send(f'The extension {ext} was reloaded!')
        except commands.ExtensionNotFound:
            await ctx.send(f'The extension {ext} doesn\'t exist.')
        except commands.ExtensionNotLoaded:
            await ctx.send(f'The extension {ext} is not loaded! (use !load)')
        except commands.NoEntryPointError:
            await ctx.send(f'The extension {ext} doesn\'t have an entry point (try adding the setup function) ')
        except commands.ExtensionFailed:
            await ctx.send(f'Some unknown error happened while trying to reload extension {ext} (check logs)')
            self.bot.logger.exception(f'Failed to reload extension {ext}:')


    @commands.command(name='announce', hidden=True)
    @commands.check(is_mod)
    async def _announce(self, ctx, channel: discord.TextChannel, *, msg):
        await channel.send(msg)

async def setup(bot):
    await bot.add_cog(Admin(bot))