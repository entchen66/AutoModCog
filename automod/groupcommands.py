import discord
from discord.ext.commands import Greedy
from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

from .constants import *
from .utils import *
from .converters import ToggleBool
from tabulate import tabulate

groups = {
    "mentionspamrule": "mention spam",
    "wallspamrule": "wall spam",
    "inviterule": "discord invites",
    "spamrule": "general spam",
    "maxwordsrule": "maximum words",
    "maxcharsrule": "maximum characters",
    "wordfilterrule": "word filter",
}


# thanks Jackenmen#6607 <3


class GroupCommands:
    def __init__(self, *args, **kwargs):
        self.bot = kwargs.get('bot')

    # commands specific to filterword
    @commands.group()
    @checks.mod_or_permissions(manage_messages=True)
    async def wordfilterrule(self, ctx):
        """
        Detects if a word matches list of forbidden words.

        This has an optional attribute of `is_cleaned` which will attempt to remove all punctuation from the word
        in sentence. This can aid against people attempting to evade, example: `f.ilte.red`
        """
        pass

    @commands.command(name="preda")
    async def _embed_test(self, ctx):
        table = [
            [("Messages Read      : 322\n"
             "Messages Sent       : 10\n"
             "Messages Deleted    : 4\n"
             "Messages Edited     : 203\n"
             "DMs Received        : 0\n")
             ],
            [("Commands Processed  : 9\n"
                "rrors Occured      : 0\n"
            "Sessions Resumed    : 0\n")
        ]
            ]
        await ctx.send(embed=discord.Embed(description=box(tabulate(table, headers=['One', 'Two']))))

    @wordfilterrule.command(name="remove", aliases=["del"])
    @checks.mod_or_permissions(manage_messages=True)
    async def _remove_filter(self, ctx, word: str):
        """Remove a word from the list of filtered words"""
        current_filtered = await self.wordfilterrule.get_filtered_words(ctx.guild)
        current_filtered = [x['word'] for x in current_filtered]
        if word not in current_filtered:
            return await ctx.send(await error_message(f"`{word}` is not being filtered."))

        await self.wordfilterrule.remove_filter(ctx.guild, word)
        return await ctx.send(check_success(f"`{word}` has been removed from the list of filtered words."))

    @wordfilterrule.command(name="list")
    async def _show_all_filtered_words(self, ctx, word: str = None):
        """
        Show all the filtered words

        `word` adding a word parameter will show information about a single word."""
        current_filtered = await self.wordfilterrule.get_filtered_words(ctx.guild)
        if not word:
            amount_filtered = len(current_filtered)
            channels_filtering = [x['channel'] for x in current_filtered]
            channels_filtering = len(channels_filtering)
            chunked = chunks(current_filtered, 4)
            embeds = []
            for chunk in chunked:
                embed = discord.Embed(
                    title="Filtered words",
                    description=f"To show information about a single rule: `{ctx.prefix}{ctx.command} <word>`")
                embed.set_footer(text=f"Filtering {amount_filtered} words across {channels_filtering} channels")
                for word in chunk:
                    channels = word['channel']
                    chans = "\n".join('#{0}'.format(ctx.guild.get_channel(w)) for w in channels) if channels else '[Global]'
                    table = [
                        [(f"Word     : [{word['word']}]\n"
                         f"Added by : [{self.bot.get_user(word['author'])}]\n"
                         f"Cleaned  : [{word['is_cleaned']}]\n"), chans],

                    ]
                    tab = box(tabulate(table, ['Meta', 'Channels'], tablefmt="presto"), "ini")
                    embed.add_field(name=f"`{word['word']}`",
                                    value=tab,
                                    inline=False)

                embeds.append(embed)
            if embeds:
                return await menu(ctx, embeds, DEFAULT_CONTROLS)
            else:
                return await ctx.send("There is currently no words being filtered.")
        else:
            try:
                current_word = [x for x in current_filtered if x['word'] == word.lower()][0]
                channels = current_word['channel']
                chans = "\n".join('#{0}'.format(ctx.guild.get_channel(w)) for w in channels) if channels else '[Global]'
                author = self.bot.get_user(current_word['author']) or 'Not found user.'
                embed = discord.Embed(title="Word filtering",
                                      description=box(
                                          f"Word    : [{current_word['word']}]\n"
                                          f"Cleaned : [{current_word['is_cleaned']}]\n"
                                          f"Added by: [{author}]\n"
                                          f"--------\n"
                                          f"Channels\n"
                                          f"--------\n"
                                          f"{chans}", "ini"))
                return await ctx.send(embed=embed)
            except IndexError:
                return await ctx.send(await error_message(f"`{word}` is not being filtered."))

    @wordfilterrule.group(name="add")
    @checks.mod_or_permissions(manage_messages=True)
    async def add_word_to_filter(self, ctx):
        pass

    @add_word_to_filter.command(name="channel")
    async def _add_to_channels(self, ctx, word: str, channels: Greedy[discord.TextChannel] = None, is_cleaned: bool = False):
        """Add a word to the list of forbidden words

        `word`: the word to add to the filter
        `channels`: a list of channels to add this word two
        `is_cleaned`: an optional True/False argument that will remove punctuation from the word
        """
        await self.handle_adding_to_filter(ctx, word, channels, is_cleaned)

    @add_word_to_filter.command(name="group")
    async def _add_to_group(self, ctx, word: str, group_name: str, is_cleaned: bool = False):
        """Add a word to a predefined group of channels

        `word`: the word to add to the filter
        `group`: the key name of the group of channels
        `is_cleaned`: an optional True/False argument that will remove punctuation from the message
        """
        groups = await self.get_channel_groups(ctx.guild)
        if group_name not in groups:
            return await ctx.send(
                await error_message(
                    f"`{group_name}` Could not find group.")
            )
        channels = [ctx.guild.get_channel(ch) for ch in groups[group_name]]
        await self.handle_adding_to_filter(
            ctx, word, channels, is_cleaned
        )

    async def handle_adding_to_filter(self, ctx, word: str, channels: [discord.TextChannel] = None, is_cleaned: bool = False):
        word = word.lower()
        current_filtered = await self.wordfilterrule.get_filtered_words(ctx.guild)
        for values in current_filtered:
            if word in values['word']:
                return await ctx.send(await error_message(f"`{word}` is already being filtered."))
        await self.wordfilterrule.add_to_filter(
            guild=ctx.guild, word=word, author=ctx.author, channels=channels, is_cleaned=is_cleaned
        )

        nl = "\n"
        chans = nl.join('+ {0}'.format(w) for w in channels) if channels else '+ Global'
        fmt_box = box(
            f"Word       :  [{word}]\n"
            f"Cleaned    :  [{is_cleaned}]\n",
            "ini"
        )
        embed = discord.Embed(
            title=f"Word added",
            description=f"You can remove this word from the filter by running the command: `{ctx.prefix}wordfilterrule remove {word}`")
        embed.add_field(name="Word details", value=fmt_box)
        embed.add_field(name="Channels", value=box(chans, "diff"))
        return await ctx.send(embed=embed)

    # commands specific to maxwords
    @commands.group()
    @checks.mod_or_permissions(manage_messages=True)
    async def maxwordsrule(self, ctx):
        """
        Detects the maximum allowed length of individual words in a single message
        """
        pass

    @maxwordsrule.command(name="threshold")
    @checks.mod_or_permissions(manage_messages=True)
    async def _maxwords_threshold(self, ctx, max_length: int):
        """Set the threshold for the amount of individual words allowed

        For example, if the threshold is set to 4 this sentence would be caught:

        `The quick brown fox`
        """
        await self.maxwordsrule.set_max_words_length(ctx.guild, max_length)
        await ctx.send(f"`💬` The maximum number of words in one message is set to `{max_length}`")

    # commands specific to maxchars
    @commands.group()
    @checks.mod_or_permissions(manage_messages=True)
    async def maxcharsrule(self, ctx):
        """Detects the maximum allowed individual characters in a single message"""
        pass

    @maxcharsrule.command(name="threshold")
    @checks.mod_or_permissions(manage_messages=True)
    async def _max_chars_threshold(self, ctx, max_length: int):
        """Set the threshold for the amount of individual characters allowed

        For example, if the threshold is set to 10 this sentence would be caught:

        `This is too long`
        """
        await self.maxcharsrule.set_max_chars_length(ctx.guild, max_length)
        await ctx.send(
            f"`💬` The maximum number of characters in one message is set to `{max_length}`"
        )

    # commands specific to spamrule
    @commands.group()
    @checks.mod_or_permissions(manage_messages=True)
    async def spamrule(self, ctx):
        """
        Mass spamming by user or content

        1) It checks if a user has spammed more than 10 times in 12 seconds
        2) It checks if the content has been spammed 15 times in 17 seconds.
        """
        pass

    # commands specific to mention spam rule
    @commands.group()
    @checks.mod_or_permissions(manage_messages=True)
    async def mentionspamrule(self, ctx):
        """Individual mentions spam settings"""
        pass

    @mentionspamrule.command()
    @checks.mod_or_permissions(manage_messages=True)
    async def threshold(self, ctx, threshold: int):
        """Set the max amount of individual mentions allowed

        This overrides the default number of 4 individual mentions on the Mention Spam rule
        """
        before, after = await self.mentionspamrule.set_threshold(ctx, threshold)
        await ctx.send(f"`🎯` Mention threshold changed from `{before}` to `{after}`")

    # commands specific to wall spam rule
    @commands.group()
    @checks.mod_or_permissions(manage_messages=True)
    async def wallspamrule(self, ctx):
        """Walls of text/emojis settings"""
        pass

    # commands specific to discord invite rule
    @commands.group()
    @checks.mod_or_permissions(manage_messages=True)
    async def inviterule(self, ctx):
        """Filters discord invites

        Supported type of discord links:
        `discord.gg/inviteCode`
        `discordapp.com/invite/inviteCode`
        """
        pass

    @inviterule.group()
    @checks.mod_or_permissions(manage_messages=True)
    async def whitelistlink(self, ctx):
        """Add/remove/show links allowed

        Adding a link to the whitelist will allow it to be immune from automod actions"""
        pass

    @whitelistlink.command(name="add")
    @checks.mod_or_permissions(manage_messages=True)
    async def add_link(self, ctx, link: str):
        """
        Add a link to not be filtered.

        This must be the full link, supported types:

        discord.gg/inviteCode
        discordapp.com/invite/inviteCode
        """
        try:
            await self.inviterule.add_allowed_link(ctx.guild, link)
        except ValueError:
            return await ctx.send("`👆` That link already exists.")

        return await ctx.send(f"`👍` Added `{link}` to the allowed links list.")

    @whitelistlink.command(name="delete")
    @checks.mod_or_permissions(manage_messages=True)
    async def delete_link(self, ctx, link: str):
        """
        Deletes a link from the ignore list

        This must be the full exact match of a link in the list.
        """
        try:
            await self.inviterule.delete_allowed_link(ctx.guild, link)
        except ValueError as e:
            await ctx.send(f"`❌` {e.args[0]}")

    @whitelistlink.command(name="show")
    @checks.mod_or_permissions(manage_messages=True)
    async def show_links(self, ctx):
        """
        Show a list of links that are not filtered.
        """
        allowed_links = await self.inviterule.get_allowed_links(ctx.guild)
        if allowed_links is not None:
            embed = discord.Embed(
                title="Links that are not filtered by the rule",
                description=", ".join("`{0}`".format(w) for w in allowed_links),
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"`❌` No links currently allowed.")


