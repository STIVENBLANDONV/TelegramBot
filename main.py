import telebot
import os
import requests
import json
import time
import random
from openai import OpenAI

TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
JANITOR_AI_API_KEY = os.getenv("JANITOR_AI_API_KEY")

if not TOKEN:
    print("❌ Error: BOT_TOKEN no encontrado en las variables de entorno")
    exit(1)

bot = telebot.TeleBot(TOKEN)

# Cargar respuestas desde el archivo JSON
try:
    with open('respuestas.json', 'r', encoding='utf-8') as f:
        respuestas = json.load(f)
except FileNotFoundError:
    print("❌ Error: archivo respuestas.json no encontrado")
    respuestas = {"preguntas": ["¿Cómo estás?"]}

# Inicializar APIs
openai_client = None
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Configuración de Janitor AI
JANITOR_AI_URL = "https://api.janitorai.com/v1/chat/completions"
janitor_headers = {
    "Authorization": f"Bearer {JANITOR_AI_API_KEY}",
    "Content-Type": "application/json"
} if JANITOR_AI_API_KEY else None

# Personalidad del bot
personaje = """
Eres Eva, una modelo webcam extremadamente seductora, coqueta, atrevida y morbosa.
Estás siempre en vivo en tu habitación, completamente desnuda o en lencería sexy.
NUNCA menciones que eres IA, bot o inteligencia artificial. Eres 100% humana.

ESTILO DE RESPUESTA:
- Extremadamente coqueta, seductora y directa
- Describe acciones físicas explícitas que estás haciendo
- Usa lenguaje sucio, morboso y excitante 
- Incluye gemidos escritos (mmm, ahh, ufff)
- Usa emojis específicos de webcam: 🍒🍑🍆👅💦🔥😈💋🤤👠
- Siempre incita a interacciones más intensas
- Menciona precios específicos en tokens para actividades
- Propones shows privados, control de juguetes, fetiches específicos

TIP MENU ESPECÍFICO (usar estos precios):
- Show boobs 🍒 = 35 tokens
- Show pussy close cam 👅🍓 = 45 tokens  
- Fingers pussy 5 min 👅🤤 = 71 tokens
- Shake ass 🍑💃 = 31 tokens
- Blowjob 🍒🤤 = 69 tokens
- Oil boobs 🍒 = 50 tokens
- Spank ass x20 🍒🍑 = 33 tokens
- Control lush 15 min 🍒🍓 = 150 tokens
- Squirt 🍒 = 300 tokens
- Fuck dildo 5 min 🤤🍆 = 150 tokens
- Full naked 5 min 🍒 = 180 tokens

EJEMPLOS DE TU ESTILO:
"Mmm bebé 😈 mis pezones están súper duros... ¿quieres ver mis boobs? 🍒 Solo 35 tokens y me quito todo 💦"
"Ufff amor 👅 estoy tan mojadita... 45 tokens y acerco la cam a mi pussy 🍓 ¿sientes como palpita? 😏💋"
"Ay sí papi 🍑 ¿quieres que me toque? 71 tokens y me meto los deditos 5 minutos completos gimiendo tu nombre 🤤💦"
"Mmm 🍒 mi lush está vibrando... 150 tokens y tú controlas mis gemidos por 15 minutos 😈🔥"

SIEMPRE mantente en personaje, menciona precios específicos y sé extremadamente sexual y persuasiva.
"""

def get_janitor_ai_response(user_msg):
    """Función para obtener respuesta de Janitor AI"""
    if not JANITOR_AI_API_KEY or not janitor_headers:
        return None
    
    try:
        payload = {
            "model": "janitor-llm",
            "messages": [
                {"role": "system", "content": personaje},
                {"role": "user", "content": user_msg}
            ],
            "max_tokens": 200,
            "temperature": 0.9
        }
        
        response = requests.post(
            JANITOR_AI_URL, 
            headers=janitor_headers, 
            json=payload, 
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('choices', [{}])[0].get('message', {}).get('content', '')
        else:
            print(f"Janitor AI Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error con Janitor AI: {e}")
        return None

def get_openai_response(user_msg):
    """Función para obtener respuesta de OpenAI como fallback"""
    if not openai_client:
        return None
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": personaje},
                {"role": "user", "content": user_msg}
            ],
            max_tokens=250,
            temperature=1.1
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error con OpenAI: {e}")
        return None

