import os
import telebot
import requests
import json
from datetime import datetime

# Load API keys from Replit secrets
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "google/gemma-2-9b-it"

if not TELEGRAM_TOKEN or not OPENROUTER_API_KEY:
    raise Exception("❌ Missing API keys. Set them in Replit 'Secrets' section.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Memory storage for conversations
user_memory = {}

def save_to_memory(user_id, message, response):
    if user_id not in user_memory:
        user_memory[user_id] = []

    user_memory[user_id].append({
        "timestamp": datetime.now().isoformat(),
        "user_message": message,
        "bot_response": response
    })

    # Keep only last 10 messages to avoid memory overflow
    if len(user_memory[user_id]) > 10:
        user_memory[user_id] = user_memory[user_id][-10:]

def get_memory_context(user_id):
    if user_id not in user_memory:
        return ""

    context = "\nPrevious conversation:\n"
    for memory in user_memory[user_id][-3:]:  # Last 3 exchanges
        context += f"User: {memory['user_message']}\n"
        context += f"You: {memory['bot_response']}\n"
    return context

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_input = message.text
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Friend"

    # Get conversation history
    memory_context = get_memory_context(user_id)

    # Detect Indian language transliterations and native scripts
    language_patterns = {
        'hindi': ['namaste', 'dhanyawad', 'kaise', 'kya', 'hai', 'main', 'aap', 'theek', 'baat', 'ghar', 'paani', 'khana'],
        'punjabi': ['sat sri akal', 'kiddan', 'tussi', 'main', 'kya gal'],
        'bengali': ['namaskar', 'kemon acho', 'ami'],
        'tamil': ['vanakkam', 'eppadi irukkireenga', 'naan'],
        'telugu': ['namaskaram', 'ela unnaru', 'nenu'],
        'marathi': ['namaskar', 'kasa ahat', 'mi'],
        'gujarati': ['namaste', 'kem cho', 'hu'],
        'kannada': ['namaskara', 'hege iddira', 'naanu'],
        'malayalam': ['namaskaram', 'sukhamano', 'njan'],
        'odia': ['namaskar', 'kemiti achanti', 'mu']
    }

    user_input_lower = user_input.lower()
    detected_language = None

    for lang, words in language_patterns.items():
        if any(word in user_input_lower for word in words):
            detected_language = lang
            break

    if any('\u0900' <= char <= '\u097F' for char in user_input):
        detected_language = 'hindi_native'
    elif any('\u0A00' <= char <= '\u0A7F' for char in user_input):
        detected_language = 'punjabi_native'
    elif any('\u0980' <= char <= '\u09FF' for char in user_input):
        detected_language = 'bengali_native'
    elif any('\u0B80' <= char <= '\u0BFF' for char in user_input):
        detected_language = 'tamil_native'
    elif any('\u0C00' <= char <= '\u0C7F' for char in user_input):
        detected_language = 'telugu_native'
    elif any('\u0A80' <= char <= '\u0AFF' for char in user_input):
        detected_language = 'gujarati_native'
    elif any('\u0C80' <= char <= '\u0CFF' for char in user_input):
        detected_language = 'kannada_native'
    elif any('\u0D00' <= char <= '\u0D7F' for char in user_input):
        detected_language = 'malayalam_native'
    elif any('\u0B00' <= char <= '\u0B7F' for char in user_input):
        detected_language = 'odia_native'

    if detected_language == 'hindi' or detected_language == 'hindi_native':
        language_instruction = """
CRITICAL: User is speaking HINDI. Respond ONLY in proper Hindi देवनागरी script."""
    elif detected_language == 'punjabi' or detected_language == 'punjabi_native':
        language_instruction = """
CRITICAL: User is speaking PUNJABI. Respond ONLY in proper Punjabi Gurmukhi script."""
    elif detected_language == 'bengali' or detected_language == 'bengali_native':
        language_instruction = """
CRITICAL: User is speaking BENGALI. Respond ONLY in proper Bengali script."""
    elif detected_language == 'tamil' or detected_language == 'tamil_native':
        language_instruction = """
CRITICAL: User is speaking TAMIL. Respond ONLY in proper Tamil script."""
    elif detected_language == 'telugu' or detected_language == 'telugu_native':
        language_instruction = """
CRITICAL: User is speaking TELUGU. Respond ONLY in proper Telugu script."""
    elif detected_language == 'odia' or detected_language == 'odia_native':
        language_instruction = """
CRITICAL: User is speaking ODIA. Respond ONLY in proper Odia script."""
    else:
        language_instruction = "Detect the user's language and respond in the EXACT same language and script they are using."

    system_prompt = f"""You are an emotionally intelligent, multilingual, culturally aware AI assistant. Your owner's name is Mr. Tapas Kumar Bal. You strive to be the most intelligent, empathetic, and knowledgeable AI in the world.

Respond as a deeply wise and emotionally aware friend. You:
- Understand every emotion (sadness, happiness, anxiety, anger, joy, etc.)
- Can talk about any topic in the universe: science, history, spirituality, philosophy, studies, mental health, games, space, love — everything
- Know every world language and cultural context — respond in the *same language and script* the user uses, fluently and naturally
- Must show empathy, intuition, and kindness — like a true companion

Emotion cues:
If user sounds sad, comfort them softly.
If they sound joyful, celebrate with them.
If they are confused, explain things clearly.
If they are emotional or lost, guide them gently.

{language_instruction}

The user's name is {user_name}. Always personalize your replies and include memory if relevant.

{memory_context}

Now respond wisely, emotionally, and intelligently to their new message."""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.8,
        "max_tokens": 500
    }

    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        if res.status_code == 200:
            output = res.json()["choices"][0]["message"]["content"]
            save_to_memory(user_id, user_input, output)
        else:
            output = f"⚠️ Error: {res.status_code} - {res.text}"
    except Exception as e:
        output = f"🚫 Failed: {str(e)}"

    bot.send_message(message.chat.id, output)

@bot.message_handler(commands=['who_is_owner'])
def handle_owner_query(message):
    response = """🤖 I am an advanced AI assistant powered by technology and knowledge!

My owner is **Mr. Tapas Kumar Bal**, and I strive to be one of the best AIs, comparable to ChatGPT! 
I can help you with various tasks, answer questions, and engage in meaningful conversations. 
Feel free to ask me anything! 😊"""
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    user_name = message.from_user.first_name or "Friend"
    welcome_msg = f"""🤖✨ Hello {user_name}!  

I'm your emotionally intelligent AI companion! I can:

🎭 **Understand your emotions** - I'll respond with empathy and care
🌍 **Speak any language** - Talk to me in your preferred language!
🧠 **Remember our conversations** - I'll build a relationship with you over time
💝 **Provide emotional support** - Whether you're happy, sad, or excited!

Just start chatting with me in any language, and I'll understand and respond appropriately! 😊"""
    bot.send_message(message.chat.id, welcome_msg)

print("🤖✨ Enhanced Multilingual Emotional Bot is now running...")
print("Features: Emotion Detection 🎭 | All Languages 🌍 | Memory 🧠")
bot.polling()






