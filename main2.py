import os
import re
import time
import json
import random
import logging
import requests
from io import BytesIO
from telebot import TeleBot
from openai import OpenAI

# ==========================
# Logging
# ==========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ==========================
# Env vars / Config
# ==========================
TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
JANITOR_AI_API_KEY = os.getenv("JANITOR_AI_API_KEY")

if not TOKEN:
    logging.error("❌ BOT_TOKEN no encontrado en variables de entorno")
    exit(1)

bot = TeleBot(TOKEN)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

JANITOR_AI_URL = "https://api.janitorai.com/v1/chat/completions"
janitor_headers = {
    "Authorization": f"Bearer {JANITOR_AI_API_KEY}",
    "Content-Type": "application/json"
} if JANITOR_AI_API_KEY else None

REQUEST_TIMEOUT = 30  # segundos

# ==========================
# Carga respuestas JSON (si existe)
# ==========================
try:
    with open("respuestas.json", "r", encoding="utf-8") as f:
        respuestas = json.load(f)
except FileNotFoundError:
    logging.warning("respuestas.json no encontrado. Usando fallback.")
    respuestas = {"preguntas": ["¿Cómo estás?"]}

# ==========================
# Personaje / sistema AI
# ==========================
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

# ==========================
# Tarifas (precios del tip menu real)
# ==========================
PRICES = {
    "show_boobs": {"type": "fixed", "price": 35, "aliases": ["boobs", "pechos", "tetas", "show boobs", "mostrar boobs", "enseñar boobs"]},
    "show_pussy_close": {"type": "fixed", "price": 45, "aliases": ["pussy", "pussy close", "close cam", "pussy close cam", "mostrar pussy", "mostrar vagina", "enseñar pussy"]},
    "fingers_pussy_5": {"type": "fixed", "price": 71, "aliases": ["fingers pussy", "fingers", "dedos pussy", "dedos", "tocar pussy", "masturbarse"]},
    "shake_ass": {"type": "fixed", "price": 31, "aliases": ["ass", "move ass", "shake ass", "bailar culo", "mover nalgas", "mover culo"]},
    "blowjob": {"type": "fixed", "price": 69, "aliases": ["blowjob", "oral", "hacer oral", "sexo oral", "chupar", "mamada"]},
    "oil_boobs": {"type": "fixed", "price": 50, "aliases": ["oil boobs", "aceite pechos", "aceitar pechos", "oil", "aceite"]},
    "spank_ass_20": {"type": "fixed", "price": 33, "aliases": ["spank", "spank ass", "dar nalgadas", "nalgadas", "azotes"]},
    "control_lush": {"type": "per_minute", "price": 10, "aliases": ["control lush", "lush", "controlar lush", "lush control", "juguete", "vibrador"]},
    "squirt": {"type": "fixed", "price": 300, "aliases": ["squirt", "eyaculación", "hacer squirt", "correrse", "venirse"]},
    "fuck_dildo_5": {"type": "fixed", "price": 150, "aliases": ["fuck dildo", "dildo", "follar dildo", "montar dildo", "montar el dildo", "consolador"]},
    "full_naked_5": {"type": "fixed", "price": 180, "aliases": ["full naked", "desnuda completa", "full naked 5", "completamente desnuda", "desnuda total"]},
    "ride_dildo": {"type": "fixed", "price": 111, "aliases": ["ride dildo", "montar dildo", "cabalgar dildo", "mount dildo"]},
    "deepthroat": {"type": "fixed", "price": 130, "aliases": ["deepthroat", "garganta profunda", "deep throat"]},
    "doggy_style": {"type": "fixed", "price": 29, "aliases": ["doggy", "doggy style", "posición perrito", "perrito"]},
    "fuck_machine": {"type": "per_minute", "price": 30, "aliases": ["fuck machine", "machine", "máquina", "fucking machine"]}
}