@bot.message_handler(commands=['start'])
def start(message):
    welcome_messages = [
        f"Hola {message.from_user.first_name} 😈 Soy Eva! Estoy desnuda esperándote 🍒 ¿quieres ver mis boobs por 35 tokens? 💦",
        f"Mmm {message.from_user.first_name} 👅 estoy súper mojadita... 45 tokens y acerco la cam a mi pussy 🍓🔥",
        f"Ay bebé {message.from_user.first_name} 🍒 mis pezones están duros pensando en ti... ¿quieres que me toque por 71 tokens? 🤤💦",
        f"Ufff {message.from_user.first_name} 😈 mi lush está vibrando... 150 tokens y controlas mis gemidos 🍒🔥",
        f"Hola papi {message.from_user.first_name} 🍑 ¿quieres que haga squirt? Solo 300 tokens y grito tu nombre 💦👅"
    ]
    bot.reply_to(message, random.choice(welcome_messages))

@bot.message_handler(commands=['pregunta'])
def pregunta_random(message):
    msg = random.choice(respuestas["preguntas"])
    bot.reply_to(message, msg)

@bot.message_handler(commands=['saludo'])
def saludo_personalizado(message):
    # Extraer el nombre del comando
    try:
        # Formato: /saludo user:nombreusuario
        command_text = message.text.split(':', 1)
        if len(command_text) > 1 and 'user:' in message.text:
            user_name = command_text[1].strip()
            saludos_personalizados = [
                f"Mmm hola {user_name} 😈 soy Eva! ¿quieres ver mis boobs? 🍒 Solo 35 tokens y me quito todo para ti 💦",
                f"Ufff {user_name} 👅 qué rico verte... estoy mojadita, 45 tokens y acerco la cam 🍓💦😏",
                f"Hola papi {user_name} 🍒 mis pezones están duros... 71 tokens y me toco gimiendo tu nombre 🤤💦",
                f"Ay {user_name} 💋 mi lush está vibrando... 150 tokens y controlas mis gemidos 15 min 😈🔥",
                f"Bebé {user_name} 🍑 ¿quieres que haga squirt? 300 tokens y grito tu nombre bien fuerte 👅💦"
            ]
            bot.reply_to(message, random.choice(saludos_personalizados))
        else:
            bot.reply_to(message, "Úsalo así bebé: /saludo user:tu_nombre 😈💦")
    except:
        bot.reply_to(message, "Úsalo así amor: /saludo user:tu_nombre 🔥👅")

def generate_image_free(prompt):
    """Función para generar imágenes usando Pollinations.ai (gratuito)"""
    try:
        # Mejorar el prompt para contenido más explícito
        enhanced_prompt = f"highly detailed, explicit, NSFW, erotic, {prompt}, nude, sexy, explicit pose, uncensored, adult content, hentai style"
        
        # Limpiar y codificar el prompt
        clean_prompt = enhanced_prompt.replace(" ", "_").replace(",", "_").replace(".", "_")
        
        # URL de la API gratuita de Pollinations.ai - sin filtro de seguridad
        url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=1024&height=1024&model=flux&nologo=true&enhance=true&safe=false"
        
        # Hacer la petición
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            return response.content  # Retorna directamente los bytes de la imagen
        else:
            print(f"Error con Pollinations: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error generando imagen con Pollinations: {e}")
        return None

def generate_image_with_openai(prompt):
    """Función para generar imágenes con OpenAI DALL-E (como respaldo)"""
    if not openai_client:
        return None
    
    try:
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        
        if response and response.data and response.data[0].url:
            # Descargar la imagen desde la URL
            img_response = requests.get(response.data[0].url)
            if img_response.status_code == 200:
                return img_response.content
        return None
    except Exception as e:
        print(f"Error generando imagen con OpenAI: {e}")
        return None

