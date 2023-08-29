import sqlite3

db = sqlite3.connect("membership.db")

db.execute(
    """
    CREATE TABLE IF NOT EXISTS membership (
        user INT PRIMARY KEY 
    );
"""
)

def addVoterToCache(user):
    db.execute("INSERT INTO membership VALUES (?);", (user))


def removeVoterFromCache(user):
    db.execute("DELETE FROM membership WHERE user = ?;", (user))


def clearCache():
    db.execute("DELETE FROM membership;")

def loadIDs():
    voters = set()
    cursor = db.cursor()
    cursor.execute("SELECT user FROM membership;")
    row = cursor.fetchone()
    while row is not None:
        voters.add(row[1])
    return voters
