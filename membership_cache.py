import sqlite3

db = sqlite3.connect("membership.db")

db.execute(
    """
    CREATE TABLE IF NOT EXISTS membership (
        chat INT,
        user INT,
        PRIMARY KEY (chat, user) 
    );
"""
)

db.execute(
    """
    CREATE TABLE IF NOT EXISTS chat (
        chat INT PRIMARY KEY,
        owner_can_vote INT NOT NULL
    );
"""
)


def addVoterToCache(chat, user):
    db.execute("INSERT INTO membership VALUES (?, ?);", (chat, user))


def removeVoterFromCache(chat, user):
    db.execute("DELETE FROM membership WHERE chat = ? AND user = ?;", (chat, user))


def clearCache():
    db.execute("DELETE FROM membership;")
    db.execute("DELETE FROM chat;")


def addChat(chat):
    db.execute("INSERT INTO chat VALUES (?, 1);", (chat))


def setChatOwnerCanVote(chat, canvote):
    db.execute(
        "UPDATE chat SET owner_can_vote = ? WHERE chat = ?;",
        (chat, canvote if 1 else 0),
    )


def loadIDs():
    voters = set()
    cursor = db.cursor()
    cursor.execute("SELECT chat, user FROM membership;")
    row = cursor.fetchone()
    while row is not None:
        voters.add(row[1])
    return voters
    # votings = {}

    # cursor = db.cursor()
    # cursor.execute("SELECT chat, user FROM membership;")

    # row = cursor.fetchone()
    # while row is not None:
    # if row[0] not in votings:
    # votings[row[0]] = set()
    # votings[row[0]].add(row[1])
    # row = cursor.fetchone()
    # return votings
