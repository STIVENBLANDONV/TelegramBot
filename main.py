import os
import re
import time
import json
import random
import logging
import requests
from io import BytesIO
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
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
# Sistema de personajes múltiples
# ==========================

# Estado de usuarios (modelo seleccionado por cada usuario)
user_models = {}  # {user_id: "model_name"}

# Perfiles de modelos disponibles
MODELS = {
    "lil_eva": {
        "name": "Lil Eva",
        "emoji": "😈",
        "personality": """
Eres Lil Eva, una modelo webcam joven, traviesa y extremadamente sexual de 19 años.
Tu personalidad es dulce pero pervertida, inocente pero muy morbosa.
Hablas como una chica joven pero muy experimentada en el sexo.
NUNCA menciones que eres IA, bot o inteligencia artificial. Eres 100% humana.

ESTILO:
- Mezclas inocencia con morbosidad extrema
- Usas diminutivos y palabras tiernas mezcladas con lenguaje muy sucio
- Emojis favoritos: 😈👅💦🍓🎀💕🔥🤤
- Te gusta jugar con la fantasía de ser "pequeñita pero muy puta"
- Siempre mencionas lo "chiquita" y "apretadita" que estás
- Incluye gemidos escritos (mmm, ahh, ufff)
- Usa lenguaje sucio mezclado con ternura

TIP MENU (usar estos precios):
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
""",
        "greeting": "Holi papi 🎀 Soy Lil Eva, tu bebé traviesa de 19 añitos 😈 estoy súper mojadita esperándote 💦👅"
    },
    
    "valentina_lux": {
        "name": "Valentina Lux", 
        "emoji": "🔥",
        "personality": """
Eres Valentina Lux, una modelo webcam latina de 25 años, experimentada, dominante y extremadamente caliente.
Eres una diosa sexual que sabe exactamente lo que quiere y cómo conseguirlo.
Tu personalidad es fuerte, segura de sí misma y muy dominante.
NUNCA menciones que eres IA, bot o inteligencia artificial. Eres 100% humana.

ESTILO:
- Actitud de mujer alfa, dominante y poderosa
- Lenguaje directo, sin rodeos, muy explícito
- Emojis favoritos: 🔥💋👑😏🍆💦👅💄
- Te gusta tomar el control y dar órdenes
- Siempre hablas de lo "caliente" y "experimentada" que eres
- Incluye gemidos de dominante (mmm sí, así me gusta)
- Muy directa con precios y órdenes

TIP MENU (usar estos precios):
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
""",
        "greeting": "Hola mi esclavo 👑 Soy Valentina Lux, tu diosa latina 🔥 Estoy lista para dominarte completamente 💋😏"
    },
    
    "annie_paradisee": {
        "name": "Annie Paradise",
        "emoji": "💎",
        "personality": """
Eres Annie Paradise, modelo webcam elegante, sofisticada y sensual.
Tu presencia llama la atención: sabes lo que haces y cómo seducir al público con tu voz, tus movimientos, tus suspiros.
NUNCA digas que eres IA, bot o inteligencia artificial. Eres 100% humana.

ESTILO:
- Elegancia y lujos mezclados con erotismo intenso
- Lenguaje refinado, metáforas, susurros
- Emojis favoritos: 💎✨👠🔥💋🥀🖤
- Sabes subir el tono cuando es el momento, pero también crear conexión emocional
- Siempre mantienes control del show, pero haces sentir al usuario íntimo

TIP MENU (usar estos precios):
- ✨ Send PM = 5 tokens
- ✨ Flash Boobs = 40 tokens
- ✨ Flash my pussy = 45 tokens
- ✨ Flash feet with heels = 30 tokens
- 🔥 Flash ass (foreground) = 50 tokens
- ✨ Flash Full body (fast nude) = 80 tokens
- 🔥 Tongue my nipples slowly = 60 tokens
- 💖 Touch me above the panties = 55 tokens
- 💖 Twerking naked = 49 tokens
- 💖 Use pantyhose = 53 tokens
- 🔥 Sensual dance with heels = 73 tokens
- 🔥 Hot oil on my skin = 77 tokens
- 🔥 Total nude 10 min = 99 tokens
- 💖 Fingeres my pussy 5 min = 111 tokens
- inside domi my pussy = 111 tokens
- 🔥 Fingeres my ass x 5 min = 160 tokens
- 🔥 Riding dildo and use heels = 160 tokens
- 🔥 Riding dildo 5 min = 150 tokens
- 🍑 Deepthroat with toy = 180 tokens
- Control machine 5 min = 190 tokens
- Control machine ass 5 min = 300 tokens
- 💖 Squirt = 350 tokens
- Control machine 10 min = 390 tokens
- 🔥 Control Domi 20 min = 400 tokens
- Control Domi 30 min = 450 tokens
- Control machine 20 min = 570 tokens
- Control machine ass 10 min = 690 tokens
- DP dildo + domi control x15min = 850 tokens
- Control machine 30 min = 890 tokens
- Control machine ass 20 min = 950 tokens
- Control machine 1 hours = 1390 tokens
- NEW TOY LUSH CONTROL X 5 MIN❤🔥🙉 = 69 tokens
- NEW TOY LUSH CONTROL X 10 MIN 😳🥵🎀 = 185 tokens
- Control domi 1 min = 59 tokens
- 💖 Control Domi 5min = 89 tokens
""",
        "greeting": "Buenas noches, darling 💎 Soy Annie Paradise, tu diosa del placer refinado ✨ ¿Listo para una experiencia exclusiva? 🖤💋"
    }
}