def enable_rule_wrapper(group, name, friendly_name):
    @group.command(name="toggle")
    @checks.mod_or_permissions(manage_messages=True)
    @docstring_parameter(ToggleBool.fmt_box)
    async def enable_rule(self, ctx, toggle: ToggleBool):
        """
        Enable or disable this rule

        {0}
        """
        rule = getattr(self, name)
        is_enabled = await rule.is_enabled(ctx.guild)
        if toggle is None:
            return await ctx.send(f"{name} is `{transform_bool(is_enabled)}`.")

        if is_enabled == toggle:
            return await ctx.send(f"{name} is already `{transform_bool(is_enabled)}`")

        before, after = await rule.toggle_enabled(ctx.guild, toggle)
        await ctx.send(
            f"**{friendly_name.title()}** set from `{transform_bool(before)}` to `{transform_bool(after)}`"
        )

    return enable_rule


def action_to_take__wrapper(group, name, friendly_name):
    @group.command(name="action")
    @checks.mod_or_permissions(manage_messages=True)
    async def action_to_take(self, ctx):
        """
        Choose which action to take on an offensive message

       1) Nothing (still fires event for third-party integration)
       2) DM a role\n
       3) Add a role to offender (Mute role for example)
       4) Kick offender
       5) Ban offender
        """
        rule = getattr(self, name)
        embed = discord.Embed(
            title=f"What action should be taken against {friendly_name}?",
            description=f":one: Nothing (still fires event for third-party integration)\n"
            f":two: DM a role\n"
            f":three: Add a role to offender (Mute role for example)\n"
            f":four: Kick offender\n"
            f":five: Ban offender",
        )
        action = await get_option_reaction(ctx, embed=embed)
        if not action:
            return await ctx.send("Okay. Nothings changed.")

        await ctx.send(await thumbs_up_success(ACTION_CONFIRMATION[action]))
        if action == "add_role":
            mute_role = await rule.get_mute_role(ctx.guild)
            if mute_role is None:
                await ctx.send(
                    await error_message(
                        f"There is no role set. Add one with: `{ctx.prefix}{name} role <role>`"
                    )
                )
        await rule.set_action_to_take(action, ctx.guild)

    return action_to_take