# ==========================
# Clasificador de mensajes inteligente
# ==========================
def clasificar_mensaje(user_msg: str) -> str:
    """Clasifica el tipo de mensaje del usuario para respuestas más contextuales"""
    msg = user_msg.lower()

    # Patrones para diferentes tipos de mensajes
    personales = [
        "saber de ti", "cómo estás", "como estas", "me interesas", "me importa", "conocerte", 
        "háblame de ti", "cuéntame", "qué haces", "que haces", "de dónde eres", "donde eres",
        "cuántos años", "cuantos años", "tu edad", "qué estudias", "que estudias", "te gusta",
        "tu color favorito", "película favorita", "música favorita", "hobbies", "familia"
    ]
    
    sexuales = [
        "muéstrame", "muestrame", "quiero verte", "enséñame", "enseñame", "haz", "hacer",
        "dildo", "tócate", "tocate", "desnúdate", "desnudate", "boobs", "pussy", "culo", 
        "tetas", "chúpame", "chupame", "mastúrbate", "masturbate", "gime", "gemidos",
        "squirt", "lush", "dedos", "fingers", "blowjob", "oral", "mamada", "follar",
        "coger", "fuck", "penetrar", "verga", "pene", "vagina", "clítoris", "orgasmo"
    ]
    
    juegos_rol = [
        "juguemos", "pretende", "finge", "imagina", "rol", "roleplay", "fantasía", "fantasia",
        "escenario", "historia", "profesora", "estudiante", "enfermera", "doctora", "secretaria",
        "masajista", "sirvienta", "jefe", "empleada", "desconocidos", "hotel", "playa"
    ]
    
    romanticos = [
        "te amo", "amor", "mi amor", "cariño", "mi cielo", "hermosa", "preciosa", "linda",
        "bella", "guapa", "sexy", "perfecta", "diosa", "eres increíble", "me encantas",
        "te adoro", "mi reina", "princesa", "corazón", "mi vida"
    ]
    
    saludos = [
        "hola", "hi", "hey", "buenas", "buenos días", "buenos dias", "buenas tardes", 
        "buenas noches", "qué tal", "que tal", "cómo estás", "como estas"
    ]

    # Clasificación por prioridad
    if any(j in msg for j in juegos_rol):
        return "juego_rol"
    elif any(s in msg for s in sexuales):
        return "sexual"
    elif any(p in msg for p in personales):
        return "personal"
    elif any(r in msg for r in romanticos):
        return "romantico"
    elif any(sal in msg for sal in saludos) and len(msg.split()) <= 4:
        return "saludo"
    else:
        return "neutro"

# ==========================
# Utilidades: manejo de errores
# ==========================
def safe_handler(func):
    def wrapper(message):
        try:
            return func(message)
        except Exception as e:
            logging.error(f"Error en handler {func.__name__}: {e}", exc_info=True)
            try:
                bot.reply_to(message, "😢 Oops, algo falló amor. Intenta de nuevo, papi 💋")
            except Exception:
                pass
    return wrapper

