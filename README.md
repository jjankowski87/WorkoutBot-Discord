# WorkoutBot-Discord

Bot for Discord communicator which provides functionality to choose random training for today :) List of trainings can be freely categorized. Bot can be executed from discord by mentioning it's name and then adding command.
Commands:
* @WorkoutBot help - writes help text with list of all commands.
* @WorkoutBot categories - lists categories (stored in data\categories.json file).
* @WorkoutBot add {category1} [{category n}] NEW_LINE {workout} - adds new workout to database with given categories.
* @WorkoutBot get - returns random training with any category.
@ @WorkooutBot get {category1} [{category n}] - returns random training with any of given category.