def delete_message_wrapper(group, name, friendly_name):
    @group.command(name="delete")
    @checks.mod_or_permissions(manage_messages=True)
    async def delete_message(self, ctx):
        """
        Toggles whether message should be deleted on offence

        `manage_messages` perms are needed for this to run.
        """
        rule = getattr(self, name)
        before, after = await rule.toggle_to_delete_message(ctx.guild)
        await ctx.send(
            f"Deleting messages set from `{transform_bool(before)}` to `{transform_bool(after)}`"
        )

    return delete_message


def whitelist_wrapper(group, name, friendly_name):
    @group.group(name="whitelistrole")
    @checks.mod_or_permissions(manage_messages=True)
    async def whitelistrole(self, ctx):
        """Whitelisting roles settings

        Adding a role to the whitelist means that this role will be immune to automod actions
        """
        pass

    return whitelistrole


def whitelistrole_add_wrapper(group, name, friendly_name):
    @group.command(name="add")
    @checks.mod_or_permissions(manage_messages=True)
    async def whitelistrole_add(self, ctx, role: discord.Role):
        """
                Add a role to be ignored by automod actions"

                Passing a role already whitelisted will prompt for deletion
                """
        rule = getattr(self, name)
        try:
            await rule.append_whitelist_role(ctx.guild, role)
        except ValueError:
            await ctx.send(f"`{role}` is already whitelisted.", delete_after=30)
            result = await yes_or_no(ctx, f"Would you like to remove `{role}` from the whitelist?")
            if result:
                await rule.remove_whitelist_role(ctx.guild, role)
        await ctx.send(f"`{role}` added to the whitelist.")

    return whitelistrole_add