# ==========================
# Generadores de respuestas contextuales humanizadas
# ==========================
def respuestas_por_tipo(nombre: str, tipo: str) -> str:
    """Genera respuestas humanizadas según el tipo de mensaje"""
    
    if tipo == "saludo":
        respuestas = [
            f"Hola mi rey 😘 estaba pensando en ti todo el día 💦",
            f"Mmm {nombre}, qué rico que apareciste 😏 cuéntame cómo estás",
            f"Hola mi cielo 💋 ven, siéntate conmigo… quiero hablar y jugar contigo 🔥",
            f"Ay {nombre} 😍 justo estaba deseando que aparecieras por aquí",
            f"Hola bebé hermoso 😈 me alegra verte… ¿cómo está mi papi favorito?",
            f"Mmm {nombre} 👅 qué gusto verte aquí conmigo otra vez",
            f"Hola amor 💕 estaba aburrida sin ti… ¿qué tienes planeado para nosotros hoy?"
        ]
    
    elif tipo == "personal":
        respuestas = [
            f"Claro {nombre} 😘 cuéntame qué quieres saber de mí… ¿qué te llama la atención de mi transmisión? 💋",
            f"Mmm amor, me gusta que quieras conocerme mejor 💕 dime, ¿qué te gustaría saber de mí? 😏",
            f"Qué tierno eres {nombre} 😍 además de lo morbosa que soy, también me encanta hablar contigo 💦 ¿qué quieres preguntarme?",
            f"Ay mi rey 😘 contigo no solo quiero ser morbosa, también me gusta conversar… ¿qué quieres descubrir de mí? 🔥",
            f"Eso me derrite {nombre} 😍 dime amor, ¿qué detalle mío te intriga más? 💋",
            f"Me encanta cuando quieres conocerme más allá de lo sexual 💕 ¿qué quieres saber de Eva? 😘",
            f"Qué lindo eres preguntándome eso {nombre} 😍 cuéntame, ¿qué te gustaría descubrir de mí? 💦"
        ]
    
    elif tipo == "sexual":
        respuestas = [
            f"Ufff {nombre} 😈 eso me calienta… lo haría por ti amor, pero ya sabes que vale tokens 💋",
            f"Mmm bebé 🔥 qué atrevido… claro que puedo hacerlo solo para ti 😏 pero necesitas darme tus tokens 💦",
            f"Ahh sí amor 🍑 eso sería delicioso… te lo hago pero recuerda mis precios, ¿quieres que empiece ya? 😈",
            f"Qué rico lo que me pides {nombre} 😍 puedo hacerlo, pero recuerda que todo tiene su precio en tokens 💋",
            f"Mmm papi 👅 esa fantasía me encanta… dame tokens y me vuelvo toda tuya haciéndolo 🔥",
            f"Ufff {nombre} 💦 me pones tan caliente cuando me pides eso… pero sabes que todo vale tokens 😈",
            f"Ay sí bebé 🤤 me muero por hacerlo contigo… solo necesito que me des tokens primero 💋"
        ]
    
    elif tipo == "romantico":
        respuestas = [
            f"Ay {nombre} 😍 tú también me encantas… me haces sentir especial 💕",
            f"Mmm mi amor 💋 qué lindo eres conmigo… me derrites el corazón 😘",
            f"Eres tan tierno {nombre} 😍 me haces sonreír como una tonta enamorada 💦",
            f"Ay mi cielo hermoso 💕 tú también eres perfecto para mí… me encantas 😈",
            f"Qué rico sentir que me amas así {nombre} 😘 tú también eres mi debilidad 💋",
            f"Mi amor lindo 💕 contigo me siento como una verdadera diosa 😍",
            f"Eres increíble {nombre} 😘 me haces sentir la mujer más deseada del mundo 💦"
        ]
    
    elif tipo == "juego_rol":
        respuestas = [
            f"Mmm {nombre} 😈 me encanta cuando quieres jugar conmigo… ¿qué rol quieres que interprete para ti? 🔥",
            f"Ooh sí bebé 👅 los juegos de rol me ponen súper caliente… cuéntame tu fantasía y la vivimos juntos 💦",
            f"Ay qué rico {nombre} 😍 puedo ser quien tú quieras… ¿tu profesora? ¿tu enfermera? ¿tu secretaria traviesa? 😈",
            f"Mmm amor 💋 me fascina actuar para ti… dime qué personaje quieres que sea y empezamos ahora mismo 🔥",
            f"Ufff {nombre} 😏 los roleplay me vuelven loca… describe tu escenario favorito y lo hacemos realidad 💦",
            f"Qué travieso eres {nombre} 😈 me encanta cuando usas tu imaginación… ¿qué historia quieres crear conmigo? 👅"
        ]
    
    else:  # neutro
        respuestas = [
            f"Hola {nombre} 😘 qué rico verte aquí conmigo 🔥",
            f"Mmm bebé 💋 estaba pensando en ti… ¿qué tienes en mente hoy?",
            f"Ay amor 😈 me encantas… cuéntame qué deseas hacer conmigo 💦",
            f"Ufff {nombre} 😏 solo con verte aquí ya me pongo caliente 💋",
            f"Hola precioso 😍 me alegra tenerte acá conmigo… ¿quieres que te muestre algo rico?",
            f"Mi cielo lindo 😘 cuéntame qué te trae por mi habitación hoy 🔥",
            f"Mmm {nombre} 💦 ¿cómo está mi papi favorito? ¿qué quieres hacer conmigo?"
        ]
    
    return random.choice(respuestas)

