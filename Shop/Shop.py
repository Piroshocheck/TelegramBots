from operator import call
import os 
import json
import time
import yookassa
import uuid
from yookassa import Configuration, Payment
from random import randint
import telebot
from telebot import types

path = os.path.dirname(__file__)
with open(os.path.join(path, 'settings.json'), 'r', encoding='utf-8-sig') as f:
    settings = json.load(f)

with open(os.path.join(path, 'ShopItems.json'), 'r', encoding='utf-8-sig') as f:    
    shopitems = json.load(f)

with open(os.path.join(path, 'customers.json'), 'r', encoding='utf-8-sig') as f:    
    customers = json.load(f)


bot = telebot.TeleBot(settings['token'])

user_states = {}  # Словарь для хранения состояний пользователей

dataname = {
"name": "Название",
"price": "Цена",
"description": "Описание",
"image": "Изображение"               
}

yookassa.Configuration.account_id = settings['shop_id']
yookassa.Configuration.secret_key = settings['secret_key']

try:
    me = bot.get_me()
    print(f"[TEST]Бот запущен: @{me.username}, ID: {me.id}")
except Exception as e:
    print(f"[TEST]Ошибка при проверке бота: {e}")
    exit(1)

welcomeKeyboard = types.InlineKeyboardMarkup()
welcomeKeyboard.add(types.InlineKeyboardButton("Товары", callback_data="products"))
welcomeKeyboard.add(types.InlineKeyboardButton("Профиль", callback_data="profile"))

subscribeKeyboard = types.InlineKeyboardMarkup()
subscribeKeyboard.add(types.InlineKeyboardButton("Подписаться", url="https://t.me/misterLogovo"))

def generate_confirm_buttons(item_id):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Подтвердить покупку", callback_data=f"confirm_payment_{item_id}"))
    keyboard.add(types.InlineKeyboardButton("Отмена", callback_data=f"select_{item_id}"))
    return keyboard

def generate_payment_button(payment_url,item_id):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Оплатить", url=payment_url))
    keyboard.add(types.InlineKeyboardButton("Отмена", callback_data="buy_" + str(item_id)))
    return keyboard

## Поиск продукта по ID
def find_product_by_id(id:int):
    for item in shopitems:
        if item['id'] == id:
            return item
    return False

def create_payment(order_id:int, value:int): 
    payment = Payment.create({
        "amount": {
            "value": str(value),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/FlaemeeBot"
        },
        "capture": True,
        "description": f"Оплата товаров по заказу №{order_id}"
    }, uuid.uuid4())
    return payment





