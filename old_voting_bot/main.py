# This software is provided under MIT license, You can contact me at telegram: @antender.

# Copyright 2022 Anton "antender" Volokitin.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import configparser
import requests
from requests.adapters import HTTPAdapter
import string
import random
import json
import os
from bottle import default_app, static_file, get, post, request, abort

requests_ses = requests.Session()
requests_ses.mount('https://api.telegram.org', HTTPAdapter(max_retries=5))

config = configparser.ConfigParser()
config.read('config.ini')

TOKEN = config['settings']['token'].strip(' ')
CHAT_ID = config['settings'].getint('chat_id')
ADMIN = config['settings']['admin'].strip(' ').lstrip('@')
RESTORE = config['settings'].getboolean('restore_user_ids')
BOT_NAME = config['settings']['bot_name']
ADMIN_CAN_VOTE = config['settings'].getboolean('admin_can_vote')

with open('help.md') as f:
    HELP = f.read()

def clear():
    global voting_status, winner_count, candidates, votes, choosers, goal, confirmed
    voting_status = "не начато"
    winner_count = None
    candidates = []
    votes = {}
    choosers = {}
    goal = None
    confirmed = set()

voters = set()
clear()

def removeSavedIds():
    try:
        os.remove('saved_ids')
    except FileNotFoundError:
        pass

if RESTORE:
    try:
        with open('saved_ids') as f:
            for line in f:
                command = line.split()
                if command[0] == 'add' or command[0] == 'addadmin' and ADMIN_CAN_VOTE:
                    voters.add(int(command[1]))
                elif command[0] == 'remove':
                    try:
                        voters.remove(int(command[1]))
                    except KeyError:
                        pass
    except OSError:
        pass
else:
    removeSavedIds()

def apiCall(method, parameters):
    r = requests_ses.post(f'https://api.telegram.org/bot{TOKEN}/{method}', timeout=3, data=parameters)
    if r.status_code == 200:
        result = r.json()
        if result['ok'] != True:
            print(f"Error: {result['description']}")
            return None
        return result['result']
    print(f"Network error:{r.text}")
    return None

def addVoter(user):
    global voters
    if not (user['is_bot']):
        is_admin = 'username' in user and user['username'].lstrip('@') == ADMIN
        if not is_admin or is_admin and ADMIN_CAN_VOTE:
            voters.add(user['id'])
        if RESTORE:
            with open('saved_ids', 'a') as f:
                if is_admin:
                    print(f"addadmin {user['id']}", file=f)
                else:
                    print(f"add {user['id']}", file=f)
                f.flush()

def sendToGroupChat(message):
    apiCall('sendMessage', {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    })

def addCandidate(name):
    global candidates
    if name == "":
        sendToGroupChat("Имя не задано")
        return
    if name not in candidates:
        candidates.append(name)
    sendToGroupChat("Кандидат теперь в списке")

def removeCandidate(name):
    global candidates
    if name == "":
        sendToGroupChat("Имя не задано")
        return
    try:
        candidates.remove(name)
    except ValueError:
        pass
    sendToGroupChat("Кандидата теперь нет в списке")

def setGoal(text):
    global goal
    if text == "":
        sendToGroupChat("Укажите цель голосования")
        return
    goal = text
    sendToGroupChat("Цель задана")

def setWinnerCount(count):
    global winner_count
    try:
        count = int(count)
    except:
        sendToGroupChat("Кол-во должно быть числом от 1 до кол-ва кандидатов - 1")
        return
    if (count >= 1) and (count <= len(candidates)):
        winner_count = count
        sendToGroupChat(f"Число победителей: {winner_count}")
        return
    sendToGroupChat("Кол-во должно быть числом от 1 до кол-ва кандидатов - 1")
    return


def printStats():
    all_voters = len(voters)
    fully_voted = 0
    partially_voted = 0
    not_voted = 0
    for voter in voters:
        if voter not in votes:
            not_voted += 1
        else:
            if voter in confirmed:
                fully_voted += 1
            else:
                partially_voted += 1
    sendToGroupChat("""
_Не начали голосовать_: {}/{}
_Продолжают голосовать_: {}/{}
_Закончили голосовать_: {}/{}
""".format(not_voted, all_voters, partially_voted, all_voters, fully_voted, all_voters))

