# This software is provided under MIT license, You can contact me at telegram: @antender.

# Copyright 2022 Anton "antender" Volokitin. 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import configparser
import requests
import string
import random
import json
import os
from bottle import default_app, static_file, get, post, request, abort

config = configparser.ConfigParser()
config.read('config.ini')

TOKEN = config['settings']['token'].strip(' ')
CHAT_ID = config['settings'].getint('chat_id')
ADMIN = config['settings']['admin'].strip(' ').lstrip('@')
RESTORE = config['settings'].getboolean('restore_user_ids')
BOT_NAME = config['settings']['bot_name']
ADMIN_CAN_VOTE = config['settings'].getboolean('admin_can_vote')

voting_status = "не начато"
winner_count = None
candidates = []
votes = {}
voters = set()
choosers = {}
goal = None
f = None
admin_saved_id = None

def removeSavedIds():
    try:
        os.remove('saved_ids')
    except FileNotFoundError:
        pass

if RESTORE:
    try:
        with open('saved_ids') as f:
            for line in f:
                voters.add(int(line.rstrip("\n")))
    except OSError:
        pass
    f = open('saved_ids', 'a')
else:
    removeSavedIds()

def apiCall(method, parameters):
    global TOKEN
    r = requests.post(f'https://api.telegram.org/bot{TOKEN}/{method}', timeout=3, data=parameters)
    if r.status_code == 200:
        result = r.json()
        if result['ok'] != True:
            print(f"Error: {result['description']}")
            return None
        return result['result']
    print(f"Network error:{r.text}")
    return None

def sendToGroupChat(message):
    global CHAT_ID
    apiCall('sendMessage', {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    })

def clear():
    global voting_status, winner_count, candidates, votes, choosers, theme
    voting_status = "не начато"
    winner_count = None
    candidates = []
    votes = {}
    choosers = {}
    goal = None
    sendToGroupChat("Бот сброшен в стартовое состояние. Все голоса удалены.")

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
    global winner_count, candidates
    try:
        count = int(count)
    except:
        sendToGroupChat("Кол-во должно быть числом от 1 до кол-ва кандидатов - 1")
        return
    if (count >= 1) and (count < len(candidates)):
        winner_count = count
        sendToGroupChat(f"Число победителей: {winner_count}")
        return
    sendToGroupChat("Кол-во должно быть числом от 1 до кол-ва кандидатов - 1")
    return
    

def printStats():
    global winner_count, votes, voters
    all_voters = len(voters)
    fully_voted = 0
    partially_voted = 0
    not_voted = 0
    for voter in voters:
        if voter not in votes:
            not_voted += 1
        else:
            if len(votes[voter]) == winner_count:
                fully_voted += 1
            else:
                partially_voted += 1
    sendToGroupChat("""
_Не начали голосовать_: {}/{}
_Продолжают голосовать_: {}/{}
_Закончили голосовать_: {}/{}
""".format(not_voted, all_voters, partially_voted, all_voters, fully_voted, all_voters))

def printWinners():
    global winner_count, candidates, votes
    winners = []
    for candidate in candidates:
        winners.append({'points': 0, 'votes': [0] * winner_count, 'candidate': candidate})
    fully_voted = 0
    partially_voted = 0
    for vote_key in votes:
        vote_list = votes[vote_key]
        if len(vote_list) == winner_count:
            fully_voted += 1
            vote_index = 0
            for vote in vote_list:
                winner = winners[vote]
                winner['points'] += (winner_count - vote_index) * (winner_count - vote_index)
                winner['votes'][vote_index] += 1
                vote_index += 1
        else:
            partially_voted += 1
    winners.sort(key= lambda item : item['points'], reverse = True)
    losers = winners[winner_count : len(winners)]
    winners = winners[0 : winner_count]
    text = f"_Проголосовали_: {fully_voted}\n_Недоголосовали (не учитываются)_: {partially_voted}\n*Победители*:\n"
    candidate_index = 1
    for winner in winners:
        text += f"{candidate_index}. {winner['candidate']}: {winner['points']} баллов; голоса: [{','.join(map(str, winner['votes']))}]\n"
        candidate_index += 1
    text += "_Остальные_:\n"
    for loser in losers:
        text += f"{candidate_index}. {loser['candidate']}: {loser['points']} баллов; голоса: [{','.join(map(str, loser['votes']))}]\n"
        candidate_index += 1
    sendToGroupChat(text)

