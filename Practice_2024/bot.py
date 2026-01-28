import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup # type: ignore
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes # type: ignore
import requests
import psycopg2
import os

# Set up logging
logging.basicConfig(level=logging.INFO)

API_TOKEN = '7169093777:AAGIg5jjGN8fV7HLBbmUj_mBxgKkNTiplLA'

# Database connection
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')

conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    host=DB_HOST,
    port=DB_PORT
)
cursor = conn.cursor()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Название", callback_data='title'),
            InlineKeyboardButton("Зарплата", callback_data='salary'),
            InlineKeyboardButton("Стаж", callback_data='experience')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите параметр поиска:', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'title':
        keyboard = [
            [
                InlineKeyboardButton("Разработчик", callback_data='developer'),
                InlineKeyboardButton("Тестировщик", callback_data='tester'),
                InlineKeyboardButton("Аналитик", callback_data='analyst')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Выберите профессию:", reply_markup=reply_markup)
    elif query.data == 'salary':
        await query.edit_message_text(text="Введите минимальную зарплату:")
        context.user_data['next'] = 'salary_input'
    elif query.data == 'experience':
        keyboard = [
            [
                InlineKeyboardButton("Без опыта", callback_data='no_experience'),
                InlineKeyboardButton("Год и больше", callback_data='one_year'),
                InlineKeyboardButton("Много опыта", callback_data='many_years')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text='Выберите стаж:', reply_markup=reply_markup)
    elif query.data in ['developer', 'tester', 'analyst', 'no_experience', 'one_year', 'many_years']:
        context.user_data[query.data] = query.data
        await query.edit_message_text(text=f"Вы выбрали: {query.data}")
        await search_vacancies(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('next') == 'salary_input':
        min_salary = update.message.text
        context.user_data['salary'] = min_salary
        del context.user_data['next']
        await update.message.reply_text(f"Вы выбрали минимальную зарплату: {min_salary}")
        await search_vacancies(update, context)

async def search_vacancies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = context.user_data.get('title')
    salary = context.user_data.get('salary')
    experience = context.user_data.get('experience')
    
    # Example URL for API request
    url = 'https://api.hh.ru/vacancies'
    params = {
        'text': title if title else '',
        'salary': salary if salary else '',
        'experience': experience if experience else '',
        'area': '1',  # Russia
        'per_page': '20'
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        vacancies = response.json().get('items', [])
        for vacancy in vacancies:
            # Insert vacancy data into database
            cursor.execute(
                '''
                INSERT INTO vacancies (vacancy_id, title, company, salary, experience, city, description, schedule)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (vacancy_id) DO NOTHING
                ''',
                (vacancy['id'], vacancy['name'], vacancy['employer']['name'], vacancy.get('salary', {}).get('from'), vacancy['experience']['name'], vacancy['area']['name'], vacancy['snippet']['requirement'], vacancy['schedule']['name'])
            )
        conn.commit()
        
        # Send vacancies to user
        if vacancies:
            message = "\n\n".join([f"{v['name']} at {v['employer']['name']}, {v['area']['name']}\nSalary: {v['salary']['from'] if v['salary'] else 'Not specified'}" for v in vacancies[:20]])
            await update.message.reply_text(message)
        else:
            await update.message.reply_text('По вашему запросу вакансии не найдены.')
    else:
        await update.message.reply_text('Ошибка при получении данных с hh.ru')

app = ApplicationBuilder().token(API_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == '__main__':
    app.run_polling()