def printWinners():
    winners = []
    for candidate in candidates:
        winners.append({'votes': 0, 'candidate': candidate})
    fully_voted = 0
    partially_voted = 0
    for vote_key in votes:
        if vote_key in confirmed:
            vote_list = votes[vote_key]
            fully_voted += 1
            vote_index = 0
            for vote in vote_list:
                winners[vote]['votes'] += 1
                vote_index += 1
        else:
            partially_voted += 1
    winners.sort(key= lambda item : item['votes'], reverse = True)
    if winners[winner_count - 1]['votes'] == winners[winner_count]['votes']:
        tied_start = 0
        tied_target = winners[winner_count]['votes']
        while winners[tied_start]['votes'] != tied_target:
            tied_start += 1
        tied_end = tied_start
        while tied_end < len(winners) and winners[tied_end]['votes'] == tied_target:
            tied_end += 1
        tied = winners[tied_start : tied_end]
        losers = winners[tied_end : len(winners)]
        winners = winners[0 : tied_start]
    else:
        tied = None
        losers = winners[winner_count : len(winners)]
        winners = winners[0 : winner_count]
    text = f"_Проголосовали_: {fully_voted}\n_Недоголосовали (не учитываются)_: {partially_voted}\n*Победители*:\n"
    candidate_index = 1
    for winner in winners:
        text += f"{candidate_index}. {winner['candidate']}: {winner['votes']} голосов\n"
        candidate_index += 1
    if tied is not None:
        text += "*Одинаково голосов*:\n"
        for tie in tied:
            text += f"{candidate_index}. {tie['candidate']}: {tie['votes']} голосов\n"
            candidate_index += 1
    text += "_Остальные_:\n"
    for loser in losers:
        text += f"{candidate_index}. {loser['candidate']}: {loser['votes']} голосов\n"
        candidate_index += 1
    sendToGroupChat(text)

def processAdminCommand(text):
    global voting_status
    if text == '/clear':
        clear()
        sendToGroupChat("Бот сброшен в стартовое состояние. Все голоса удалены.")
        return
    if text.startswith('/add'):
        if voting_status != "не начато":
            sendToGroupChat("Голосование уже было начато")
            return
        addCandidate(text.removeprefix('/add').removeprefix(f"@{BOT_NAME}").strip(' '))
        return
    if text.startswith('/remove'):
        if voting_status != "не начато":
            sendToGroupChat("Голосование уже было начато")
            return
        removeCandidate(text.removeprefix('/remove').removeprefix(f"@{BOT_NAME}").strip(' '))
        return
    if text.startswith('/wincount'):
        if voting_status != "не начато":
            sendToGroupChat("Голосование уже было начато")
            return
        setWinnerCount(text.removeprefix('/wincount').removeprefix(f"@{BOT_NAME}").strip(' '))
        return
    if text.startswith('/goal'):
        if voting_status != "не начато":
            sendToGroupChat("Голосование уже было начато")
            return
        setGoal(text.removeprefix('/goal').removeprefix(f"@{BOT_NAME}").strip(' '))
        return
    if text.startswith('/startvoting'):
        if voting_status == 'приостановлено':
            voting_status = 'начато'
            sendToGroupChat("Голосование продолжено")
            return
        if voting_status != "не начато":
            sendToGroupChat("Голосование уже было начато")
            return
        if goal is None:
            sendToGroupChat("Добавьте цель голосования")
            return
        if len(candidates) == 0:
            sendToGroupChat("Добавьте кандидатов")
            return
        if winner_count is None:
            sendToGroupChat("Укажите кол-во победителей")
            return
        if len(voters) == 0:
            sendToGroupChat("Передобавьте голосующих в чат")
            return
        voting_status = "начато"
        sendToGroupChat(f"Голосование начато. Откройте ссылку: [проголосовать](https://telegram.me/{BOT_NAME}?/start=start) или напишите */start* боту *{BOT_NAME}* в личку.")
        return
    if text.startswith('/pausevoting'):
        if voting_status != "начато":
            sendToGroupChat("Голосование должно было начато")
            return
        voting_status = "приостановлено"
        sendToGroupChat("Голосование приостановлено")
        return
    if text.startswith('/stopvoting'):
        if voting_status != "начато":
            sendToGroupChat("Голосование должно было начато")
            return
        voting_status = "остановлено"
        sendToGroupChat("Голосование остановлено")
        return
    if text == '/stats':
        if voting_status == "не начато":
            sendToGroupChat("Голосование должно было начато")
            return
        printStats()
        return
    if text == '/winners':
        if voting_status == "не начато":
            sendToGroupChat("Голосование должно было начато")
            return
        printWinners()
        return
    if text == '/clearuserids':
        voters.clear()
        removeSavedIds()
    if text == '/status':
        sendToGroupChat("""
_Голосование_: {}
_Кол-во возможных победителей_: {}
_Голосующих_: {}
_Цель голосования_:
{}
_Кандидаты_:
{}
""".format(voting_status, '*не задано*' if winner_count is None else winner_count, len(voters), '*не задана*' if goal is None else goal, "\n".join(candidates)))
        return
    if text == '/help':
        sendToGroupChat()
        return

