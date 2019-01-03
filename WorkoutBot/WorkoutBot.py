# -*- coding: utf-8 -*-
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
    - get {CATEGORY1}...{CATEGORYn} - losuje trening o dowolnej z wybranych kategorii
    - getgt {RATING} {CATEGORY1}...{CATEGORYn} - losuje trening o trudności >= zadanej i dowolnej z wybranych kategorii
    - getlt {RATING} {CATEGORY1}...{CATEGORYn} - losuje trening o trudności <= zadanej i dowolnej z wybranych kategorii
    - rate {RATING} - ocenia ostatni trening w skali od 1 (mega lekko) do 5 (najciężej ever)```"""
UNKNOWN_COMMAND = '```Nieznana komenda {0}, sprawdź pomoc (help)```'
UNKNOWN_CATEGORY = '```Nieznana kategoria {0}```'
INVALID_PARAMETERS = '```Niepoprawne parametry komendy {0}.```'
INVALID_PARAMETER = '```Niepoprawny parametr {0}.```'
ADDING_WORKOUT = '```Dodaje nowy workout do kategorii {0}```'
NO_WORKOUTS = '```Nie ma żadnego workoutu spełniającego podane kryteria```'
USER_RATED = '```Użytkownik {0} już oddał głos na ostatni workout```'
WORKOUT_RATED = '```Oceniono ostatni workout na {0}```'
WORKOUT = '\n**Ocena**: {1}\n **Kategorie**: {2}\n```{0}```'

Entity = namedtuple('Entity', ['id', 'name'])
Connection = namedtuple('Connection', ['id1', 'id2'])
Rating = namedtuple('Rating', ['workoutId', 'user', 'rating'])

def wasUserMentioned(self, user):
    return user.id in [mention.id for mention in self.mentions]

def getMessageWithoutMention(self, user):
    return self.content.replace('<@{0}>'.format(user.id), '').strip()

discord.message.Message.wasUserMentioned = wasUserMentioned
discord.message.Message.getMessageWithoutMention = getMessageWithoutMention
del(wasUserMentioned)
del(getMessageWithoutMention)

class JsonDatabase():
    CONNECTIONS = 'data\\workout_categories.json'
    CATEGORIES = 'data\\categories.json'
    RATINGS = 'data\\ratings.json'
    WORKOUTS = 'data\\workouts.json'

    def getCategories(self):
        return self._loadEntities(self.CATEGORIES)

    def getWorkouts(self):
        return self._loadEntities(self.WORKOUTS)

    def getConnections(self):
        return self._loadConnections(self.CONNECTIONS)

    def getRatings(self, workoutId):
        ratings = self._loadRatings(self.RATINGS)
        return [r for r in ratings if r.workoutId == workoutId]

    def saveWorkout(self, workout, workoutCategories):
        workouts = self.getWorkouts()
        workoutId = len(workouts)
        workouts.append(Entity(workoutId, workout))
        self._save(self.WORKOUTS, workouts)

        connections = self.getConnections()
        categories = self.getCategories()

        newConnections = [Connection(workoutId, category.id) for category in workoutCategories]
        self._save(self.CONNECTIONS, connections + newConnections)

    def saveRating(self, workoutId, user, rating):
        ratings = self._loadRatings(self.RATINGS)
        ratings.append(Rating(workoutId, user, rating))
        self._save(self.RATINGS, ratings)

    def _save(self, fileName, data):
        with open(fileName, 'w') as outfile:
            json.dump(data, outfile)

    def _loadEntities(self, fileName):
        return self._loadObjectList(fileName, Entity._make) or []

    def _loadConnections(self, fileName):
        return self._loadObjectList(fileName, Connection._make) or []

    def _loadRatings(self, fileName):
        return self._loadObjectList(fileName, Rating._make) or []

    def _loadObjectList(self, fileName, objectFactory):
        if os.path.exists(fileName) and os.path.isfile(fileName):
            with open(fileName, 'r') as infile:
                return [objectFactory(data) for data in json.load(infile)]

class WorkoutCommands():
    def __init__(self, database):
        self.database = database
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
            return self._getWorkout(lambda workout: True)

        workoutIds = self._getWorkoutIdsWithCategories(category)
        return self._getWorkout(lambda workout: workout.id in workoutIds)

    def listCategories(self, parameter):
        message = ''
        for category in self.categories:
            message += ' - {0}\n'.format(category.name)

        return LIST_CATEGORIES.format(message);

    def getWithRating(self, parameter, ratingPred):
        params = parameter.split(' ', 1)
        rating = self._parseRating(params[0])
        if (rating < 1 or rating > 5):
            return INVALID_PARAMETER.format('rate')
        
        if len(params) <= 1:
            return self._getWorkout(lambda workout: ratingPred(self.getOverallRating(workout.id), rating))
        
        workoutIds = self._getWorkoutIdsWithCategories(params[1])
        return self._getWorkout(lambda workout: workout.id in workoutIds and ratingPred(self.getOverallRating(workout.id), rating))

    def rate(self, parameter, user):
        rating = self._parseRating(parameter)
        if (rating < 1 or rating > 5):
            return INVALID_PARAMETERS.format('rate')

        workouts = self.database.getWorkouts()
        if len(workouts) == 0:
            return NO_WORKOUTS

        ratings = self.database.getRatings(workouts[-1].id)
        if next((r for r in ratings if r.user == user), None) != None:
            return USER_RATED.format(user)

        self.database.saveRating(workouts[-1].id, user, rating)
        return WORKOUT_RATED.format(rating)

    def getOverallRating(self, workoutId):
        ratings = self.database.getRatings(workoutId)
        if len(ratings) < 1:
            return 0.0
        
        return sum([r.rating for r in ratings]) / len(ratings)

    def getWorkoutCategories(self, workoutId):
        categoryIds = [c.id2 for c in self.database.getConnections() if c.id1 == workoutId]
        categories = [c.name for c in self.database.getCategories() if c.id in categoryIds]
        return ', '.join(categories)

    def _getWorkoutIdsWithCategories(self, category):
        categories = category.split()
        categoryIds = [cat.id for cat in self.categories if cat.name in categories]
        if len(categoryIds) < 1:
            return []

        return [connection.id1 for connection in self.database.getConnections() if connection.id2 in categoryIds]

    def _parseRating(self, parameter):
        try:
            return int(parameter)
        except ValueError:
            return 0

    def _getWorkout(self, predicate):
        workouts = [w for w in self.database.getWorkouts() if predicate(w)]
        if len(workouts) == 0:
            return NO_WORKOUTS

        workout = workouts[random.randrange(len(workouts))]
        rating = self.getOverallRating(workout.id)
        categories = self.getWorkoutCategories(workout.id)
        return WORKOUT.format(workout.name, rating, categories)

class CommandFactory():
    def __init__(self, database):
        workout = WorkoutCommands(database)
        self.commands = {
            'help': lambda parameter, user: HELP_TEXT,
            'categories': lambda parameter, user: workout.listCategories(parameter),
            'add': lambda parameter, user: workout.add(parameter),
            'get': lambda parameter, user: workout.get(parameter),
            'getgt': lambda parameter, user: workout.getWithRating(parameter, lambda r, x: r >= x),
            'getlt': lambda parameter, user: workout.getWithRating(parameter, lambda r, x: r <= x and r > 0),
            'rate': workout.rate
        }

    def createCommand(self, command):
        if command in self.commands:
            return self.commands[command]

        return lambda parameter: UNKNOWN_COMMAND.format(command)

class WorkoutBot(discord.Client):
    def __init__(self):
        discord.Client.__init__(self)
        self.commandFactory = CommandFactory(JsonDatabase())

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

            await message.channel.send(commandHandler(parameter, message.author.name))
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