def whitelistrole_delete_wrapper(group, name, friendly_name):
    @group.command(name="delete")
    @checks.mod_or_permissions(manage_messages=True)
    async def whitelistrole_delete(self, ctx, role: discord.Role):
        """Delete a role from being ignored by automod actions"""
        rule = getattr(self, name)
        try:
            await rule.remove_whitelist_role(ctx.guild, role)
            return await ctx.send(f"Removed `{role}` from the whitelist.")
        except ValueError:
            return await ctx.send(f"`{role}` is not whitelisted.")

    return whitelistrole_delete


def whitelistrole_show_wrapper(group, name, friendly_name):
    @group.command(name="show")
    @checks.mod_or_permissions(manage_messages=True)
    async def whitelistrole_show(self, ctx):
        """Show all whitelisted roles"""
        rule = getattr(self, name)
        all_roles = await rule.get_all_whitelisted_roles(ctx.guild)
        if all_roles:
            desc = ", ".join("`{0}`".format(role) for role in all_roles)
            em = discord.Embed(
                title="Whitelisted roles", description=desc, color=discord.Color.greyple(),
            )
            await ctx.send(embed=em)
        else:
            await ctx.send("`❌` No roles currently whitelisted.")

    return whitelistrole_show


def add_role_wrapper(group, name, friendly_name):
    @group.command(name="role")
    @checks.mod_or_permissions(manage_messages=True)
    async def add_role(self, ctx, role: discord.Role):
        """
        Set the role to add to offender

        When a rule offence is found and action to take is set to "Add Role", this role is the one that will be added.
        """
        rule = getattr(self, name)
        before, after = await rule.set_mute_role(ctx.guild, role)

        await ctx.send(f"Role to add set from `{before}` to `{after}`")

    return add_role