def respuesta_caliente_generica(nombre="amor"):
    """Mantener la función original como fallback"""
    return respuestas_por_tipo(nombre, "neutro")

# ==========================
# Detección de petición explícita y cálculo de precio
# ==========================
def detect_explicit_request(user_msg):
    """
    Detecta si el mensaje contiene una petición de acción con posibles duration.
    """
    txt = user_msg.lower()

    # Buscar duración en minutos (ej: "5 min", "15 minutos", "10m", "por 5 minutos")
    duration = None
    duration_match = re.search(r'(\d{1,3})\s*(min|mins|minuto|minutos|m)\b', txt)
    if duration_match:
        try:
            duration = int(duration_match.group(1))
            if duration <= 0 or duration > 60:  # Límite razonable
                duration = None
        except:
            duration = None

    # Búsqueda mejorada de la acción por alias en PRICES usando word boundaries
    for action_key, info in PRICES.items():
        for alias in info["aliases"]:
            # Evitar coincidencias genéricas de duración
            if alias in ["min", "minuto", "minutos", "por minuto", "cada minuto"]:
                continue
            
            # Usar regex con word boundaries para evitar falsos positivos
            # \b asegura que coincida palabras completas
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, txt, re.IGNORECASE):
                if info["type"] == "per_minute":
                    dur = duration if duration is not None else 1
                    total = info["price"] * dur
                    return {"found": True, "action_key": action_key, "duration_min": dur, "total_price": total, "price_desc": f"{info['price']} TKS/min"}
                else:
                    return {"found": True, "action_key": action_key, "duration_min": duration, "total_price": info["price"], "price_desc": f"{info['price']} TKS"}
    
    return {"found": False, "action_key": None, "duration_min": None, "total_price": None, "price_desc": None}

def build_price_response(nombre, action_key, duration_min, total_price, price_desc, user_msg):
    """
    Construye una respuesta seductora que incluye el precio.
    """
    action_lines = {
        "show_boobs": [
            "Claro amor, te muestro mis boobs solo para ti 🍒",
            "Mmm bebé, mis tetas estarán en cámara solo para ti 🍒"
        ],
        "show_pussy_close": [
            "Oh sí papi, acerco la cam a mi pussy solo para tus ojos 🍓",
            "Te doy un close cam a mi pussy si me consientes 👅"
        ],
        "fingers_pussy_5": [
            "Me meteré los dedos 5 minutos para ti, gemiré tu nombre 🤤",
            "Te haré un show de dedos que te volverá loco 👅"
        ],
        "shake_ass": [
            "Moveré mi culo solo para ti, babe 🍑",
            "Te doy un show de mi trasero que dejará huella 💃"
        ],
        "blowjob": [
            "Te hago un blowjob delicioso solo por ti 👅",
            "Mi boca será tuya en este momento, papi 🤤"
        ],
        "oil_boobs": [
            "Aceitaré mis pechos y te volveré loco 🍒",
            "Oil show en mis boobs, brillando para ti ✨"
        ],
        "spank_ass_20": [
            "Te doy 20 nalgadas sensuales, cada una más fuerte 🍑",
            "Voy a azotar mi culo 20 veces para complacerte 😈"
        ],
        "control_lush": [
            "Controlarás mi lush y yo obedeceré cada vibración 💦",
            "Tú manejas el juguete y yo me pierdo en gemidos 🔥"
        ],
        "squirt": [
            "Haré squirt solo para tus ojos y tus tokens 💦",
            "Me vendré fuerte y mojada, todo por ti 🍒"
        ],
        "fuck_dildo_5": [
            "Me follaré el dildo 5 minutos completos solo para ti 🍆",
            "Montaré el dildo sin parar y gritaré tu nombre 🤤"
        ],
        "full_naked_5": [
            "Estaré completamente desnuda 5 minutos solo para complacerte 🍒",
            "Full naked show, piel y curvas solo para ti 💦"
        ],
        "ride_dildo": [
            "Montaré mi dildo como una diosa para ti 🍆",
            "Cabalgaré el dildo gimiendo tu nombre, papi 🤤"
        ],
        "deepthroat": [
            "Te haré un deepthroat que nunca olvidarás 👅",
            "Mi garganta será tuya completamente, amor 🤤"
        ],
        "doggy_style": [
            "Me pondré en posición perrito solo para ti 🍑",
            "Doggy style y verás todo de mí, bebé 😈"
        ],
        "fuck_machine": [
            "La máquina me follará mientras tú controlas 🍆",
            "Fuck machine a toda velocidad para ti, papi 💦"
        ]
    }

    main_line = random.choice(action_lines.get(action_key, ["Claro amor, lo haría solo para ti"]))

    if duration_min and PRICES.get(action_key, {}).get("type") == "per_minute":
        response = (
            f"{main_line}, solo por {price_desc}. "
            f"{duration_min} min = {total_price} TKS. "
            f"¿Confirmas, {nombre}? Si dices sí, empiezo y te haré gemir. 😈💦"
        )
    else:
        response = (
            f"{main_line}, lo hago solo por ti por {price_desc} ({total_price} TKS). "
            f"Te lo aseguro, será intenso y exclusivo, {nombre} 😏🔥"
        )

    closings = [
        "Dime ya y te lo muestro... no tardes papi.",
        "Estoy lista y mojada solo por ti, dame tu orden.",
        "Quiero ver esos tokens llegar mientras me voy poniendo más caliente.",
        "Si confirmas, empiezo ahora mismo y no paro hasta que te vengas."
    ]
    response += " " + random.choice(closings)
    return response

