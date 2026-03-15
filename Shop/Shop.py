import os
import json
import telebot
from telebot import types

path = os.path.dirname(__file__)
with open(os.path.join(path, 'settings.json'), 'r', encoding='utf-8-sig') as f:
    settings = json.load(f)

with open(os.path.join(path, 'ShopItems.json'), 'r', encoding='utf-8-sig') as f:    
    shopitems = json.load(f)

bot = telebot.TeleBot(settings['token'])

user_states = {}  # Словарь для хранения состояний пользователей

try:
    me = bot.get_me()
    print(f"Бот запущен: @{me.username}, ID: {me.id}")
except Exception as e:
    print(f"Ошибка при проверке бота: {e}")
    exit(1)

welcomeKeyboard = types.InlineKeyboardMarkup()
welcomeKeyboard.add(types.InlineKeyboardButton("Товары", callback_data="products"))
welcomeKeyboard.add(types.InlineKeyboardButton("Профиль", callback_data="profile"))

subscribeKeyboard = types.InlineKeyboardMarkup()
subscribeKeyboard.add(types.InlineKeyboardButton("Подписаться", url="https://t.me/misterLogovo"))




@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    print(f"Получен callback от пользователя {call.from_user.id} с данными: {call.data}")
    if call.data == 'products':
        shopButtons = types.InlineKeyboardMarkup()
        for item in shopitems:
            shopButtons.add(types.InlineKeyboardButton(item['name'] + f" ({item['price']} руб.)", callback_data=f"buy_{item['id']}"))
        shopButtons.add(types.InlineKeyboardButton("Назад", callback_data="back_to_welcome"))
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "Выберите товар из списка ниже:", reply_markup=shopButtons)

    if call.data == 'profile':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, f"🪪Ваш ID: {call.from_user.id}\n🥸Ваше имя: {call.from_user.first_name}",reply_markup=welcomeKeyboard)

    if call.data.startswith("buy_"):
        print(f"Пользователь {call.from_user.id} выбрал товар с ID {call.data.split('_')[1]}")
        item_id = int(call.data.split("_")[1])
        for item in shopitems:
            if item['id'] == item_id:
                productKeyboard = types.InlineKeyboardMarkup()
                productKeyboard.add(types.InlineKeyboardButton("Купить", callback_data=f"confirm_buy_{item['id']}"))
                productKeyboard.add(types.InlineKeyboardButton("Назад", callback_data="products"))
                bot.edit_message_caption(f'**{item["name"]}** \n {item["description"]} \n **Цена:** {item["price"]} руб.', call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=productKeyboard)
                break

    if call.data.startswith("confirm_buy_"):
        item_id = int(call.data.split("_")[2])
        for item in shopitems:
            if item['id'] == item_id:
                # Здесь логика покупки, например, отправка сообщения о покупке
                bot.send_message(call.message.chat.id, f"Вы купили {item['name']} за {item['price']} руб.")
                break


    if call.data == "back_to_welcome":
        start(call.message)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        

       