def sendPrivateMessage(chat_id, message):
    apiCall('sendMessage', {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    })

def buildKeyboard(user_id):
    keyboard = []
    this_user_votes = votes[user_id]
    if user_id not in confirmed:
        if len(this_user_votes) != winner_count:
            candidate_index = 0
            for candidate in candidates:
                if not candidate_index in this_user_votes:
                    keyboard.append([{
                        'text': candidate,
                        'callback_data': str(candidate_index)
                    }])
                candidate_index += 1
        keyboard.append([{
            'text': 'Подтвердить голоса',
            'callback_data': 'confirm'
        }])
        if len(this_user_votes) > 0:
            keyboard.append([{
                'text': 'Отменить предыдущий выбор',
                'callback_data': 'undo'
            }])
    if len(this_user_votes) > 0 or user_id in confirmed:
        keyboard.append([{
            'text': 'Начать с начала',
            'callback_data': 'restart'
        }])
    return keyboard

def buildPreviousText(user_id, candidate_index):
    previous = f"_Цель_:\n{goal}\n"
    if candidate_index != 1:
        previous += "_Выбранные кандидаты_:\n"
        previous_index = 1
        for vote in votes[user_id]:
            previous = f"{previous}{previous_index}. {candidates[vote]}\n"
            previous_index += 1
    if user_id in confirmed:
        previous = f"{previous}*Голосование завершено*"
    elif len(votes[user_id]) == winner_count:
        previous = f"{previous}*Подтвердите свои голоса*"
    else:
        previous = f"{previous}_Голосуем за кандидата_ *{candidate_index}* _из_ *{winner_count}*_:_"
    return previous

def sendChooser(chat_id, user_id, candidate_index):
    global choosers
    response = apiCall('sendMessage', {
        'chat_id': chat_id,
        'text': f"{buildPreviousText(user_id, candidate_index)}",
        'protect_content': True,
        'reply_markup': json.dumps({
            'inline_keyboard': buildKeyboard(user_id)
        }),
        'parse_mode': 'Markdown'
    })
    choosers[user_id] = (response['message_id'], chat_id)

def updateChooser(user_id):
    apiCall('editMessageText', {
        'chat_id': choosers[user_id][1],
        'message_id': choosers[user_id],
        'text': f"{buildPreviousText(user_id, len(votes[user_id]) + 1)}",
        'reply_markup': json.dumps({
            'inline_keyboard': buildKeyboard(user_id)
        }),
        'parse_mode': 'Markdown'
    })

def processPrivateMessage(message, chat):
    global votes
    if 'text' in message and message['text'] == '/start':
        if voting_status == 'не начато':
            sendPrivateMessage(chat['id'], '*Голосование пока не начато*')
        elif voting_status == 'приостановлено':
            sendPrivateMessage(chat['id'], '*Голосование поставлено на паузу*')
        elif voting_status == 'остановлено':
            sendPrivateMessage(chat['id'], '*Голосование остановлено*')
        elif voting_status == 'начато':
            user_id = message['from']['id']
            if user_id in votes:
                sendPrivateMessage(chat['id'], '*Начинаем заново ...*')
            else:
                sendPrivateMessage(chat['id'], '*Начинаем голосовать ...*')
            votes[user_id] = []
            try:
                confirmed.remove(user_id)
            except KeyError:
                pass
            if user_id in choosers:
                apiCall('deleteMessage', {
                    'chat_id': choosers[user_id][1],
                    'message_id': choosers[user_id][0]
                })
                del choosers[user_id]
            sendChooser(chat['id'], user_id, 1)
    else:
        sendPrivateMessage(chat['id'], 'Напишите /start чтобы начать голосовать или переголосовать')