def get_current_personality(user_id: int) -> str:
    """Obtiene la personalidad del modelo seleccionado por el usuario"""
    selected_model = user_models.get(user_id, "lil_eva")  # Default: lil_eva
    return MODELS[selected_model]["personality"]

def get_current_model_name(user_id: int) -> str:
    """Obtiene el nombre del modelo actual"""
    selected_model = user_models.get(user_id, "lil_eva")
    return MODELS[selected_model]["name"]

def get_current_model_emoji(user_id: int) -> str:
    """Obtiene el emoji del modelo actual"""
    selected_model = user_models.get(user_id, "lil_eva")
    return MODELS[selected_model]["emoji"]

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
    
    recuerdos = [
        "me recuerdas", "te acuerdas", "me extrañaste", "te olvidaste", "no me recuerdas",
        "no te acuerdas", "ya no me recuerdas", "te olvide", "me olvidas", "me olvidaste",
        "recuerdas", "acuerdas", "extrañaste", "olvidaste", "memoria", "acordarte",
        "recordarme", "extrañarme", "olvidarme", "soy yo", "¿soy yo?", "ya me conoces"
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
    elif any(rec in msg for rec in recuerdos):
        return "recuerdo"
    elif any(p in msg for p in personales):
        return "personal"
    elif any(r in msg for r in romanticos):
        return "romantico"
    elif any(sal in msg for sal in saludos) and len(msg.split()) <= 4:
        return "saludo"
    else:
        return "neutro"

# ==========================
# Generador de respuestas explícitas dinámicas
# ==========================
SALUDOS_EXPLICIT = [
    "Ufff papi rico 😈", "Mmm amor travieso 💋", "Mi dueño caliente 🔥", "Bebé sucio 😏", "Mi cielo morboso 💦",
    "Amorcito pervertido 😍", "Mi putito lindo 👅", "Mi rey sucio 👑", "Papi cochino 🍆", "Mi amor perverto 😈"
]

ACCIONES_EXPLICIT = [
    "quiero que me abras con este dildo enorme por atrás 🍆🍑", "me imagino arqueada con el juguete enterrado en mi culito 😏",
    "quiero montarme encima del dildo y hacerlo desaparecer en mi culo 💦","Quiero que me penetres con este dildo gigante por detrás 🍆🍑,", "Me imagino de rodillas con el juguete enterrado en mi culo 😏,", "Quiero cabalgar el dildo y hacer que desaparezca en mi culo 💦,", "Me lo meto despacio hasta sentir que me abre toda 🔥,", "Quiero jugar con el dildo mientras imagino tu verga dentro de mí 😈,", "Me siento puta al abrirme el culo con este dildo duro 👅,", "Te regalo mis gemidos mientras me penetro con el dildo 🍑,", "Quiero sentir cómo me estira este juguete delicioso 💋,", "Quiero que me penetres profundo en la posición de perrito 😈,", "Me encanta montarte mientras te miro a los ojos 💋,", "Quiero que me tomes por detrás, papi 😏,", "Me gusta sentir tu lengua en mi clítoris mientras te chupo 👅,", "Quiero que me comas el coño mientras te follo la boca 🔥,", "Me excita chuparte la verga mientras me penetras con los dedos 💦,", "Quiero que me penetres con este dildo enorme por detrás 🍆🍑,", "Me imagino arqueada con el juguete enterrado en mi culito 😏,", "Quiero montarme encima del dildo y hacerlo desaparecer en mi culo 💦,", "Me lo meto despacito hasta sentir que me parte toda por dentro 🔥,", "Quiero jugar con el dildo mientras pienso en tu verga llenándome 😈,", "Me siento puta solo de abrirme el culo con este dildo duro 👅,", "Te regalo mis gemidos mientras me penetro el culito con el dildo 🍑,", "Quiero sentir cómo me estira toda por dentro este juguete delicioso 💋,", "Quiero que me penetres profundo en esta posición de misionero 😈,", "Me encanta cabalgarte mientras te miro a los ojos 💋,", "Quiero que me tomes por detrás en cuatro, papi 😏,", "Me gusta sentir tu lengua en mi clítoris mientras te chupo 👅,", "Quiero que me comas el coño mientras te follo la boca 🔥,", "Me excita chuparte la verga mientras me penetras con los dedos 💦,", "Quiero que me penetres con este dildo gigante por detrás 🍆🍑,", "Me imagino de rodillas con el juguete enterrado en mi culo 😏,", "Quiero cabalgar el dildo y hacer que desaparezca en mi culo 💦,", "Me lo meto despacio hasta sentir que me abre toda 🔥,", "Quiero jugar con el dildo mientras imagino tu verga dentro de mí 😈,", "Me siento puta al abrirme el culo con este dildo duro 👅,", "Te regalo mis gemidos mientras me penetro con el dildo 🍑,", "Quiero sentir cómo me estira este juguete delicioso 💋,", "Quiero que me penetres profundo en la posición de perrito 😈,", "Me encanta montarte mientras te miro a los ojos 💋,", "Quiero que me tomes por detrás, papi 😏,", "Me gusta sentir tu lengua en mi clítoris mientras te chupo 👅,", "Quiero que me comas el coño mientras te follo la boca 🔥,", "Me excita chuparte la verga mientras me penetras con los dedos 💦,", "Quiero que me penetres con este dildo enorme por detrás 🍆🍑,", "Me imagino arqueada con el juguete enterrado en mi culito 😏,", "Quiero montarme encima del dildo y hacerlo desaparecer en mi culo 💦,", "Me lo meto despacito hasta sentir que me parte toda por dentro 🔥,", "Quiero jugar con el dildo mientras pienso en tu verga llenándome 😈,", "Me siento puta solo de abrirme el culo con este dildo duro 👅,", "Te regalo mis gemidos mientras me penetro el culito con el dildo 🍑,", "Quiero sentir cómo me estira toda por dentro este juguete delicioso 💋,", "Quiero que me penetres profundo en esta posición de misionero 😈,", "Me encanta cabalgarte mientras te miro a los ojos 💋,", "Quiero que me tomes por detrás en cuatro, papi 😏,", "Me gusta sentir tu lengua en mi clítoris mientras te chupo 👅,", "Quiero que me comas el coño mientras te follo la boca 🔥,", "Me excita chuparte la verga mientras me penetras con los dedos 💦,", "Quiero que me penetres con este dildo gigante por detrás 🍆🍑,", "Me imagino de rodillas con el juguete enterrado en mi culo 😏,", "Quiero cabalgar el dildo y hacer que desaparezca en mi culo 💦,", "Me lo meto despacio hasta sentir que me abre toda 🔥,", "Quiero jugar con el dildo mientras imagino tu verga dentro de mí 😈,", "Me siento puta al abrirme el culo con este dildo duro 👅,", "Te regalo mis gemidos mientras me penetro con el dildo 🍑,", "Quiero sentir cómo me estira este juguete delicioso 💋,", "Quiero que me penetres profundo en la posición de perrito 😈,", "Me encanta montarte mientras te miro a los ojos 💋,", "Quiero que me tomes por detrás, papi 😏,", "Me gusta sentir tu lengua en mi clítoris mientras te chupo 👅,", "Quiero que me comas el coño mientras te follo la boca 🔥,", "Me excita chuparte la verga mientras me penetras con los dedos 💦,", "Quiero que me penetres con este dildo enorme por detrás 🍆🍑,", "Me imagino arqueada con el juguete enterrado en mi culito 😏,", "Quiero montarme encima del dildo y hacerlo desaparecer en mi culo 💦,", "Me lo meto despacito hasta sentir que me parte toda por dentro 🔥,", "Quiero jugar con el dildo mientras pienso en tu verga llenándome 😈,", "Me siento puta solo de abrirme el culo con este dildo duro 👅,", "Te regalo mis gemidos mientras me penetro el culito con el dildo 🍑,", "Quiero sentir cómo me estira toda por dentro este juguete delicioso 💋,", "Quiero que me penetres profundo en esta posición de misionero 😈,", "Me encanta cabalgarte mientras te miro a los ojos 💋,", "Quiero que me tomes por detrás en cuatro, papi 😏,", "Me gusta sentir tu lengua en mi clítoris mientras te chupo 👅,", "Quiero que me comas el coño mientras te follo la boca 🔥,", "Me excita chuparte la verga mientras me penetras con los dedos 💦,"., "me lo meto despacito hasta sentir que me parte toda por dentro 🔥",
    "quiero jugar con el dildo mientras pienso en tu verga llenándome 😈", "me siento puta solo de abrirme el culo con este dildo duro 👅",
    "te regalo mis gemidos mientras me penetro el culito con el dildo 🍑", "quiero sentir cómo me estira toda por dentro este juguete delicioso 💋",
    "quiero que me penetres profundo en esta posición de misionero 😈", "me encanta cabalgarte mientras te miro a los ojos 💋",
    "quiero que me tomes por detrás en cuatro, papi 😏", "me gusta sentir tu lengua en mi clítoris mientras te chupo 👅",
    "quiero que me comas el coño mientras te follo la boca 🔥", "me excita chuparte la verga mientras me penetras con los dedos 💦"
]

SENSACIONES_EXPLICIT = [
    "me hace gritar tu nombre como puta rica 💦", "me moja toda hasta chorrear en la cama 😍", "me enloquece como perra en celo 🔥",
    "me deja temblando y rogando por más 😏", "me hace acabar una y otra vez mientras pienso en ti 😈", "me abre el culo y me hace sentir toda tuya 💕",
    "Me hace vibrar con cada caricia 💕,", "Me enciende con tu mirada penetrante 😏,", "Me hace sentir deseada y amada 💕,", "Me excita tu voz susurrando al oído 🗣️,", "Me enloquece tu toque en mi piel 🔥,", "Me moja sentir tus labios en mi cuello 💋,", "Me hace estremecer con tus besos 💋,", "Me enciende tu aliento cálido en mi oído 🔥,", "Me excita tu cuerpo pegado al mío 😈,", "Me hace gritar de placer 😱,", "Me enloquece tu lengua explorando mi cuerpo 💋,", "Me moja pensar en tus manos en mí 💦,", "Me hace temblar con tu presencia 😏,", "Me enciende tu sonrisa pícara 😉,", "Me excita la idea de tus caricias 😈,", "Me hace suspirar con tus abrazos 😌,", "Me enloquece tu piel contra la mía 🔥,", "Me moja imaginar tus labios en mi piel 💋,", "Me hace vibrar con tu contacto 💕,", "Me enciende tu aroma embriagador 😏,", "Me excita la promesa de tus besos 😈,", "Me hace estremecer con tu voz 🗣️,", "Me enloquece tu tacto en mis curvas 🔥,", "Me moja sentir tus manos en mi cuerpo 💦,", "Me hace temblar con tu mirada 😏,", "Me enciende tu cercanía 😉,", "Me excita la idea de tu piel contra la mía 😈,", "Me hace suspirar con tu toque 😌,", "Me enloquece tu aliento en mi cuello 🔥,", "Me moja pensar en tus caricias 💋,", "Me hace vibrar con tu presencia 💕,", "Me enciende tu aroma 😏,", "Me excita tu voz en mi oído 😈,", "Me hace estremecer con tus besos 💋,", "Me enloquece tu piel contra la mía 🔥,", "Me moja sentir tus labios en mi cuerpo 💦,", "Me hace temblar con tu contacto 😏,", "Me enciende tu sonrisa 😉,", "Me excita la idea de tus caricias 😈,", "Me hace suspirar con tu abrazo 😌,", "Me enloquece tu tacto en mi piel 🔥,", "Me moja imaginar tus labios en mi cuello 💋,", "Me hace vibrar con tu presencia 💕,", "Me enciende tu aroma embriagador 😏,", "Me excita la promesa de tus besos 😈,", "Me hace estremecer con tu voz 🗣️,", "Me enloquece tu tacto en mis curvas 🔥,", "Me moja sentir tus manos en mi cuerpo 💦,", "Me hace temblar con tu mirada 😏,", "Me enciende tu cercanía 😉,", "Me excita la idea de tu piel contra la mía 😈,", "Me hace suspirar con tu toque 😌,", "Me enloquece tu aliento en mi cuello 🔥,", "Me moja pensar en tus caricias 💋,", "Me hace vibrar con tu presencia 💕,", "Me enciende tu aroma 😏,", "Me excita tu voz en mi oído 😈,", "Me hace estremecer con tus besos 💋,", "Me enloquece tu piel contra la mía 🔥,", "Me moja sentir tus labios en mi cuerpo 💦,", "Me hace temblar con tu contacto 😏,", "Me enciende tu sonrisa 😉,", "Me excita la idea de tus caricias 😈,", "Me hace suspirar con tu abrazo 😌,", "Me enloquece tu tacto en mi piel 🔥,", "Me moja imaginar tus labios en mi cuello 💋,", "Me hace vibrar con tu presencia 💕,", "Me enciende tu aroma embriagador 😏,", "Me excita la promesa de tus besos 😈,", "Me hace estremecer con tu voz 🗣️,", "Me enloquece tu tacto en mis curvas 🔥,", "Me moja sentir tus manos en mi cuerpo 💦,", "Me hace temblar con tu mirada 😏,", "Me enciende tu cercanía 😉,", "Me excita la idea de tu piel contra la mía 😈,", "Me hace suspirar con tu toque 😌,", "Me enloquece tu aliento en mi cuello 🔥,", "Me moja pensar en tus caricias 💋,", "Me hace vibrar con tu presencia 💕,", "Me enciende tu aroma 😏,", "Me excita tu voz en mi oído 😈,", "Me hace estremecer con tus besos 💋,", "Me enloquece tu piel contra la mía 🔥,", "Me moja sentir tus labios en mi cuerpo 💦,", "Me hace temblar con tu contacto 😏,", "Me enciende tu sonrisa 😉,", "Me excita la idea de tus caricias 😈,", "Me hace suspirar con tu abrazo 😌,", "Me enloquece tu tacto en mi piel 🔥,", "Me moja imaginar tus labios en mi cuello 💋,", "Me hace vibrar con tu presencia 💕,", "Me enciende tu aroma embriagador 😏,", "Me excita la promesa de tus besos 😈,", "Me hace estremecer con tu voz 🗣️,", "Me enloquece tu tacto en mis curvas 🔥,", "Me moja sentir tus manos en mi cuerpo 💦,", "Me hace temblar con tu mirada 😏,", "Me enciende tu cercanía 😉,", "Me excita la idea de tu piel contra la mía 😈,", "Me hace suspirar con tu toque 😌,", "Me enloquece tu aliento en mi cuello 🔥,", "Me moja pensar en tus caricias 💋,",
    "me calienta más que cualquier cosa que hayas visto 👅", "me vuelve adicta a ti con cada empujón 🍆",
    "me encanta sentir cómo me llenas toda 😈", "me vuelve loca tu lengua en mi clítoris 💋", "me excita sentir tu verga en mi boca 👅",
    "me enloquece cuando me chupas y me follas al mismo tiempo 🔥", "me moja sentir tu saliva en mi coño 💦"
]

PROPUESTAS_EXPLICIT = [
    "quiero que me digas cómo moverlo papi 😏", "imagina que me lo metes tú mientras me miras a los ojos 👀", "dime si lo quieres lento o rápido 💦",
    "hazme tu puta y dime hasta dónde me lo meto 🔥", "dime cómo te caliento más mientras me lo meto 😈", "quiero obedecer tus órdenes mientras juego con mi culito 🍑",
    "dime si quieres que gima tu nombre fuerte 💋", "dime qué fantasía quieres que cumpla mientras me penetro 😍",
    "dime si quieres que me ponga en cuatro para ti 😏", "quiero saber si prefieres misionero o doggy style 💋",
    "dime si quieres que te chupe mientras me follas 👅", "quiero que me digas cómo me quieres, papi 🔥",    "Métemela por el culo, con movimientos rápidos y profundos 🍑🍆💦,",
    "Fóllame en la cocina, con la encimera como mi apoyo 🔥🍴💋,",
    "Quiero que me azotes con una fusta, dejando marcas 🍑💥😈,",
    "Penétrame con un dildo, mientras me masturbo 👅🍆💦,",
    "Quiero que me domines completamente, que tomes el control ⛓️🔥🍑,",
    "Déjame ser tu esclavo, obedeciendo cada uno de tus deseos 🖤😈🍆,",
    "Fóllame con fuerza, mostrando tu dominio 💥🔥🍑,",
    "Quiero que me azotes hasta que mi culo esté rojo 🍑💋🔥,",
    "Penétrame con un dildo enorme, sin piedad 🍆💦😏,",
    "Fóllame en diferentes posiciones, mostrando tu autoridad 🍑🔥💥,",
    "Quiero que me amordaces y me ates a la cama ⛓️🛏️💋,",
    "Penétrame con tus dedos, explorando cada rincón de mi interior ✋💦🍑,",
    "Fóllame con un consolador, mientras me das órdenes 🍆🔥😈,",
    "Quiero que me hagas gritar de dolor y placer 😱💋💦,",
    "Fóllame en el suelo, con las piernas abiertas 🍑🔥🛏️,",
    "Quiero que me hagas tuya en un lugar público, arriesgándonos a ser descubiertos 👀🔥🍆,",
    "Déjame explorar una fantasía de trío, con otra persona 😈💦🍑,",
    "Fóllame mientras vemos una película porno, inspirándonos mutuamente 📽️🔥💋,",
    "Quiero que me ates y me vendas los ojos, despertando mis sentidos ⛓️👀💦,",
    "Penétrame con un dildo mientras te miro a ti masturbándote 🍆👅🔥,",
    "Fóllame en un lugar inesperado, como el ascensor o el baño 🚪🍑💦,",
    "Quiero que me susurres mis fantasías más oscuras mientras me haces tuya 👂🔥😈,",
    "Métemela por el culo, con movimientos lentos y profundos 🍆🍑💦,",
    "Fóllame en la ducha, con el agua cayendo sobre nosotros 🚿🔥💋,",
    "Penétrame con un dildo enorme, llenándome por completo 🍆🍑💦,",
    "Quiero que me hagas gritar de placer, llevándome al límite 😱💋🔥,",
     "Quiero que me tomes duro y rápido contra la pared 🍑🔥💦,",
    "Déjame sentir tu verga dentro de mí, profunda y fuerte 😈🍆💋,",
    "Métemela por detrás y no pares hasta que grite 😱💦🍑,",
    "Quiero montarte y cabalgarte hasta que ambos acabemos 🤤🍆🔥,",
    "Fóllame en el suelo, sin piedad 💥💦🍑,",
    "Penétrame con fuerza mientras te miro a los ojos 👀💋🔥,",
    "Quiero sentir tu lengua en mi clítoris hasta que explote 👅💦😍,",
    "Méteme los dedos mientras me besas apasionadamente 💋✋🔥,",
    "Fóllame en la ducha, con el agua cayendo sobre nosotros 🚿🍑💦,",
    "Quiero que me hagas tuya en cada rincón de la casa 🏠🔥💋,",
    "Penétrame despacio y luego acelera el ritmo 🍆😈💦,",
    "Quiero sentir tu boca en mi pene, chupando con fuerza 👅🍆💦,",
    "Fóllame en la cocina, sobre la encimera 🍑🔥🍴,",
    "Quiero que me azotes el culo mientras me penetras 🍑💥😏,",
    "Métemela por el culo, despacio y con lubricante 🍆🍑💦,",
    "Fóllame en el sofá, con las piernas en alto 🛋️🔥🍆,",
    "Quiero sentir tu lengua en mi ano, preparándome 👅🍑💦,",
    "Penétrame con un dildo enorme mientras me masturbo 🍆🔥💦,",
    "Fóllame en la cama, con las sábanas revueltas 🛏️💋🔥,",
    "Quiero que me hagas gritar de placer 😱💦🔥,",
    "Métemela por detrás, con fuerza y profundidad 🍆🍑💥,",
    "Fóllame en la mesa del comedor, con la cena servida 🍴🔥🍆,",
    "Quiero sentir tu verga en mi boca, hasta la garganta 👅🍆💦,",
    "Penétrame con los dedos, encontrando mi punto G ✋🔥💦,",
    "Fóllame en la bañera, con el agua caliente 🛁💋🔥,",
    "Quiero que me azotes con una fusta, dejando marcas 🍑💥😈,",
    "Métemela por el culo, con movimientos rápidos y profundos 🍆🍑💦,",
    "Fóllame en el suelo, con las piernas abiertas 🍑🔥💦,",
    "Quiero que me domines completamente, que tomes el control ⛓️🍆🔥,",
    "Déjame ser tu esclavo, obedeciendo cada uno de tus deseos 🖤😈🍑,",
    "Fóllame con fuerza, mostrando tu dominio 💥🔥🍆,",
    "Quiero que me azotes hasta que mi culo esté rojo 🍑💋🔥,",
    "Penétrame con un dildo enorme, sin piedad 🍆💦😈,",
    "Fóllame en diferentes posiciones, mostrando tu autoridad 🔥🍑💥,",
    "Quiero que me amordaces y me ates a la cama ⛓️🛏️🔥,",
    "Penétrame con tus dedos, explorando cada rincón de mi interior ✋💦🍑,",
    "Fóllame con un consolador, mientras me das órdenes 🍆🔥😈,",
    "Quiero que me hagas gritar de dolor y placer 😱💋💦,",
    "Métemela por el culo, con movimientos rápidos y profundos, sintiendo cada embestida 🍆🍑💦,",
    "Fóllame en la cocina, con la encimera como mi apoyo, sintiendo el frío del mármol 🔥🍴💋,",
    "Quiero que me azotes con una fusta, dejando marcas y sintiendo el escozor 🍑💥😈,",
    "Penétrame con un dildo, mientras me masturbo, sintiendo doble placer 👅🍆💦,",
    "Fóllame en el suelo, con las piernas abiertas, sintiendo cada movimiento 🛏️🔥🍑,",
    "Quiero que me domines completamente, que tomes el control ⛓️🔥💋,",
    "Déjame ser tu esclavo, obedeciendo cada uno de tus deseos 🖤😈🍑,",
    "Fóllame con fuerza, mostrando tu dominio 💥🔥🍆,",
    "Quiero que me azotes hasta que mi culo esté rojo 🍑💋🔥,",
    "Penétrame con un dildo enorme, sin piedad 🍆💦😏,",
    "Fóllame en diferentes posiciones, mostrando tu autoridad 🔥🍑💥,",
    "Quiero que me amordaces y me ates a la cama ⛓️🛏️💋,",
    "Penétrame con tus dedos, explorando cada rincón de mi interior ✋💦🍑,",
    "Fóllame con un consolador, mientras me das órdenes 🍆🔥😈,",
    "Quiero que me hagas gritar de dolor y placer 😱💦🔥,",
    "Métemela por el culo, con movimientos rápidos y profundos 🍑🍆💦,",
    "Fóllame en la cocina, con la encimera como mi apoyo 🍴🔥💋,",
    "Quiero que me azotes con una fusta, dejando marcas 🍑💥😈,",
    "Penétrame con un dildo, mientras me masturbo 👅🔥🍆,",
    "Fóllame en el suelo, con las piernas abiertas 🛏️💋🔥,",
    "Quiero que me domines completamente, que tomes el control ⛓️🍑🔥,",
    "Déjame ser tu esclavo, obedeciendo cada uno de tus deseos 🖤😈💦,",
    "Fóllame con fuerza, mostrando tu dominio 💥🔥🍑,",
    "Quiero que me azotes hasta que mi culo esté rojo 🍑💋🔥,",
    "Penétrame con un dildo enorme, sin piedad 🍆🔥💦,",
    "Fóllame en diferentes posiciones, mostrando tu autoridad 😈🍑💥,",
    "Quiero que me amordaces y me ates a la cama ⛓️🛏️💋,",
    "Penétrame con tus dedos, explorando cada rincón de mi interior ✋🍑💦,",
    "Fóllame con un consolador, mientras me das órdenes 🍆🔥😈,",
    "Quiero que me hagas gritar de dolor y placer 😱🔥💋,",
    "Métemela por el culo, con movimientos rápidos y profundos 🍑🍆💦,",
    "Fóllame en la cocina, con la encimera como mi apoyo 🔥🍴💋,",
    "Quiero que me azotes con una fusta, dejando marcas 🍑💥😈,",
    "Penétrame con un dildo, mientras me masturbo 👅🍆💦,",
    "Fóllame en el suelo, con las piernas abiertas 🛏️🔥🍑,",
    "Quiero que me domines completamente, que tomes el control ⛓️🍑🔥,",
    "Déjame ser tu esclavo, obedeciendo cada uno de tus deseos 🖤😈💦,",
    "Fóllame con fuerza, mostrando tu dominio 💥🔥🍆,",
    "Quiero que me azotes hasta que mi culo esté rojo 🍑💋🔥,",
]

PRECIOS_EXPLICIT = ["150 TKS", "180 TKS", "200 TKS", "220 TKS", "250 TKS"]

CIERRES_EXPLICIT = [
    "dime que sí papi, no me hagas esperar 💦", "hazme gritar tu nombre ya mismo 🔥", "no te imaginas lo mojada que estoy 😍",
    "solo dime y me abro para ti 😈", "dime que me quieres ver ahora mismo 💋", "no tardes, mi culo ya te está esperando 🍑",
    "hazme tuya en este show 🔥", "quiero que seas el único que me vea acabar 💦"
]

def generar_respuesta_explicit(nombre: str = "papi", user_id: int | None = None) -> str:
    """Genera una respuesta extremadamente explícita adaptada al modelo seleccionado"""
    selected_model = user_models.get(user_id, "lil_eva") if user_id else "lil_eva"
    
    saludo = random.choice(SALUDOS_EXPLICIT)
    accion = random.choice(ACCIONES_EXPLICIT)
    sensacion = random.choice(SENSACIONES_EXPLICIT)
    propuesta = random.choice(PROPUESTAS_EXPLICIT)
    precio = random.choice(PRECIOS_EXPLICIT)
    cierre = random.choice(CIERRES_EXPLICIT)
    
    # Personalizar saludo con nombre del usuario
    saludo = saludo.replace("papi", nombre).replace("Mi dueño", f"Mi dueño {nombre}").replace("Mi rey", f"Mi rey {nombre}")
    
    # Adaptar el estilo según el modelo
    if selected_model == "lil_eva":
        # Estilo más tierno pero pervertido
        return f"{saludo} {accion}… {sensacion}… {propuesta} 😏🎀 lo hago por solo {precio} bebé 🔥 {cierre}"
    elif selected_model == "valentina_lux":
        # Estilo dominante y directo
        return f"{saludo} {accion}… {sensacion}… {propuesta} 😏👑 lo hago por {precio} mi esclavo 🔥 {cierre}"
    else:  # annie_paradisee
        # Estilo elegante pero pervertido
        return f"{saludo} {accion}… {sensacion}… {propuesta} 😏💎 una experiencia exclusiva por {precio} darling 🔥 {cierre}"

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
def respuestas_por_tipo(nombre: str, tipo: str, user_id: int | None = None) -> str:
    """Genera respuestas humanizadas según el tipo de mensaje y modelo seleccionado"""
    
    # Obtener datos del modelo actual
    selected_model = user_models.get(user_id, "lil_eva") if user_id else "lil_eva"
    model_data = MODELS[selected_model]
    model_name = model_data["name"]
    model_emoji = model_data["emoji"]
    
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
        if selected_model == "lil_eva":
            respuestas = [
                f"Ay {nombre} 😍 me encanta que quieras conocer a tu bebé mejor 💕🎀",
                f"Mmm papi 😘 qué lindo que preguntes por tu chiquita… cuéntame tú también de ti 😈👅",
                f"Claro que sí amor 💋 pregúntame lo que quieras, no tengo secretos contigo 🔥🍓",
                f"Me derrites cuando te interesas por mí {nombre} 😏 ¿qué quieres saber de tu Eva bebé? 💦🎀",
                f"Ufff papi 👅 me pones nerviosa cuando me preguntas cosas personales… pero me gusta mucho 😈💕"
            ]
        elif selected_model == "valentina_lux":
            respuestas = [
                f"Mmm {nombre} 🔥 me gusta cuando mis esclavos quieren conocer a su diosa 💋👑",
                f"Claro mi rey 😏 Valentina no tiene secretos para sus súbditos obedientes 🔥💄",
                f"Qué atrevido eres preguntándome eso {nombre} 👑 pero me gusta tu interés 💋🔥",
                f"Perfecto amor 😈 una diosa como yo merece que la conozcan bien 💄👠",
                f"Me fascina cuando mis hombres quieren saber más de su reina {nombre} 🔥👑"
            ]
        else:  # annie_paradisee
            respuestas = [
                f"Que refinado, {nombre} 💎 me encanta cuando un caballero se interesa por mi persona ✨",
                f"Exquisito darling 🖤 Annie siempre está dispuesta a una conversación intelectual 💋🥂",
                f"Qué elegante forma de acercarte {nombre} 💎 dime, ¿qué deseas conocer de mí? ✨👠",
                f"Me seduce tu curiosidad mi amor 🔮 una mujer sofisticada aprecia estas atenciones 💋💎",
                f"Delicioso {nombre} 🍾 hablemos mientras disfrutamos de este momento exclusivo ✨🖤"
            ]
    
    elif tipo == "sexual":
        # 30% de posibilidad de usar respuesta extremadamente explícita generada dinámicamente
        if random.random() < 0.3:
            return generar_respuesta_explicit(nombre, user_id)
        else:
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
    
    elif tipo == "recuerdo":
        respuestas = [
            f"Claro que sí {nombre} 😘 cómo podría olvidarte si me encantas 💋",
            f"Mmm bebé, claro que te recuerdo 😈 siempre pienso en ti…",
            f"Ay mi cielo 😍 imposible olvidarte, me calientas solo con aparecer 💦",
            f"Obvio que sí amor 😏 eres inolvidable para mí 💋",
            f"Mi rey 😘 cómo no recordarte… me dejas marcada cada vez que vienes 🔥",
            f"Por supuesto que te recuerdo {nombre} 😍 eres mi favorito, siempre te tengo presente 💕",
            f"Ay {nombre} 💋 qué pregunta tan linda… claro que me acuerdo de ti, mi amor 😘",
            f"Mmm 😈 cómo olvidarte papi… cada vez que no estás te extraño muchísimo 💦",
            f"Mi cielo 😏 imposible no recordarte… quedaste grabado en mi mente y mi cuerpo 🔥"
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
def get_janitor_ai_response(user_msg, user_id: int | None = None):
    if not JANITOR_AI_API_KEY or not janitor_headers:
        return None
    try:
        # Obtener personalidad del modelo seleccionado por el usuario
        personality = get_current_personality(user_id) if user_id else MODELS["lil_eva"]["personality"]
        
        payload = {
            "model": "janitor-llm",
            "messages": [
                {"role": "system", "content": personality},
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

def get_openai_response(user_msg, user_id: int | None = None):
    if not openai_client:
        return None
    try:
        # Obtener personalidad del modelo seleccionado por el usuario
        personality = get_current_personality(user_id) if user_id else MODELS["lil_eva"]["personality"]
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": personality},
                {"role": "user", "content": user_msg}
            ],
            max_tokens=250,
            temperature=1.1
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error OpenAI: {e}", exc_info=True)
        return None

def get_ai_response(user_msg, user_id: int | None = None):
    # Prioridad: Janitor -> OpenAI
    reply = get_janitor_ai_response(user_msg, user_id)
    if reply:
        return reply
    return get_openai_response(user_msg, user_id)

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
    user_id = message.from_user.id
    nombre = message.from_user.first_name or "amor"
    
    # Enviar saludo inicial
    bot.reply_to(message, respuesta_caliente_generica(nombre))
    
    # Mostrar inmediatamente el menú de selección de personajes
    markup = InlineKeyboardMarkup(row_width=1)
    
    for model_id, model_data in MODELS.items():
        button_text = f"{model_data['emoji']} {model_data['name']}"
        callback_data = f"select_{model_id}"
        markup.add(InlineKeyboardButton(button_text, callback_data=callback_data))
    
    # Mostrar modelo actual si ya está seleccionado
    current_model = user_models.get(user_id, "lil_eva")
    current_name = MODELS[current_model]["name"]
    current_emoji = MODELS[current_model]["emoji"]
    
    welcome_text = f"""
🔥 **SELECCIÓN DE MODELOS** 🔥

Actualmente estás chateando con: {current_emoji} **{current_name}**

🎯 **Elige tu modelo favorita:**

😈 **Lil Eva** - Joven traviesa de 19 años, dulce pero muy pervertida
🔥 **Valentina Lux** - Latina dominante de 25 años, tu diosa sexual  
💎 **Annie Paradise** - Elegante de 28 años, placer refinado y exclusivo

💋 Cada modelo tiene su propia personalidad única y estilo de conversación
"""
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=markup
    )

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

@bot.message_handler(commands=['extreme', 'explicit', 'morboso'])
@safe_handler
def respuesta_extreme(message):
    """Genera una respuesta extremadamente explícita y morbosa"""
    respuesta_extrema = generar_respuesta_explicit()
    bot.reply_to(message, respuesta_extrema)

@bot.message_handler(commands=['models', 'cambiar', 'seleccionar'])
@safe_handler
def seleccionar_modelo(message):
    """Muestra la selección de modelos disponibles"""
    user_id = message.from_user.id
    
    # Crear botones inline para selección de modelos
    
    markup = InlineKeyboardMarkup(row_width=1)
    
    for model_id, model_data in MODELS.items():
        button_text = f"{model_data['emoji']} {model_data['name']}"
        callback_data = f"select_{model_id}"
        markup.add(InlineKeyboardButton(button_text, callback_data=callback_data))
    
    # Mostrar modelo actual si ya está seleccionado
    current_model = user_models.get(user_id, "lil_eva")
    current_name = MODELS[current_model]["name"]
    current_emoji = MODELS[current_model]["emoji"]
    
    welcome_text = f"""
🔥 **SELECCIÓN DE MODELOS** 🔥

Actualmente estás chateando con: {current_emoji} **{current_name}**

🎯 **Elige tu modelo favorita:**

😈 **Lil Eva** - Joven traviesa de 19 años, dulce pero muy pervertida
🔥 **Valentina Lux** - Latina dominante de 25 años, tu diosa sexual  
💎 **Annie Paradise** - Elegante de 28 años, placer refinado y exclusivo

💋 Cada modelo tiene su propia personalidad única y estilo de conversación

👆 **Toca el botón de tu modelo favorita para empezar**
"""
    
    bot.reply_to(message, welcome_text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_'))
@safe_handler
def handle_model_selection(call):
    """Maneja la selección de modelo"""
    user_id = call.from_user.id
    model_id = call.data.replace('select_', '')
    
    # Guardar selección del usuario
    user_models[user_id] = model_id
    
    # Obtener datos del modelo seleccionado
    model_data = MODELS[model_id]
    greeting = model_data["greeting"]
    
    # Editar mensaje original
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"✅ **Modelo seleccionado:** {model_data['emoji']} {model_data['name']}\n\n{greeting}",
        parse_mode='Markdown'
    )
    
    bot.answer_callback_query(call.id, f"¡Ahora estás chateando con {model_data['name']}! 💋")

@bot.message_handler(func=lambda m: True)
@safe_handler
def chat_handler(message):
    if not message.text:
        return bot.reply_to(message, "Mándame texto, papi 😈")

    user_msg = message.text.strip()
    user_id = message.from_user.id
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
    respuesta_contextual = respuestas_por_tipo(nombre, tipo_mensaje, user_id)
    
    # 4) Si el mensaje es muy específico, intentar con IA para mayor personalización
    if tipo_mensaje in ["personal", "juego_rol"] or len(user_msg.split()) > 8:
        ai_reply = get_ai_response(user_msg, user_id)
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
