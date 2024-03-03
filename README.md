# Телеграм бот для отправки уведомлений о проверенном домашней работы с API

### Используемые технологии:
- `Python 3.10`
- `python-telegram-bot 13.7`
- `requests 2.26.0`


## Подготовка
##### Клонировать репозиторий и перейти в него в командной строке:

```
git clone https://github.com/antonata-c/homework_bot.git
```

```
cd homework_bot
```

##### Cоздать и активировать виртуальное окружение:
* Если у вас Linux/macOS
  ```
  python3 -m venv venv
  source venv/bin/activate
  ```
* Если у вас windows
  ```
  python -m venv venv
  source venv/Scripts/activate
  ```

##### Установить зависимости из файла requirements.txt:

```
python3 -m pip install --upgrade pip
```
```
pip install -r requirements.txt
```

##### Создайте файл .env, содержащий переменные окружения, пример представлен в файле `.env.example`

## Развертывание и запуск
##### Примените миграции:
```
alembic upgrade head
```
##### Запустите проект
```
python homework.py
```
#### Проект готов к использованию!
***
### Автор работы:
**[Антон Земцов](https://github.com/antonata-c)**
