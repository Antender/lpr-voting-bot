Телеграм бот для голосований

Голоса тех кто не проголосовал полностью (т.е. не подтвердил) не учитываются

## Как установить

```
python -m pip install requests bottle
```

## Как запустить
Создать бота через BotFather, он должен иметь право добавлять людей
Создать группу (ботоадмином)
Превратить группу в супергруппу (добавить, например, админа), у группы изменится id
Прописать id в config.ini
Запустить бота (main.py) через WSGI
Добавить в группу бота, если id неправильный, то он сразу выйдет
Добавить голосующих