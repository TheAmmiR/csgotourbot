import discord
import uuid
import json
from typing import List, Optional

class JSONManager:
    def __init__(self, cache_file: str, *, bot: discord.Bot):
        open(cache_file, "a+")
        with open(cache_file, "r+") as f:
            if not f.read():
                f.write('{"tournaments": {}}')

        self.f = cache_file
        self.bot = bot

    def cache_tournament(self, tour_uuid: str, members: List[discord.User], message: discord.Message):
        with open(self.f, "r") as f:
            for i, user in enumerate(members):
                members[i] = user.id
            current_json = json.load(f)
            current_json["tournaments"][tour_uuid] = [message.channel.id, message.id, members]
        with open(self.f, "w") as f:
            json.dump(current_json, f, indent=2)

    async def load_tournaments(self) -> List["Tournament"]:
        with open(self.f, "r") as f:
            result = []
            for k, v in json.loads(f.read())['tournaments'].items():
                tour = Tournament(k, [self.bot.get_user(i) for i in v[2]], await (await self.bot.fetch_channel(v[0])).fetch_message(v[1]))
                result.append(tour)
                print(tour.members)

            return result

    async def get_tournament(self, tour_uuid: str) -> "Tournament":
        with open(self.f, "r") as f:
            current_json = json.loads(f.read())['tournaments']
            tour_data = current_json.get(tour_uuid)
            return Tournament(tour_uuid, [self.bot.get_user(i) for i in tour_data[2]], await (await self.bot.fetch_channel(tour_data[0])).fetch_message(tour_data[1]))


class Bot(discord.Bot):
    def run(self):
        with open("token.txt", 'r') as f:
            token = f.read()
            super().run(token)

global bot, manager
intents = discord.Intents.default()
intents.members = True

bot = Bot(intents=intents)
manager = JSONManager("cache.json", bot=bot)

class TournamentEmbed(discord.Embed):
    def __init__(self, tour: "Tournament", members: List[discord.User]):
        self.tour = tour
        super().__init__(
            title='Турнир по CS:GO',
            description=f"{len(members)}/10"
        )
        for i in range(1, 11):
            try:
                self.add_field(name=str(i), value=str(members[i - 1]), inline=(not i % 5 == 0))
            except IndexError:
                self.add_field(name=str(i), value='свободное место', inline=(not i % 5 == 0))

class TournamentJoinButton(discord.ui.Button):
    def __init__(self, tour: "Tournament"):
        self.tour = tour
        self._to_remove: List[discord.User] = []
        super().__init__(
            label="Присоединиться",
            style=discord.enums.ButtonStyle.primary,
            custom_id=self.tour.uuid
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user not in self.tour.members:
            self.tour.members.append(interaction.user)
            await self.tour.send_or_edit()
        else:
            if interaction.user not in self._to_remove:
                await interaction.response.send_message("Вы уже участвуете в турнире! Нажмите кнопку ещё раз, чтобы выйти из турнира.", ephemeral=True)
                self._to_remove.append(interaction.user)
            else:
                self.tour.members.remove(interaction.user)
                self._to_remove.remove(interaction.user)
                await self.tour.send_or_edit()
        manager.cache_tournament(self.tour.uuid, self.tour.members.copy(), self.tour.msg)

        if len(self.tour.members) == 10:
            await self.on_tour_ready()

    async def on_tour_ready(self):
        pass

class Tournament:
    def __init__(self, tour_uuid: uuid.UUID, members: Optional[List[discord.User]] = None, message: Optional[discord.Message] = None):
        self.uuid = str(tour_uuid)
        self.join_button = TournamentJoinButton(self)
        self.members: List[discord.User] = members or []
        self.msg: discord.Message = message
        self.view = discord.ui.View(timeout=None)
        self.view.add_item(self.join_button)

    async def send_or_edit(self, channel: Optional[discord.TextChannel] = None):
        print(self.members)
        if (not self.msg) or channel:
            self.msg = await channel.send(embed=TournamentEmbed(self, self.members), view=self.view)
        else:
            await self.msg.edit(embed=TournamentEmbed(self, self.members), view=self.view)

@bot.slash_command(name='create_tournament', guild_ids=[961686323129896971])
async def create_tournament(ctx):
    tournament = Tournament(uuid.uuid4())
    await tournament.send_or_edit(ctx.channel)
    await ctx.respond("Турнир успешно создан.", ephemeral=True)

@bot.event
async def on_ready():
    print("Logged in.")
    for tour in await manager.load_tournaments():
        bot.add_view(tour.view)

bot.run()