## Админ ли пользователь
def check_permission(message):
    try:
        if bot.get_chat_member(settings['subscribecribed_channels'], message.from_user.id) in ['creator', 'administrator']:
            return True
        else:
            return False
    except Exception as e:
        print(f"Ошибка при проверке прав: {e}")
        return False


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    print(f"[TEST]Получен callback от пользователя {call.from_user.id} с данными: {call.data}")
    
    if call.data.startswith("edit_") and len(call.data.split("_")) == 2:
        print(f"[TEST]Пользователь {call.from_user.id} выбрал редактирование товара с данными: {call.data.split('_')}")
        item = find_product_by_id(int(call.data.split("_")[1]))
        if item:
            editKeyboard = types.InlineKeyboardMarkup(row_width=1)
            for key in dataname.keys():
                editKeyboard.add(types.InlineKeyboardButton(dataname[key], callback_data=f"edit_{key}_{item['id']}"))
            editKeyboard.add(types.InlineKeyboardButton("Назад", callback_data="editproduct"))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Вы редактируете товар {item['name']}",reply_markup=editKeyboard)


    if call.data == 'products':
        shopButtons = types.InlineKeyboardMarkup()
        for item in shopitems:
            print(type(item['name']))
            shopButtons.add(types.InlineKeyboardButton(item['name'] + f" ({str(item['price'])} руб.)", callback_data=f"select_{int(item['id'])}"))
        shopButtons.add(types.InlineKeyboardButton("Назад", callback_data="back_to_welcome"))
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "Выберите товар из списка ниже:", reply_markup=shopButtons)

    if call.data == 'profile':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, f"🪪Ваш ID: {call.from_user.id}\n🥸Ваше имя: {call.from_user.first_name}",reply_markup=welcomeKeyboard)

    if call.data.startswith("select_"):
        print(f"[TEST]Пользователь {call.from_user.id} выбрал товар с ID {call.data.split('_')[1]}")
        item_id = int(call.data.split("_")[1])
        for item in shopitems:
            if item['id'] == item_id:
                productKeyboard = types.InlineKeyboardMarkup()
                productKeyboard.add(types.InlineKeyboardButton("Купить", callback_data=f"buy_{item['id']}"))
                productKeyboard.add(types.InlineKeyboardButton("Назад", callback_data="products"))
                bot.edit_message_media(chat_id=call.message.chat.id, message_id=call.message.message_id, media=types.InputMediaPhoto(item['image']), reply_markup=productKeyboard)
                bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=f"{item['name']}\n\n{item['description']}\n\nЦена: {item['price']} руб.",reply_markup=productKeyboard)
                break

    if call.data.startswith("buy_"):
        item = find_product_by_id(int(call.data.split("_")[1]))
        for customer in customers:
            if customer['user_id'] == call.from_user.id and customer['status'] == 'pending':
                bot.send_message(call.message.chat.id, "У вас уже есть незавершенный заказ.")
                return
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_photo(call.message.chat.id, item['image'], caption=f"Вы точно хотите приобрести {item['name']}?", reply_markup=generate_confirm_buttons(item['id']))

    
    if call.data.startswith("confirm_payment_"):
        order_number = randint(100000, 999999)
        item_id = int(call.data.split("_")[2])
        item = find_product_by_id(item_id)
        customers.append({
            "user_id": call.from_user.id,
            "product_id": item_id,
            "status": "waiting_for_payment",
            "order_number": order_number
        })
        with open(os.path.join(path, 'customers.json'), 'w', encoding='utf-8-sig') as f:
            json.dump(customers, f, ensure_ascii=False, indent=4)
        payment = create_payment(order_id=order_number, value=item['price'])
        payMessage = bot.send_message(call.message.chat.id, f"Пожалуйста, оплатите заказ по ссылке ниже в течении 10 минут. \n Оплата проходит в течении 10-15 секунд", reply_markup=generate_payment_button(payment.confirmation.confirmation_url,item_id))
        status = yookassa.Payment.find_one(payment.id).status
        print(f"[TEST]Статус оплаты для заказа {order_number}: {status}")
        while status != 'succeeded' or status != 'canceled':
            status = yookassa.Payment.find_one(payment.id).status
            if status == 'succeeded':
                time.sleep(10)
                for customer in customers:
                    if customer['order_number'] == order_number:
                        customer['status'] = 'pending'
                        with open(os.path.join(path, 'customers.json'), 'w', encoding='utf-8-sig') as f:
                            json.dump(customers, f, ensure_ascii=False, indent=4)
                bot.send_message(call.message.chat.id, text=settings['product_purchase_message'].format(product_name=item['name']), reply_markup=welcomeKeyboard)
                bot.delete_messages(call.message.chat.id, [call.message.message_id, payMessage.message_id])
                break
            elif status == 'canceled':
                customers.remove(next(customer for customer in customers if customer['order_number'] == order_number))
                with open(os.path.join(path, 'customers.json'), 'w', encoding='utf-8-sig') as f:
                    json.dump(customers, f, ensure_ascii=False, indent=4)
                bot.send_message(call.message.chat.id, "Покупка отменена.", reply_markup=welcomeKeyboard)
                bot.delete_message(call.message.chat.id, call.message.message_id)
                break
            else:
                print(f"[TEST]Ожидание оплаты для заказа {order_number}. Текущий статус: {status}")
        
        
    if call.data == "back_to_welcome":
        start(call.message)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
    if call.data.startswith("complete_order_"):
        order_number = int(call.data.split("_")[2])
        for customer in customers:
            if customer['order_number'] == order_number:
                customer['status'] = 'completed'
                with open(os.path.join(path, 'customers.json'), 'w', encoding='utf-8-sig') as f:
                    json.dump(customers, f, ensure_ascii=False, indent=4)

                bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
                bot.send_message(chat_id=customer['user_id'], text=f"Заказ {order_number} завершён! \n По всем вопросам, касающихся заказа и/или его выполнения обращайтесь в поддержку @Flaemee \n Спасибо за покупку!💖")
                break
       
    if call.data.startswith("edit_") and len(call.data.split("_")) == 3:
        print(f"Пользователь {call.from_user.id} выбрал редактирование товара с данными: {call.data.split('_')[2]}")
        item = find_product_by_id(int(call.data.split("_")[2]))
        if item:
            key = call.data.split("_")[1]
            user_states[call.from_user.id] = {'stage': f'edit_{key}', 'item_id': item['id']}
            bot.send_message(call.message.chat.id, f"Введите новое значение для {dataname[key]} (текущее значение: {item[key]})")
    
    