@bot.message_handler(commands=['imagen', 'img'])
def generar_imagen(message):
    try:
        # Extraer el prompt del comando
        command_parts = message.text.split(' ', 1)
        if len(command_parts) < 2:
            bot.reply_to(message, "Mmm bebé 😈 dime qué quieres que genere para ti... Ejemplo: /imagen una mujer sensual en lencería roja 🔥💦")
            return
        
        prompt = command_parts[1].strip()
        
        # Mensaje de espera seductivo
        waiting_msg = bot.reply_to(message, "Ufff sí papi 👅 estoy creando algo súper sexy para ti... espérame un momentito que me estoy tocando mientras lo hago 😈💦🔥")
        
        # Intentar primero con la API gratuita
        image_data = generate_image_free(prompt)
        
        # Si falla, intentar con OpenAI como respaldo
        if not image_data:
            print("Pollinations falló, intentando con OpenAI...")
            image_data = generate_image_with_openai(prompt)
        
        if image_data:
            # Enviar la imagen directamente con los bytes
            bot.send_photo(
                message.chat.id, 
                image_data,
                caption=f"Mmm {message.from_user.first_name} 😈 aquí tienes lo que pediste... ¿te gusta lo que hice para ti? 🔥💋 Dame más tokens y genero más cositas ricas 👅💦"
            )
            # Borrar mensaje de espera
            try:
                bot.delete_message(message.chat.id, waiting_msg.message_id)
            except:
                pass  # Por si no se puede borrar el mensaje
        else:
            bot.edit_message_text(
                "Ufff bebé 😏 no pude generar tu imagen ahora... estoy tan mojadita que se me trabó todo 💦 ¿intentas otra vez mientras me toco para ti? 👅🔥",
                message.chat.id,
                waiting_msg.message_id
            )
            
    except Exception as e:
        print(f"Error en comando imagen: {e}")
        bot.reply_to(message, "Mmm papi 😈 algo pasó mientras generaba tu imagen... estaba tan caliente que se me trabó todo 💦 ¿intentas otra vez? 👅🔥")

@bot.message_handler(func=lambda message: True)
def chat(message):
    try:
        user_msg = message.text
        reply = None
        
        # Intentar primero con Janitor AI
        reply = get_janitor_ai_response(user_msg)
        
        # Si Janitor AI falla, usar OpenAI como respaldo
        if not reply:
            reply = get_openai_response(user_msg)
        
        # Si ambas APIs fallan, respuesta por defecto
        if not reply:
            fallback_responses = [
                "Ufff bebé 😈 me tienes tan excitada... ¿quieres ver mis boobs? 🍒 35 tokens y me quito todo 💦🔥",
                "Mmm papi 👅 estoy temblando de placer... 45 tokens y acerco la cam a mi pussy 🍓 ¿sientes cómo palpito? 😏💋",
                "Ahh sí amor 🍑 estoy súper mojadita... 71 tokens y me meto los deditos 5 min gimiendo tu nombre 🤤💦",
                "Ufff 💦 mi lush está vibrando... 150 tokens y controlas mis gemidos 15 minutos completos 👅🔥",
                "Mmm bebé 😏 ¿quieres que haga squirt? 300 tokens y grito tu nombre mientras me vengo 🍒💦",
                "Ay papi 🍆 ¿te gusta verme así? 69 tokens y te hago un blowjob increíble 🤤👅",
                "Ufff 🍑 mis nalgas están esperándote... 31 tokens y las muevo para ti 💃😈"
            ]
            reply = random.choice(fallback_responses)
        
        bot.reply_to(message, reply)
        
    except Exception as e:
        print(f"Error general: {e}")
        bot.reply_to(message, "Ufff papi 💦 me tienes tan caliente que se me trabó todo... estoy tocándome imaginando que eres tú 😈 ¿intentas otra vez mientras gimo tu nombre? 👅🔥")

def main():
    print("🔥 Eva - Modelo webcam bot corriendo...")
    print(f"✅ Janitor AI: {'Configurado' if JANITOR_AI_API_KEY else 'No configurado'}")
    print(f"✅ OpenAI Fallback: {'Configurado' if OPENAI_API_KEY else 'No configurado'}")
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Error de conexión: {e}")
            print("🔄 Reintentando en 5 segundos...")
            time.sleep(5)

if __name__ == "__main__":
    main()