def check_subscription(user_id):
    try:
        member = bot.get_chat_member(-1002389669978, user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception as e:
        print(f"Ошибка при проверке подписки: {e}")
        return False

@bot.message_handler(commands=['start'])
def start(message):
    print(f"Получена команда /start от пользователя {message.from_user.id}")
    if check_subscription(message.from_user.id):
        bot.send_message(message.chat.id, "Добро пожаловать в магазин! Вы можете просмотреть наши товары, нажав кнопку ниже.", reply_markup=welcomeKeyboard)
    else:
        bot.send_message(message.chat.id, "Для доступа к магазину вам нужно быть подписчиком.", reply_markup=subscribeKeyboard)

@bot.message_handler(commands=['newproduct'])
def new_product_create(message):
    user_id = message.from_user.id
    if bot.get_chat_member(-1002389669978, user_id).status not in ['creator', 'administrator']:
        bot.reply_to(message, "У вас нет прав для добавления товаров.")
        return
    user_states[user_id] = {'stage': 'name', 'new_product': {}}
    bot.send_message(message.chat.id, "Введите название нового товара")

@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'))
def handle_new_product_steps(message):
    user_id = message.from_user.id
    if user_id not in user_states:
        return  # Игнорировать, если нет активного состояния
    
    state = user_states[user_id]
    stage = state['stage']
    new_product = {}
    
    if stage == 'name':
        new_product['name'] = message.text.strip()
        state['stage'] = 'price'
        bot.send_message(message.chat.id, "Введите цену нового товара")
    elif stage == 'price':
        try:
            new_product['price'] = int(message.text.strip())
            state['stage'] = 'description'
            bot.send_message(message.chat.id, "Введите описание нового товара")
        except ValueError:
            bot.reply_to(message, "Цена должна быть числом. Попробуйте снова.")
    elif stage == 'description':
        new_product['description'] = message.text.strip()
        state['stage'] = 'image'
        bot.send_message(message.chat.id, "Отправьте изображение товара или введите URL")
    elif stage == 'image':
        if message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
            file_url = f"https://api.telegram.org/file/bot{settings['token']}/{file_info.file_path}"
            new_product['image'] = file_url
        else:
            new_product['image'] = message.text.strip()
        
        # Добавление товара
        new_id = max(item['id'] for item in shopitems) + 1 if shopitems else 1
        new_item = {
            'id': new_id,
            'name': new_product['name'],
            'price': new_product['price'],
            'description': new_product['description'],
            'image': new_product['image']
        }
        shopitems.append(new_item)
        with open(os.path.join(path, 'ShopItems.json'), 'w', encoding='utf-8-sig') as f:
            json.dump(shopitems, f, ensure_ascii=False, indent=4)
        bot.reply_to(message, f"Товар '{new_item['name']}' успешно добавлен!")
        del user_states[user_id]  # Очистить состояние
    elif stage == 'remove':
        try:
            product_id = int(message.text.strip())
        except ValueError:
            bot.reply_to(message, "ID товара должно быть числом. Попробуйте снова.")
            return
        item_to_remove = next((item for item in shopitems if item['id'] == product_id), None)
        print(f"Пользователь {message.from_user.id} пытается удалить товар с ID {product_id}")
        if item_to_remove:
            print(f"Пользователь {message.from_user.id} удаляет товар с ID {product_id}")
            shopitems.remove(item_to_remove)
            with open(os.path.join(path, 'ShopItems.json'), 'w', encoding='utf-8-sig') as f:
                json.dump(shopitems, f, ensure_ascii=False, indent=4)
            bot.reply_to(message, f"Товар с ID {product_id} успешно удалён!")
        else:
            bot.reply_to(message, f"Товар с ID {product_id} не найден.")
        del user_states[user_id]  # Очистить состояние


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    if user_id in user_states and user_states[user_id]['stage'] == 'image':
        file_info = bot.get_file(message.photo[-1].file_id)
        file_url = f"https://api.telegram.org/file/bot{settings['token']}/{file_info.file_path}"
        new_product = user_states[user_id]['new_product']
        new_product['image'] = file_url
        
        # Добавление товара
        new_id = max(item['id'] for item in shopitems) + 1 if shopitems else 1
        new_item = {
            'id': new_id,
            'name': new_product['name'],
            'price': new_product['price'],
            'description': new_product['description'],
            'image': new_product['image']
        }
        shopitems.append(new_item)
        with open(os.path.join(path, 'ShopItems.json'), 'w', encoding='utf-8-sig') as f:
            json.dump(shopitems, f, ensure_ascii=False, indent=4)
        bot.reply_to(message, f"Товар '{new_item['name']}' успешно добавлен!")
        del user_states[user_id]  # Очистить состояние
   

@bot.message_handler(commands=['removeproduct'])
def remove_product(message):
    user_id = message.from_user.id
    if bot.get_chat_member(-1002389669978, user_id).status not in ['creator', 'administrator']:
        bot.reply_to(message, "У вас нет прав для удаления товаров.")
        return
    user_states[user_id] = {'stage': 'remove'}
    bot.send_message(message.chat.id, "Введите ID товара, который хотите удалить")
    @bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'))
    def handle_remove_product(message):
        for item in shopitems:
            if item['id'] == int(message.text.strip()):
                shopitems.remove(item)
                with open(os.path.join(path, 'ShopItems.json'), 'w', encoding='utf-8-sig') as f:
                    json.dump(shopitems, f, ensure_ascii=False, indent=4)
                bot.reply_to(message, f"Товар с ID {item['id']} успешно удалён!")
                del user_states[message.from_user.id]  # Очистить состояние
                return
    

bot.infinity_polling(
    allowed_updates=['message', 'callback_query']
)