def add_channel_wrapper(group, name, friendly_name):
    @group.command(name="channels")
    @checks.mod_or_permissions(manage_messages=True)
    async def add_channel(self, ctx, channels: commands.Greedy[discord.TextChannel]):
        """
        Set the channels to enforce this rule on.

        The default setting is global, passing nothing will reset to global.
        """
        rule = getattr(self, name)
        set_channels = await rule.set_enforced_channels(ctx.guild, channels)
        if not channels:
            should_clear = await yes_or_no(ctx, "Would you like to clear the channels?")
            if should_clear:
                channels = []
            else:
                return await ctx.send("Okay, no channels changed.")
        elif not channels:
            return await ctx.send("Please send me which channels you would like to enforce.")

        enforcing = await rule.set_enforced_channels(ctx.guild, channels)
        enforcing_string = "\n".join(
            "• `{0}`".format(ctx.guild.get_channel(channel)) for channel in enforcing
        )
        await ctx.send(f"Okay, done. Enforcing these channels:\n{enforcing_string}")

    return add_channel


def settings_wrapper(group, name, friendly_name):
    @group.command(name="settings")
    @checks.mod_or_permissions(manage_messages=True)
    async def _invoke_settings(self, ctx):
        """
        Show settings for this rule
        """
        rule = getattr(self, name)
        await ctx.invoke(self.bot.get_command(f"automodset show"), name)

    return _invoke_settings


for name, friendly_name in groups.items():
    group = getattr(GroupCommands, name)

    settings = settings_wrapper(group, name, friendly_name)
    settings.__name__ = f"settings_{name}"
    setattr(GroupCommands, f"settings_{name}", settings)

    enable_rule = enable_rule_wrapper(group, name, friendly_name)
    enable_rule.__name__ = f"enable_{name}"
    setattr(GroupCommands, f"enable_{name}", enable_rule)

    action_to_take = action_to_take__wrapper(group, name, friendly_name)
    action_to_take.__name__ = f"action_{name}"
    setattr(GroupCommands, f"action_{name}", action_to_take)

    delete_message = delete_message_wrapper(group, name, friendly_name)
    delete_message.__name__ = f"delete_{name}"
    setattr(GroupCommands, f"delete_{name}", delete_message)

    # whitelist settings
    # whitelist commands inherit whitelist role group
    whitelistrole = whitelist_wrapper(group, name, friendly_name)
    whitelistrole.__name__ = f"whitelistrole_{name}"
    setattr(GroupCommands, f"whitelistrole_{name}", whitelistrole)

    # whitelist group
    whitelistrole_delete = whitelistrole_delete_wrapper(whitelistrole, name, friendly_name)
    whitelistrole_delete.__name__ = f"whitelistrole_delete_{name}"
    setattr(GroupCommands, f"whitelistrole_delete_{name}", whitelistrole_delete)

    # whitelist group
    whitelistrole_add = whitelistrole_add_wrapper(whitelistrole, name, friendly_name)
    whitelistrole_add.__name__ = f"whitelistrole_add_{name}"
    setattr(GroupCommands, f"whitelistrole_add_{name}", whitelistrole_add)

    # whitelist group
    whitelistrole_show = whitelistrole_show_wrapper(whitelistrole, name, friendly_name)
    whitelistrole_show.__name__ = f"whitelistrole_show_{name}"
    setattr(GroupCommands, f"whitelistrole_show_{name}", whitelistrole_show)

    add_role = add_role_wrapper(group, name, friendly_name)
    add_role.__name__ = f"add_role_{name}"
    setattr(GroupCommands, f"add_role_{name}", add_role)

    add_channel = add_channel_wrapper(group, name, friendly_name)
    add_channel.__name__ = f"add_channel_{name}"
    setattr(GroupCommands, f"add_channel_{name}", add_channel)