def processAdminCommand(text):
    global voting_status, winner_count, candidates, goal, admin_saved_id, f, BOT_NAME
    if text == '/clear':
        clear()
        return
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
    if text.startswith('/add'):
        if voting_status != "не начато":
            sendToGroupChat("Голосование уже было начато")
            return
        addCandidate(text.removeprefix('/add').strip(' '))
        return
    if text.startswith('/remove'):
        if voting_status != "не начато":
            sendToGroupChat("Голосование уже было начато")
            return
        removeCandidate(text.removeprefix('/remove').strip(' '))
        return
    if text.startswith('/wincount'):
        if voting_status != "не начато":
            sendToGroupChat("Голосование уже было начато")
            return
        setWinnerCount(text.removeprefix('/wincount').strip(' '))
        return
    if text.startswith('/goal'):
        if voting_status != "не начато":
            sendToGroupChat("Голосование уже было начато")
            return
        setGoal(text.removeprefix('/goal').strip(' '))        
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
    #if text == '/adminvotes':
    #    if admin_saved_id is None:
    #        sendToGroupChat("Админу нужно перезайти")
    #        return
    #    voters.add(admin_saved_id)
    #    if f is not None:
    #        print(admin_saved_id, file=f, flush=True)
    #    sendToGroupChat("Админ теперь может голосовать")
    #    return
    if text == '/clearuserids':
        voters.clear()
        removeSavedIds()
    if text == '/help':
        sendToGroupChat("""
    *Команды в общем чате для админа-организатора:*

/help
    пишет подсказку

*Настройка:*
/clear 
    полностью сбрасывает состояние бота в начальное, кроме id голосующих
/status
    пишет состояние бота
/add _имя кандидата_
    добавляет претендента в список
/remove _имя кандидата_
    удаляет претендента из списка
/wincount _число_
    задаёт кол-во победителей в голосовании, 1 <= целое число < кол-во кандидатов
/goal
    задаёт цель голосования
/adminvotes
    добавляет админа в список голосующих
/clearuserids
    удаляет все id голосующих; чтобы они снова могли голосовать их придётся передобавлять в чат

*Управление процессом голосования:*
/startvoting
    начинает или продолжает голосование
/pausevoting
    приостанавливает голосование
/stopvoting
    безвозвратно останавливает голосование

/stats
    показывает статистику по голосованию на текущий момент
/winners
    подсчитывает и показывает победителей
"""
        )
        return
    #sendToGroupChat("Нераспознанная команда, напиши /help для списка доступных команд")

def sendPrivateMessage(chat_id, message):
    apiCall('sendMessage', {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    })

def buildKeyboard(user_id):
    global candidates, votes
    keyboard = []
    candidate_index = 0
    this_user_votes = votes[user_id]
    for candidate in candidates:
        if not candidate_index in this_user_votes:
            keyboard.append([{
                'text': candidate,
                'callback_data': str(candidate_index)
            }])
        candidate_index += 1
    return keyboard

def buildPreviousText(user_id, candidate_index):
    global candidates, votes, goal
    previous = f"_Цель_:\n{goal}\n"
    if candidate_index != 1:
        previous += "_Выбранные кандидаты_:\n"
        previous_index = 1
        for vote in votes[user_id]:
            previous = f"{previous}{previous_index}. {candidates[vote]}\n"
            previous_index += 1
    return previous

def sendChooser(chat_id, user_id, candidate_index):
    global winner_count, choosers
    response = apiCall('sendMessage', {
        'chat_id': chat_id,
        'text': f"{buildPreviousText(user_id, candidate_index)}_Голосуем за кандидата_ *{candidate_index}* _из_ *{winner_count}*_:_",
        'protect_content': True,
        'reply_markup': json.dumps({
            'inline_keyboard': buildKeyboard(user_id)
        }),
        'parse_mode': 'Markdown'
    })
    choosers[user_id] = (response['message_id'], chat_id)

def updateChooser(user_id):
    global winner_count, votes, choosers
    apiCall('editMessageText', {
        'chat_id': choosers[user_id][1],
        'message_id': choosers[user_id],
        'text': f"{buildPreviousText(user_id, len(votes[user_id]) + 1)}_Голосуем за кандидата_ *{len(votes[user_id]) + 1}* _из_ *{winner_count}*_:_",
        'reply_markup': json.dumps({
            'inline_keyboard': buildKeyboard(user_id)
        }),
        'parse_mode': 'Markdown'
    })