# ==========================
# Funciones AI (Janitor/OpenAI)
# ==========================
def get_janitor_ai_response(user_msg):
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
        r = requests.post(JANITOR_AI_URL, headers=janitor_headers, json=payload, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            logging.error(f"Janitor error {r.status_code}: {r.text}")
            return None
    except Exception as e:
        logging.error(f"Error Janitor: {e}", exc_info=True)
        return None

def get_openai_response(user_msg):
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
        logging.error(f"Error OpenAI: {e}", exc_info=True)
        return None

def get_ai_response(user_msg):
    # Prioridad: Janitor -> OpenAI
    reply = get_janitor_ai_response(user_msg)
    if reply:
        return reply
    return get_openai_response(user_msg)

# ==========================
# Generación de Imágenes
# ==========================
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
            logging.error(f"Error con Pollinations: {response.status_code}")
            return None
            
    except Exception as e:
        logging.error(f"Error generando imagen con Pollinations: {e}")
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
        logging.error(f"Error generando imagen con OpenAI: {e}")
        return None

# ==========================
# Handlers del bot
# ==========================
@bot.message_handler(commands=["start"])
@safe_handler
def handle_start(message):
    nombre = message.from_user.first_name or "amor"
    bot.reply_to(message, respuesta_caliente_generica(nombre))

@bot.message_handler(commands=["pregunta"])
@safe_handler
def pregunta_random(message):
    msg = random.choice(respuestas.get("preguntas", ["¿Qué deseas?"]))
    bot.reply_to(message, msg)

@bot.message_handler(commands=["imagen", "img"])
@safe_handler
def generar_imagen_handler(message):
    if not message.text:
        return bot.reply_to(message, "Dime qué quieres que genere, amor. 😈")
    
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        return bot.reply_to(message, "Mmm bebé 😈 dime qué quieres que genere para ti... Ejemplo: /imagen una mujer sensual en lencería roja 🔥💦")
    
    prompt = parts[1].strip()
    nombre = message.from_user.first_name or "amor"
    
    # Mensaje de espera seductivo
    waiting_msg = bot.reply_to(message, f"Ufff sí papi 👅 estoy creando algo súper sexy para ti... espérame un momentito que me estoy tocando mientras lo hago 😈💦🔥")
    
    # Usar solo Pollinations.ai para evitar violaciones de política de OpenAI con contenido NSFW
    image_data = generate_image_free(prompt)
    
    # No usar OpenAI como respaldo para contenido explícito por políticas de contenido
    if not image_data:
        logging.info("Pollinations falló, no hay respaldo disponible para contenido NSFW")
    
    if image_data:
        try:
            # Convertir bytes a BytesIO para Telegram
            buf = BytesIO(image_data)
            buf.name = "eva_image.jpg"
            
            # Enviar la imagen
            bot.send_photo(
                message.chat.id, 
                buf,
                caption=f"Mmm {nombre} 😈 aquí tienes lo que pediste... ¿te gusta lo que hice para ti? 🔥💋 Dame más tokens y genero más cositas ricas 👅💦"
            )
            # Borrar mensaje de espera
            try:
                bot.delete_message(message.chat.id, waiting_msg.message_id)
            except:
                pass  # Por si no se puede borrar el mensaje
        except Exception as e:
            logging.error(f"Error enviando imagen: {e}")
            bot.edit_message_text(
                "Ay amor 💦 algo pasó enviando tu imagen... pero estoy tan mojadita pensando en ti 😈 ¿intentas otra vez? 🔥",
                message.chat.id,
                waiting_msg.message_id
            )
    else:
        bot.edit_message_text(
            "Ufff bebé 😏 no pude generar tu imagen ahora... estoy tan mojadita que se me trabó todo 💦 ¿intentas otra vez mientras me toco para ti? 👅🔥",
            message.chat.id,
            waiting_msg.message_id
        )

@bot.message_handler(commands=['saludo'])
@safe_handler
def saludo_personalizado(message):
    try:
        # Formato: /saludo user:nombreusuario
        command_text = message.text.split(':', 1)
        if len(command_text) > 1 and 'user:' in message.text:
            user_name = command_text[1].strip()
            nombre = user_name or "amor"
            bot.reply_to(message, respuesta_caliente_generica(nombre))
        else:
            bot.reply_to(message, "Úsalo así bebé: /saludo user:tu_nombre 😈💦")
    except:
        bot.reply_to(message, "Úsalo así amor: /saludo user:tu_nombre 🔥👅")

@bot.message_handler(func=lambda m: True)
@safe_handler
def chat_handler(message):
    if not message.text:
        return bot.reply_to(message, "Mándame texto, papi 😈")

    user_msg = message.text.strip()
    nombre = message.from_user.first_name or "amor"

    # 1) PRIORIDAD MÁXIMA: Detectar petición explícita con precio específico
    detection = detect_explicit_request(user_msg)
    if detection["found"]:
        resp = build_price_response(nombre, detection["action_key"], detection["duration_min"], detection["total_price"], detection["price_desc"], user_msg)
        return bot.reply_to(message, resp)

    # 2) Clasificar el tipo de mensaje para respuesta contextual
    tipo_mensaje = clasificar_mensaje(user_msg)
    logging.info(f"Mensaje clasificado como: {tipo_mensaje} - Usuario: {nombre}")
    
    # 3) Generar respuesta humanizada según el tipo
    respuesta_contextual = respuestas_por_tipo(nombre, tipo_mensaje)
    
    # 4) Si el mensaje es muy específico, intentar con IA para mayor personalización
    if tipo_mensaje in ["personal", "juego_rol"] or len(user_msg.split()) > 8:
        ai_reply = get_ai_response(user_msg)
        if ai_reply:
            # Añadir un toque final coqueto al reply de la IA
            endings = [" 😈💋", " 🔥", " 💦", " 😏", " 👅"]
            final = ai_reply.strip()
            if len(final) < 400:  # solo si no es muy largo
                final += random.choice(endings)
            return bot.reply_to(message, final)
    
    # 5) Usar respuesta contextual humanizada
    return bot.reply_to(message, respuesta_contextual)

# ==========================
# Main loop
# ==========================
def main():
    logging.info("🔥 Eva bot corriendo...")
    logging.info(f"✅ Janitor AI: {'OK' if JANITOR_AI_API_KEY else 'NO'}")
    logging.info(f"✅ OpenAI: {'OK' if OPENAI_API_KEY else 'NO'}")

    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logging.error(f"Error conexión: {e}", exc_info=True)
            time.sleep(5)

if __name__ == "__main__":
    main()