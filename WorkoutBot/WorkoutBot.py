# pip install -U git+https://github.com/Rapptz/discord.py@rewrite#egg=discord.py[voice]
import discord
import asyncio
import traceback
import random
import json
import os.path
from collections import namedtuple

CLIENT_ID = "TODO: insert your bot client id"

LIST_CATEGORIES = '```Pełna lista kategorii:\n{0}```'
HELP_TEXT = """```WorkoutBot pozwala na dodawanie treningów a następnie wylosowanie jednego.
Lista możliwych komend:
    - help - pomoc
    - categories - wyświetla pełną listę kategorii treningów
    - add {CATEGORY1}...{CATEGORYn}\\n{WORKOUT} - dodaje nowy trening o danych kategoriach
    - get - losuje dowolny trening
    - get {CATEGORY1}...{CATEGORYn} - losuje trening o dowolnej z wybranych kategorii```"""
UNKNOWN_COMMAND = '```Nieznana komenda {0}, sprawdź pomoc (help)```'
UNKNOWN_CATEGORY = '```Nieznana kategoria {0}```'
INVALID_PARAMETERS = '```Niepoprawne parametry komendy {0}.```'
ADDING_WORKOUT = '```Dodaje nowy workout do kategorii {0}```'
NO_CATEGORY_WORKOUTS = '```Nie ma żadnego workoutu w kategorii {0}```'
NO_WORKOUTS = '```Nie ma żadnego workoutu```'

WORKOUTS_FILE_NAME = 'workouts.json'

Entity = namedtuple('Entity', ['id', 'name'])
Connection = namedtuple('Connection', ['id1', 'id2'])

def wasUserMentioned(self, user):
    return user.id in [mention.id for mention in self.mentions]

def getMessageWithoutMention(self, user):
    return self.content.replace('<@{0}>'.format(user.id), '').strip()

discord.message.Message.wasUserMentioned = wasUserMentioned
discord.message.Message.getMessageWithoutMention = getMessageWithoutMention
del(wasUserMentioned)
del(getMessageWithoutMention)

class JsonDatabase():
    def getCategories(self):
        return self._loadEntities('data\\categories.json')

    def getWorkouts(self):
        return self._loadEntities('data\\workouts.json')

    def getConnections(self):
        return self._loadConnections('data\\workout_categories.json')

    def saveWorkout(self, workout, workoutCategories):
        workouts = self.getWorkouts()
        workoutId = len(workouts)
        workouts.append(Entity(workoutId, workout))
        self._save('data\\workouts.json', workouts)

        connections = self.getConnections()
        categories = self.getCategories()

        newConnections = [Connection(workoutId, category.id) for category in workoutCategories]
        self._save('data\\workout_categories.json', connections + newConnections)

    def _save(self, fileName, data):
        with open(fileName, 'w') as outfile:
            json.dump(data, outfile)

    def _loadEntities(self, fileName):
        return self._loadObjectList(fileName, Entity._make) or []

    def _loadConnections(self, fileName):
        return self._loadObjectList(fileName, Connection._make) or []

    def _loadObjectList(self, fileName, objectFactory):
        if os.path.exists(fileName) and os.path.isfile(fileName):
            with open(fileName, 'r') as infile:
                return [objectFactory(data) for data in json.load(infile)]

class WorkoutCommands():
    def __init__(self, fileName, database):
        self.database = database
        self.fileName = fileName

        self.categories = database.getCategories()

    def add(self, parameter):
        params = parameter.split('\n', 1)
        if len(params) < 2:
            return INVALID_PARAMETERS.format('add')

        categoryEntites = []
        categoryText = params[0].split()
        for category in categoryText:
            foundCategories =[cat for cat in self.categories if cat.name.lower() == category.lower()]
            if len(foundCategories) < 1:
                return UNKNOWN_CATEGORY.format(category)
            categoryEntites.append(foundCategories[0])

        workout = params[1]
        self.database.saveWorkout(workout, categoryEntites)

        return ADDING_WORKOUT.format(category)

    def get(self, parameter):
        category = parameter.lower()
        if parameter == '':
            return self.getAnyWorkout()

        categories = category.split()
        categoryIds = [cat.id for cat in self.categories if cat.name in categories]
        if len(categoryIds) < 1:
            return UNKNOWN_CATEGORY.format(category)

        workouts = self.database.getWorkouts()
        workoutIds = [connection.id1 for connection in self.database.getConnections() if connection.id2 in categoryIds]

        if len(workoutIds) > 0:
            workoutId = random.randrange(len(workoutIds))
            return '```{0}```'.format(workouts[workoutIds[workoutId]].name)

        return NO_CATEGORY_WORKOUTS.format(category)

    def listCategories(self, parameter):
        message = ''
        for category in self.categories:
            message += ' - {0}\n'.format(category.name)

        return LIST_CATEGORIES.format(message);

    def getAnyWorkout(self):
        workouts = self.database.getWorkouts()

        if len(workouts) == 0:
            return NO_WORKOUTS

        workoutId = random.randrange(len(workouts))
        return '```{0}```'.format(workouts[workoutId].name)

class CommandFactory():
    def __init__(self, fileName, database):
        workout = WorkoutCommands(fileName, database)
        self.commands = {
            'help': lambda parameter: HELP_TEXT,
            'categories': workout.listCategories,
            'add': workout.add,
            'get': workout.get
        }

    def createCommand(self, command):
        if command in self.commands:
            return self.commands[command]

        return lambda parameter: UNKNOWN_COMMAND.format(command)

class WorkoutBot(discord.Client):
    def __init__(self):
        discord.Client.__init__(self)
        self.commandFactory = CommandFactory(WORKOUTS_FILE_NAME, JsonDatabase())

    @asyncio.coroutine
    def on_ready(self):
        print('#####\n{0} is online and connected to Discord, bot id: {1}\n#####'.format(self.user.name, self.user.id))

    @asyncio.coroutine
    async def on_message(self, message):
        # do not reply to yourself
        if message.author == self.user:
            return

        if not message.wasUserMentioned(self.user):
            return

        try:
            command, parameter = self.parseMessage(message)
            commandHandler = self.commandFactory.createCommand(command)

            await message.channel.send(commandHandler(parameter))
        except:
            traceback.print_exc()
            raise

    @asyncio.coroutine
    def on_error(self, event, *args, **kwargs):
        print('Exception occurs in event {0}, with args {1} and kwargs {2}'.format(event, args, kwargs))

    def parseMessage(self, message):
        text = message.getMessageWithoutMention(self.user)
        commandParameters = text.split(' ', 1)

        command = 'help'
        parameter = ''

        if len(commandParameters) >= 1:
            command = commandParameters[0].strip().lower()
        if len(commandParameters) >= 2:
            parameter = commandParameters[1].strip()

        return command, parameter

workoutBot = WorkoutBot()
workoutBot.run(CLIENT_ID)