def processPrivateMessage(message, chat):
    global voting_status, votes
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
    global CHAT_ID, ADMIN, admin_saved_id, f, ADMIN_CAN_VOTE
    chat = message['chat']
    if chat['type'] == 'private':
        if message['from']['id'] not in voters:
            sendPrivateMessage(message['chat']['id'], 'Вас нет в списке голосующих')
            return
        processPrivateMessage(message, chat)
    else:
        if chat['id'] != int(CHAT_ID):
            print(chat['id'])
            apiCall('leaveChat', {
                'chat_id': chat['id']
            })
        if 'new_chat_members' in message:
            for user in message['new_chat_members']:
                if 'username' in user and user['username'].lstrip('@') == ADMIN:
                    admin_saved_id = user['id']
                if not ('username' in user and user['username'].lstrip('@') == ADMIN and (not ADMIN_CAN_VOTE) or user['is_bot']):
                    voters.add(user['id'])
                    if f is not None:
                        print(user['id'], file=f, flush=True)
            return
        if 'left_chat_member' in message:
            try:
                voters.remove(message['left_chat_member']['id'])
            except KeyError:
                pass
        if 'from' in message:
            sent_by = message['from']
            if 'text' in message and 'username' in sent_by and sent_by['username'].lstrip('@') == ADMIN:
                text = message['text']
                processAdminCommand(text)

def processCallback(callback_id, user_id, message_id, data):
    global voting_status, winner_count, candidates, votes, choosers
    if user_id not in voters:
        apiCall('answerCallbackQuery', {
            'callback_query_id': callback_id,
            'text': f"Вас нет в списке голосующих"
        })
        return
    if voting_status != 'начато':
        apiCall('answerCallbackQuery', {
            'callback_query_id': callback_id,
            'text': 'Голосование не начато'
        })
        return
    try:
        data = int(data)
    except:
        apiCall('answerCallbackQuery', {
            'callback_query_id': callback_id
        })
    if data < 0 or data > len(candidates) or data in votes[user_id] or len(votes[user_id]) >= winner_count:
        apiCall('answerCallbackQuery', {
            'callback_query_id': callback_id,
        })
        return
    votes[user_id].append(data)
    if len(votes[user_id]) == winner_count:
        apiCall('answerCallbackQuery', {
            'callback_query_id': callback_id,
            'text': f"Голос за {candidates[data]} принят"
        })
        sendPrivateMessage(choosers[user_id][1], f"{buildPreviousText(user_id, -1)}*Голосование завершено*.")
        if choosers[user_id][0] == message_id:
            apiCall('deleteMessage', {
                'chat_id': choosers[user_id][1],
                'message_id': choosers[user_id][0]
            })
            del choosers[user_id]
        return
    if choosers[user_id][0] != message_id:
        sendChooser(choosers[user_id][1], user_id, len(votes[user_id]) + 1)
    else:
        updateChooser(user_id)
    apiCall('answerCallbackQuery', {
        'callback_query_id': callback_id,
        'text': f"Голос за {candidates[data]} принят"
    })

def processUpdate(update):
    global CHAT_ID, ADMIN, voters, admin_saved_id, f, ADMIN_CAN_VOTE
    if 'message' in update:
        processMessage(update['message'])
        return
    if 'chat_join_request' in update and update['chat_join_request']['chat']['id'] == CHAT_ID:
        user = update['chat_join_request']['from']
        if 'username' in user and user['username'].lstrip('@') == ADMIN:
            admin_saved_id = user['id']
        if not ('username' in user and user['username'].lstrip('@') == ADMIN and (not ADMIN_CAN_VOTE) or user['is_bot']):
            voters.add(user['id'])
            if f is not None:
                print(user['id'], file=f, flush=True)
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

requests.post(f'https://api.telegram.org/bot{TOKEN}/setWebhook', data={
    'url': config['settings']['domain'].strip(' '),
    'max_connections': 1,
    'allowed_updates': json.dumps(['message', 'chat_join_request', 'chat_member', 'callback_query']),
    'drop_pending_updates': True,
    'secret_token': SECRET
})

@post('/')
def update():
    global SECRET
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') == SECRET:
        processUpdate(request.json)
        return 'OK'
    else:
        abort(401, "Access denied.")

@get('/source-code')
def sourceCode():
    return static_file('main.py', root='./')

application = default_app()