def processMessage(message):
    global CHAT_ID
    chat = message['chat']
    if chat['type'] == 'private':
        if message['from']['id'] not in voters:
            sendPrivateMessage(message['chat']['id'], 'Вас нет в списке голосующих')
            return
        processPrivateMessage(message, chat)
    else:
        if chat['id'] != int(CHAT_ID):
            print(f"Wrong chat id: {chat['id']}")
            apiCall('leaveChat', {
                'chat_id': chat['id']
            })
            return
        if 'migrate_to_chat_id' in message:
            CHAT_ID = message['migrate_to_chat_id']
            config = configparser.ConfigParser()
            config.read('config.ini')
            config['settings']['chat_id'] = str(CHAT_ID)
            with open('config.ini', 'w') as configfile:
                config.write(configfile)
            return
        if 'new_chat_members' in message:
            for user in message['new_chat_members']:
                addVoter(user)
            return
        if 'left_chat_member' in message:
            try:
                voters.remove(message['left_chat_member']['id'])
            except KeyError:
                pass
            with open('saved_ids', 'a') as f:
                for voter in voters:
                    print(f"remove {voter}", file=f)
                f.flush()
            return
        if 'from' in message:
            sent_by = message['from']
            if 'text' in message and 'username' in sent_by and sent_by['username'].lstrip('@') == ADMIN:
                text = message['text']
                processAdminCommand(text)
            return

def processCallback(callback_id, user_id, message_id, data):
    def answer(text):
        nonlocal callback_id
        answerJson = { 'callback_query_id': callback_id }
        if text is not None:
            answerJson['text'] = text
        apiCall('answerCallbackQuery', answerJson)
    def setChooser():
        if choosers[user_id][0] != message_id:
            sendChooser(choosers[user_id][1], user_id, len(votes[user_id]) + 1)
        else:
            updateChooser(user_id)
    if user_id not in voters:
        answer("Вас нет в списке голосующих")
        return
    if voting_status != 'начато':
        answer('Голосование не начато')
        return
    if data == 'undo':
        try:
            votes[user_id].pop()
        except IndexError:
            pass
        try:
            confirmed.remove(user_id)
        except KeyError:
            pass
        answer("Предыдущий выбор отменён")
        setChooser()
        return
    if data == 'restart':
        votes[user_id] = []
        try:
            confirmed.remove(user_id)
        except KeyError:
            pass
        answer("Начинаем заново")
        setChooser()
        return
    if data == 'confirm':
        confirmed.add(user_id)
        setChooser()
        answer('Голоса подтверждены')
        return
    try:
        data = int(data)
    except:
        answer(None)
        return
    if data < 0 or data > len(candidates) or data in votes[user_id] or len(votes[user_id]) >= winner_count:
        answer(None)
        return
    if user_id not in confirmed:
        votes[user_id].append(data)
    setChooser()
    answer(f"Голос за {candidates[data]} принят")

def processUpdate(update):
    if 'message' in update:
        processMessage(update['message'])
        return
    if 'chat_join_request' in update and update['chat_join_request']['chat']['id'] == CHAT_ID:
        user = update['chat_join_request']['from']
        addVoter(user)
        apiCall('approveChatJoinRequest', {
            'chat_id': CHAT_ID,
            'user_id': user['id']
        })
        return
    if 'callback_query' in update:
        callback_query = update['callback_query']
        message_id = callback_query['message']['message_id'] if 'message' in callback_query else None
        processCallback(callback_query['id'], callback_query['from']['id'], message_id, callback_query['data'])
        return

SECRET = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(32))

try:
    requests_ses.post(f'https://api.telegram.org/bot{TOKEN}/setWebhook', timeout=10, data={
        'url': config['settings']['domain'].strip(' '),
        'max_connections': 1,
        'allowed_updates': json.dumps(['message', 'chat_join_request', 'chat_member', 'callback_query']),
        'drop_pending_updates': True,
        'secret_token': SECRET
    })
    print('Webhook is set!')
except:
    print('Failed to setup webhook')
    exit(1)

@post('/')
def update():
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') == SECRET:
        processUpdate(request.json)
        return 'OK'
    else:
        abort(401, "Access denied.")

@get('/source-code')
def sourceCode():
    return static_file('main.py', root='./')

application = default_app()