def check_subscription(user_id):
    try:
        member = bot.get_chat_member(settings['subscribecribed_channels'], user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception as e:
        print(f"Ошибка при проверке подписки: {e}")
        return False

@bot.message_handler(commands=['start'])
def start(message):
    print(f"[TEST]Получена команда /start от пользователя {message.from_user.id}")
    if check_subscription(message.from_user.id):
        bot.send_message(message.chat.id, "Добро пожаловать в магазин! Вы можете просмотреть наши товары, нажав кнопку ниже.", reply_markup=welcomeKeyboard)
    else:
        bot.send_message(message.chat.id, "Для доступа к магазину вам нужно быть подписчиком.", reply_markup=subscribeKeyboard)

@bot.message_handler(commands=['newproduct'])
def new_product_create(message):
    user_id = message.from_user.id
    if message.from_user.id == bot.bot_id:
        print(f"[TEST]Игнорируем callback от самого бота")
        return
    if bot.get_chat_member(settings['subscribecribed_channels'], user_id).status not in ['creator', 'administrator']:
        bot.reply_to(message, "У вас нет прав для добавления товаров.")
        return
    user_states[user_id] = {'stage': 'name', 'new_product': {}}
    bot.send_message(message.chat.id, "Введите название нового товара")


new_product = {}

@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'))
def handle_input(message):
    user_id = message.from_user.id
    user_id = message.from_user.id
    
    message = message
    user_id = message.from_user.id
    state = user_states.get(user_id)
    print(f"[TEST]Состояние пользователя {user_id}: {state}")
    if state and state['stage'].startswith('edit_') and message.from_user.id == user_id:
        print(f"[TEST]Пользователь {user_id} находится в процессе редактирования товара с состоянием: {state}")
        key = state['stage'].split("_")[1]
        item_id = state['item_id']
        item = find_product_by_id(item_id)
        if item: 
            print(f"[TEST]Пользователь {user_id} редактирует товар с ID {item_id}, ключ {key}, новое значение: {message.text.strip()}")  
            if key == 'price':
                try:
                    item[key] = int(message.text.strip())
                except ValueError:
                    bot.reply_to(message, "Цена должна быть числом. Попробуйте снова.")
                    return
            else:
                item[key] = message.text.strip()
            with open(os.path.join(path, 'ShopItems.json'), 'w', encoding='utf-8-sig') as f:
                json.dump(shopitems, f, ensure_ascii=False, indent=4)
            bot.reply_to(message, f"{dataname[key]} товара '{item['name']}' успешно обновлено!")
            del user_states[user_id]  # Очистить состояние
            return
        else:
            print(f"[TEST]Товар с ID {item_id} не найден для редактирования пользователем {user_id}")
        return
    else:
        print(f"[TEST]Нет активного состояния редактирования для пользователя {user_id}")
        
    for customer in customers:
        if customer['user_id'] == user_id and customer['status'] == 'pending':
            confrimKeyboard = types.InlineKeyboardMarkup()
            confrimKeyboard.add(types.InlineKeyboardButton("Выдача товара завершена", callback_data=f"complete_order_{customer['order_number']}"))
            bot.send_message(chat_id=settings['work_channel'],text=str.format(settings['workers_purchase_notification'],user=f'@{message.from_user.username}',product_name=find_product_by_id(customer['product_id'])['name'],data=message.text),reply_markup=confrimKeyboard)
            bot.reply_to(message, "Спасибо за предоставленную информацию! Ваш заказ будет обработан в ближайшее время.")
            return
    if user_id not in user_states:
        return  # Игнорировать, если нет активного состояния
    
    state = user_states[user_id]
    stage = state['stage']
    
    if stage == 'name':
        new_product.clear()
        new_product['name'] = message.text.strip()
        print(new_product['name'])
        state['stage'] = 'price'
        bot.send_message(message.chat.id, "Введите цену нового товара")
        print(f"[TEST]Новое значение названия: {new_product['name']}")
    elif stage == 'price':
        try:
            new_product['price'] = int(message.text.strip())
            state['stage'] = 'description'
            bot.send_message(message.chat.id, "Введите описание нового товара")
            print(f"[TEST]Новое значение цены: {new_product['price']}")
        except ValueError:
            bot.reply_to(message, "Цена должна быть числом. Попробуйте снова.")
    elif stage == 'description':
        new_product['description'] = message.text.strip()
        state['stage'] = 'image'
        bot.send_message(message.chat.id, "Отправьте изображение товара или введите URL")
        print(new_product)
    elif stage == 'image':
        if message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
            file_url = f"https://api.telegram.org/file/bot{settings['token']}/{file_info.file_path}"
            new_product['image'] = file_url
            print(new_product)
        else:
            new_product['image'] = message.text.strip()
        
        # Добавление товара
        new_id = max(item['id'] for item in shopitems) + 1 if shopitems else 1
        print(f"[TEST]Пользователь {message.from_user.id} добавляет товар: {new_product}")
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
    if bot.get_chat_member(settings['subscribecribed_channels'], user_id).status not in ['creator', 'administrator']:
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

@bot.message_handler(commands=['orders'])
def view_orders(message):
    if message.chat.id != settings['work_channel'] or not bot.get_chat_member(settings['subscribecribed_channels'], message.from_user.id).status in ['creator', 'administrator']:
        bot.reply_to(message, "У вас нет доступа к этой команде.")
        return
    orderButtons = types.InlineKeyboardMarkup(row_width=2)
    for order in customers:
        orderButton = types.InlineKeyboardButton(f"Заказ {order['order_number']}", callback_data=f'view_order_{order["order_number"]}')
        orderButtons.add(orderButton)
    bot.send_message(message.chat.id, "Выберите заказ для просмотра:", reply_markup=orderButtons)
    

@bot.message_handler(commands=['editproduct'])
def edit_product(message):
    user_id = message.from_user.id
    if bot.get_chat_member(settings['subscribecribed_channels'], user_id).status not in ['creator', 'administrator']:
        bot.reply_to(message, "У вас нет прав для редактирования товаров.")
        return
    editButtons = types.InlineKeyboardMarkup()
    for item in shopitems:
        editButtons.add(types.InlineKeyboardButton(f"{item['name']}", callback_data=f"edit_{item['id']}"))
    bot.send_message(message.chat.id, f"Выберите товар для редактирования:", reply_markup=editButtons)
   

bot.infinity_polling(
    allowed_updates=['message', 'callback_query']
)