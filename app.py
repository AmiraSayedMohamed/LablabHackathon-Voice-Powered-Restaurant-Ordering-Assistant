
import streamlit as st
import requests
import json
import os
import io
import asyncio
import platform
import threading
import time
from livekit.api import AccessToken
from livekit.rtc import Room, LocalParticipant, RoomOptions
from dotenv import load_dotenv
import speech_recognition as sr
from pydub import AudioSegment
from audio_recorder_streamlit import audio_recorder

# --- Configuration ---
load_dotenv()  # Load environment variables from .env file

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_WS_URL = os.getenv("LIVEKIT_WS_URL")  # e.g., wss://your-project.livekit.cloud
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
LLAMA_MODEL = "llama3-8b-8192"

# --- Menu Data ---
menu = {
    "burgers": [
        {"id": "beef_burger", "name": "Classic Cheeseburger", "price": 12.99, "description": "Juicy beef patty with melted cheese, lettuce, tomato, and our special sauce", "upsell": ["coke", "fries_upgrade"], "dietary": []},
        {"id": "bbq_bacon_burger", "name": "BBQ Bacon Burger", "price": 14.99, "description": "Beef patty with crispy bacon, BBQ sauce, onion rings, and cheddar", "upsell": ["lemonade"], "dietary": []},
    ],
    "pizza": [
        {"id": "margherita_pizza", "name": "Margherita Pizza", "price": 16.99, "description": "Fresh mozzarella, basil, and tomato sauce on crispy thin crust", "dietary": ["vegetarian"]},
        {"id": "pepperoni_pizza", "name": "Pepperoni Pizza", "price": 17.99, "description": "Classic pepperoni with rich tomato sauce and mozzarella", "dietary": []},
    ],
    "appetizers": [
        {"id": "golden_fries", "name": "Golden Fries", "price": 4.00, "description": "Crispy golden french fries.", "dietary": ["vegetarian", "vegan"]},
        {"id": "chicken_wings", "name": "Spicy Chicken Wings", "price": 8.50, "description": "Crispy chicken wings tossed in spicy buffalo sauce.", "dietary": ["spicy"]},
    ],
    "salads": [
        {"id": "garden_salad", "name": "Garden Salad", "price": 5.50, "description": "Mixed greens, cherry tomatoes, cucumber, and vinaigrette.", "dietary": ["vegetarian", "vegan"]},
    ]
}

promotions = [
    {"name": "Combo Deal", "description": "Add any drink and a dessert to your main course for just $5 extra! 🎉", "items": ["main_courses", "drinks", "desserts"], "discount": 5.00}
]

flat_menu = {item_id: item for category_data in menu.values() for item_id, item in [(item["id"], item) for item in category_data]}

# --- LiveKit Token Generator ---
def generate_access_token(api_key, api_secret, room_name, identity):
    try:
        token = (
            AccessToken(api_key, api_secret)
            .with_identity(identity)
            .with_grants(
                {
                    "room_join": True,
                    "room": room_name,
                    "can_publish": True,
                    "can_subscribe": True,
                }
            )
        )
        return token.to_jwt()
    except Exception as e:
        st.error(f"Error generating token: {e}")
        return None

# --- LiveKit Setup ---
livekit_room = None

async def start_voice_session():
    global livekit_room
    livekit_room = Room()
    token = generate_access_token(LIVEKIT_API_KEY, LIVEKIT_API_SECRET, "foodie-room", "user1")
    if not token:
        st.error("Failed to generate authentication token.")
        return
    try:
        await livekit_room.connect(LIVEKIT_WS_URL, token)
        local_participant = livekit_room.local_participant
        await local_participant.publish_audio_track()
        livekit_room.on("track_published", handle_track)
        st.session_state.voice_session_started = True
        st.success("Voice session connected! Speak to order! 🗣️")
    except Exception as e:
        st.error(f"LiveKit connection failed: {e}")
        st.session_state.voice_session_started = False

def run_voice_session():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_voice_session())
    finally:
        loop.close()

def handle_track(track):
    if track.kind == "audio" and not st.session_state.is_processing_audio:
        st.session_state.is_processing_audio = True
        audio_data = track.receive()
        transcribed_text = recognize_speech(audio_data)
        process_user_input(transcribed_text)
        st.session_state.is_processing_audio = False

def recognize_speech(audio_data):
    r = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(audio_data)) as source:
        audio = r.record(source)
    try:
        return r.recognize_google(audio)
    except sr.UnknownValueError:
        return "Sorry, I couldn't understand the audio."
    except sr.RequestError as e:
        return f"Speech recognition error: {e}"

# --- MCP with Mock Implementation ---
class MCP:
    def __init__(self):
        self.agents = {}

class Agent:
    def __init__(self, name, mcp):
        self.name = name
        self.mcp = mcp
        self.mcp.agents[name] = self
        self.tasks = {}

    def task(self, func):
        self.tasks[func.__name__] = func
        return func

    def run_task(self, task_name, *args):
        try:
            return self.tasks[task_name](*args)
        except KeyError as e:
            st.error(f"Task not found: {e}")
            return None

mcp = MCP()
inventory_agent = Agent(name="InventoryAgent", mcp=mcp)

@inventory_agent.task
def check_availability(item_id):
    available_items = {"beef_burger": 10, "margherita_pizza": 5}
    return available_items.get(item_id, 0) > 0

# --- Fetch.ai Setup ---
class LedgerApi:
    def __init__(self, node):
        pass

class Entity:
    pass

ledger_api = LedgerApi('<your-fetch-ai-node>')
entity = Entity()
recommendation_agent = Agent(name="RecommendationAgent", mcp=mcp)

@recommendation_agent.task
def suggest_item(order):
    if "beef_burger" in [item["id"] for item in order]:
        return "golden_fries"
    return None

# --- Streamlit App Setup ---
st.set_page_config(layout="wide", page_title="Agentic Foodie 🍔")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pacifico&family=Inter:wght@400;600;700;800&display=swap');
    :root {
        --primary-hsl: 25, 95%, 55%;
        --primary-glow-hsl: 25, 90%, 65%;
        --secondary-hsl: 142, 76%, 36%;
        --accent-hsl: 270, 91%, 65%;
        --background-hsl: 25, 15%, 98%;
        --foreground-hsl: 25, 20%, 15%;
        --primary-rgb-r: 247; --primary-rgb-g: 104; --primary-rgb-b: 25;
        --secondary-rgb-r: 29; --secondary-rgb-g: 191; --secondary-rgb-b: 84;
        --accent-rgb-r: 153; --accent-rgb-g: 25; --accent-rgb-b: 247;
        --foreground-rgb-r: 64; --foreground-rgb-g: 54; --foreground-rgb-b: 46;
    }
    .stApp { font-family: 'Inter', sans-serif; background-color: hsl(var(--background-hsl)); color: hsl(var(--foreground-hsl)); }
    .hero-section { position: relative; height: 300px; background: linear-gradient(135deg, hsl(var(--primary-hsl)), hsl(var(--accent-hsl))), url('https://content.streamlit.io/v3/uploaded:image_d9d45d.jpg-28e75a55-fe11-4c1a-9b91-11f8fe316e18'); background-size: cover; background-position: center; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: white; border-radius: 1.5rem; box-shadow: 0 10px 20px rgba(var(--primary-rgb-r), var(--primary-rgb-g), var(--primary-rgb-b), 0.3); margin-bottom: 2rem; overflow: hidden; }
    .hero-section::before { content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(135deg, rgba(var(--primary-rgb-r), var(--primary-rgb-g), var(--primary-rgb-b), 0.7), rgba(var(--accent-rgb-r), var(--accent-rgb-g), var(--accent-rgb-b), 0.7)); z-index: 1; }
    .hero-content { position: relative; z-index: 2; padding: 1rem; }
    .hero-title { font-family: 'Pacifico', cursive; font-size: 5rem; color: white; text-shadow: 3px 3px 6px rgba(0,0,0,0.5); margin-bottom: 0.5rem; line-height: 1; }
    .hero-subtitle { font-size: 1.8rem; color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); margin-top: 0; margin-bottom: 1rem; }
    .llama-badge { background-color: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.5); padding: 0.5rem 1rem; border-radius: 9999px; font-size: 0.9rem; font-weight: bold; color: white; text-shadow: 1px 1px 2px rgba(0,0,0,0.2); }
    h2.section-title, h3.section-subtitle, .menu-item-category { color: hsl(var(--foreground-hsl)); text-shadow: none; }
    p, span, div, label { color: hsl(var(--foreground-hsl)); text-shadow: none; }
    .stFileUploader label, .stTextInput label, .place-order-button, .audio-recorder-container button, .stFileUploader div[data-testid="stFileUploaderDropzone"], .stFileUploader div[data-testid="stFileUploaderFileName"], .stFileUploader button, .chat-bubble { color: white; text-shadow: 1px 1px 2px rgba(0,0,0,0.2); }
    .stTextInput input { color: hsl(var(--foreground-hsl)) !important; background-color: #ffffff; }
    .bouncing-dots { display: flex; justify-content: center; align-items: center; margin-top: 10px; }
    .dot { width: 10px; height: 10px; border-radius: 50%; background-color: hsl(var(--secondary-hsl)); margin: 0 5px; animation: bounce 1s infinite ease-in-out; }
    .dot:nth-child(1) { animation-delay: 0s; }
    .dot:nth-child(2) { animation-delay: 0.1s; }
    .dot:nth-child(3) { animation-delay: 0.2s; }
    @keyframes bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
    .chat-header { display: flex; align-items: center; justify-content: flex-start; margin: 0 !important; padding: 0 !important; }
    .chat-history-container { height: 3px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; margin-top: -10px !important; padding-top: 0 !important; }
    .chat-bubble { max-width: 75%; padding: 10px 15px; border-radius: 1rem; word-wrap: break-word; width: fit-content; box-sizing: border-box; }
    .user-bubble { background: linear-gradient(90deg, hsl(var(--primary-hsl)), hsl(var(--primary-glow-hsl))); color: white; align-self: flex-end; border-bottom-right-radius: 0.25rem; }
    .agent-bubble { background: linear-gradient(90deg, hsl(var(--secondary-hsl)), hsl(var(--secondary-hsl), 90%)); color: white; align-self: flex-start; border-bottom-left-radius: 0.25rem; }
    .bot-avatar { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(45deg, hsl(var(--accent-hsl)), hsl(var(--accent-hsl), 70%)); display: flex; justify-content: center; align-items: center; font-size: 1.5rem; margin-right: 10px; flex-shrink: 0; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
    .chat-row { display: flex; align-items: flex-start; gap: 10px; }
    .chat-row.user { justify-content: flex-end; }
    .chat-row.agent { justify-content: flex-start; }
    .suggestion-buttons-container { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
    .suggestion-button button { background-color: rgba(var(--primary-rgb-r), var(--primary-rgb-g), var(--primary-rgb-b), 0.1); color: hsl(var(--foreground-hsl)); border: 1px solid rgba(var(--primary-rgb-r), var(--primary-rgb-g), var(--primary-rgb-b), 0.3); border-radius: 9999px; padding: 0.5rem 1rem; font-size: 0.9rem; cursor: pointer; transition: all 0.2s ease; }
    .suggestion-button button:hover { background-color: rgba(var(--primary-rgb-r), var(--primary-rgb-g), var(--primary-rgb-b), 0.2); transform: translateY(-2px); box-shadow: 0 2px 5px rgba(var(--primary-rgb-r), var(--primary-rgb-g), var(--primary-rgb-b), 0.2); }
    div[data-testid="stAudioRecorder"] { border: none !important; box-shadow: none !important; background-color: transparent !important; padding: 0 !important; margin: 0 !important; display: flex !important; justify-content: center !important; width: 100 !important; }
    div[data-testid="stAudioRecorder"] button { background-color: #2ECC71 !important; background: linear-gradient(135deg, #2ECC71, #27AE60) !important; color: white !important; border-radius: 0.75rem !important; padding: 0.8rem 1.5rem !important; border: none !important; cursor: pointer !important; width: 100% !important; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1) !important; transition: all 0.3s ease !important; }
    div[data-testid="stAudioRecorder"] button:hover { background: linear-gradient(135deg, #27AE60, #219653) !important; transform: translateY(-2px) !important; box-shadow: 0 6px 15px rgba(0, 0, 0, 0.2) !important; }
    button { background: linear-gradient(135deg, #FF8C00, #FF4500) !important; color: white !important; border-radius: 0.75rem !important; padding: 0.8rem 1.5rem !important; border: none !important; cursor: pointer !important; width: 100% !important; box-shadow: none !important; outline: none !important; transition: all 0.3s ease !important; }
    button:hover { background: linear-gradient(135deg, #FF4500, #FF8C00) !important; transform: translateY(-2px) !important; box-shadow: none !important; }
    button:focus { outline: none !important; box-shadow: none !important; }
    .menu-item-card button { transition: all 0.2s ease !important; }
    .menu-item-card button:hover { transform: translateY(-2px) !important; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1) !important; }
    .menu-item-card button:focus { outline: none !important; box-shadow: 0 0 0 3px rgba(46, 204, 113, 0.5) !important; transform: translateY(-1px) !important; }
    .menu-section-title { text-align: center; margin-bottom: 0.5rem; }
    .menu-section-title h2 { font-size: 2.5rem; font-weight: 800; color: hsl(var(--foreground-hsl)); }
    .menu-section-subtitle { text-align: center; font-size: 1.1rem; color: hsl(var(--foreground-hsl), 70%); margin-bottom: 2rem; }
    .menu-item-category { font-size: 1.6rem; font-weight: bold; margin-top: 1.5rem; margin-bottom: 0.8rem; color: hsl(var(--foreground-hsl)); text-shadow: none; }
    .menu-item-card { padding: 1rem; margin-bottom: 0.8rem; display: flex; flex-direction: column; align-items: flex-start; gap: 0.5rem; transition: transform 0.2s ease; }
    .menu-item-header { display: flex; align-items: center; gap: 1rem; width: 100%; }
    .menu-item-image { width: 80px; height: 80px; border-radius: 50%; border: 3px solid hsl(var(--primary-glow-hsl)); object-fit: cover; flex-shrink: 0; }
    .menu-item-details { flex-grow: 1; }
    .menu-item-name { font-weight: bold; font-size: 1.1rem; color: hsl(var(--foreground-hsl)); }
    .menu-item-description { font-size: 0.9rem; color: hsl(var(--foreground-hsl), 80%); margin-top: 0.2rem; }
    .menu-item-price { font-weight: bold; font-size: 1.2rem; color: hsl(var(--primary-hsl)); margin-left: auto; }
    .dietary-badge { font-size: 0.75rem; padding: 0.2rem 0.6rem; border-radius: 9999px; font-weight: 600; margin-right: 5px; display: inline-block; margin-top: 5px; color: white; }
    .dietary-vegetarian { background-color: hsl(var(--secondary-hsl)); }
    .dietary-spicy { background-color: hsl(0, 70%, 50%); color: white; }
    .order-summary-title { text-align: center; margin-bottom: 0.5rem; }
    .order-summary-title h2 { font-size: 2.5rem; font-weight: 800; color: hsl(var(--foreground-hsl)); }
    .empty-cart-message { text-align: center; padding: 2rem; color: hsl(var(--foreground-hsl), 70%); font-style: italic; }
    .empty-cart-icon { font-size: 3rem; color: hsl(var(--foreground-hsl), 50%); margin-bottom: 1rem; }
    .order-item-row { display: flex; align-items: center; padding: 0.5rem 0; border-bottom: 1px dashed rgba(var(--foreground-rgb-r), var(--foreground-rgb-g), var(--foreground-rgb-b), 0.1); }
    .order-item-row:last-child { border-bottom: none; }
    .order-item-name { flex-grow: 1; color: hsl(var(--foreground-hsl)); font-weight: 600; }
    .qty-controls { display: flex; align-items: center; gap: 5px; }
    .qty-button button { background-color: rgba(var(--secondary-rgb-r), var(--secondary-rgb-g), var(--secondary-rgb-b), 0.1); color: hsl(var(--secondary-hsl)); border: 1px solid hsl(var(--secondary-hsl)); border-radius: 0.5rem; padding: 0.2rem 0.6rem; font-size: 1rem; cursor: pointer; transition: background-color 0.2s ease; }
    .qty-button button:hover { background-color: rgba(var(--secondary-rgb-r), var(--secondary-rgb-g), var(--secondary-rgb-b), 0.2); }
    .qty-display { width: 30px; text-align: center; color: hsl(var(--foreground-hsl)); font-weight: bold; }
    .remove-button button { background-color: transparent; border: none; color: hsl(0, 70%, 50%); font-size: 1.2rem; cursor: pointer; transition: transform 0.2s ease; }
    .remove-button button:hover { transform: scale(1.2); }
    .order-item-price { color: hsl(var(--primary-hsl)); font-weight: bold; text-align: right; width: 80px; }
    .order-summary-totals { margin-top: 1.5rem; padding-top: 1rem; border-top: 2px solid rgba(var(--foreground-rgb-r), var(--foreground-rgb-g), var(--foreground-rgb-b), 0.1); }
    .total-row { display: flex; justify-content: space-between; font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; color: hsl(var(--foreground-hsl)); }
    .total-row.grand-total { font-size: 1.5rem; font-weight: bold; color: hsl(var(--primary-hsl)); }
    .place-order-button .stButton>button { background: linear-gradient(90deg, hsl(var(--primary-hsl)), hsl(var(--primary-glow-hsl))); color: white; font-size: 1.2rem; padding: 1rem 2rem; border-radius: 9999px; box-shadow: 0 5px 15px rgba(var(--primary-rgb-r), var(--primary-rgb-g), var(--primary-rgb-b), 0.3); transition: all 0.3s ease; width: 100%; margin-top: 1.5rem; }
    .place-order-button .stButton>button:hover { transform: scale(1.03); box-shadow: 0 8px 25px rgba(var(--primary-rgb-r), var(--primary-rgb-g), var(--primary-rgb-b), 0.5); }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; padding-left: 2rem; padding-right: 2rem; }
    @media (max-width: 768px) { .hero-title { font-size: 3.5rem; } .hero-subtitle { font-size: 1.2rem; } .stApp .block-container { padding-left: 1rem; padding-right: 1rem; } .chat-history-container { height: auto; min-height: 300px; margin-bottom: 1.5rem; } .st-emotion-cache-10trblm { text-align: center; margin-bottom: 1rem; } }
    .stToast { background-color: #2ecc71 !important; color: white !important; font-weight: bold !important; border-radius: 12px !important; box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown(f"""
    <div class="hero-section" style="background: linear-gradient(135deg, hsl(var(--primary-hsl)), hsl(var(--accent-hsl))), url('cover.png'); background-size: cover; background-position: center;">
        <div class="hero-content">
            <h1 class="hero-title">Agentic Foodie</h1>
            <p class="hero-subtitle">Voice-Powered Restaurant Ordering Assistant</p>
            <span class="llama-badge">Powered by Llama AI 🤖</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
    initial_agent_message = "Hello! 👋 Welcome to Agentic Foodie! I'm your voice-powered assistant ready to help you order from our delicious menu 🍽️ and suggest great additions. How can I help you today? 🗣️"
    st.session_state.conversation_history.append({"role": "agent", "text": initial_agent_message})

if 'current_order' not in st.session_state:
    st.session_state.current_order = []
if 'is_processing_audio' not in st.session_state:
    st.session_state.is_processing_audio = False
if 'is_llm_thinking' not in st.session_state:
    st.session_state.is_llm_thinking = False
if 'voice_session_started' not in st.session_state:
    st.session_state.voice_session_started = False
if 'last_request_time' not in st.session_state:
    st.session_state.last_request_time = 0
if 'rate_limit_warning' not in st.session_state:
    st.session_state.rate_limit_warning = False

# --- Helper Functions ---
def add_message_to_chat(text, sender):
    st.session_state.conversation_history.append({"role": sender, "text": text})

def get_order_total():
    return sum(item["price"] * item["quantity"] for item in st.session_state.current_order)

def update_order(item_id, quantity):
    if flat_menu.get(item_id):
        existing_order_item = next((item for item in st.session_state.current_order if item["id"] == item_id), None)
        if existing_order_item:
            existing_order_item["quantity"] += quantity
            if existing_order_item["quantity"] <= 0:
                st.session_state.current_order = [item for item in st.session_state.current_order if item["id"] != item_id]
        else:
            if quantity > 0:
                st.session_state.current_order.append({"id": flat_menu[item_id]["id"], "name": flat_menu[item_id]["name"], "price": flat_menu[item_id]["price"], "quantity": quantity})
        return True
    return False

def add_item_to_order_from_button(item_id):
    if update_order(item_id, 1):
        item_name = flat_menu[item_id]['name']
        st.toast(f"Added {item_name} to your order! ✅", icon="✅")
    else:
        st.toast(f"Could not add {item_id} to your order.", icon="❌")
    st.rerun()

def remove_order_item(item_id_to_remove):
    st.session_state.current_order = [item for item in st.session_state.current_order if item["id"] != item_id_to_remove]
    st.toast(f"Item removed from order. 🗑️", icon="🗑️")
    st.rerun()

def set_order_item_quantity(item_id_to_update, new_quantity):
    if new_quantity <= 0:
        remove_order_item(item_id_to_update)
    else:
        for item in st.session_state.current_order:
            if item["id"] == item_id_to_update:
                item["quantity"] = new_quantity
                st.toast(f"Quantity for {item['name']} updated to {new_quantity}. 👍", icon="👍")
                break
    st.rerun()

def process_user_input(user_input_text):
    if user_input_text:
        add_message_to_chat(user_input_text, "user")
        st.session_state.is_llm_thinking = True
        llm_result = get_llm_response(user_input_text, st.session_state.current_order, st.session_state.conversation_history)
        agent_response = llm_result["response_text"]
        add_message_to_chat(agent_response, "agent")
        speak_text(agent_response)
        st.session_state.is_llm_thinking = False
        st.rerun()

def speak_text(text):
    # Fallback to chat display since Groq does not support text-to-speech
    add_message_to_chat("Audio output is currently unavailable. Here's my response: " + text, "agent")

def get_llm_response(user_message: str, current_order_state: list, conv_history: list):
    if not GROQ_API_KEY:
        return {"intent": "error", "item_id": None, "quantity": None, "response_text": "I'm sorry, my AI capabilities are not configured. Please contact support. 😔"}

    # Rate limiting: Ensure minimum time between requests (e.g., 2 seconds)
    current_time = time.time()
    time_since_last = current_time - st.session_state.last_request_time
    min_interval = 2  # Minimum seconds between requests
    if time_since_last < min_interval:
        time.sleep(min_interval - time_since_last)

    messages = [{
        "role": "system",
        "content": f"""
        You are a helpful and friendly restaurant ordering assistant named Agentic Foodie.
        Your goal is to take food orders, answer questions about the menu, and intelligently
        recommend additional items, upgrades, or promotions to maximize the order value and customer satisfaction.
        
        Current Menu (JSON): {json.dumps(menu)}
        Current Promotions (JSON): {json.dumps(promotions)}
        Current Order (JSON): {json.dumps(current_order_state)}
        
        Based on the user's input and the current conversation context, you MUST respond with a JSON object.
        This JSON object should contain:
        1. "intent": A string indicating the user's primary intent.
           Possible values: "order", "query_menu", "confirm", "cancel", "greeting", "farewell", "other", "thank_you".
        2. "item_id": The 'id' of the menu item if the intent is "order" or "query_menu", otherwise null.
        3. "quantity": An integer representing the quantity if the intent is "order", otherwise null.
        4. "response_text": A natural language, conversational response for the user, including relevant emojis.
           Ensure this text is engaging and directly addresses the user's input.

        **STRICT JSON OUTPUT REQUIREMENT:**
        Your entire response MUST be a valid JSON object and contain ONLY the JSON. Do NOT include any other text, markdown, or explanations outside the JSON.
        Example: {{"intent": "order", "item_id": "beef_burger", "quantity": 1, "response_text": "Great choice! Adding a Classic Beef Burger 🍔 to your order. Would you like some golden fries with that? 🍟"}}

        **Recommendation Logic for "response_text":**
        - After an item is ordered, suggest relevant upsells from its 'upsell' array (e.g., "coke", "fries_upgrade").
        - If a main course is ordered and no drink/dessert, suggest the "Combo Deal".
        - If multiple items are in the cart, suggest a dessert.
        - Be friendly, conversational, and use emojis.
        - If the user asks about something not on the menu, politely state it's not available.
        - If the user says "hello" or a greeting, respond with a friendly greeting.
        - If the user says "thank you", respond appropriately.
        """
    }]
    
    for chat_turn in conv_history:
        role = "user" if chat_turn["role"] == "user" else "assistant"
        messages.append({"role": role, "content": chat_turn["text"]})
    
    messages.append({"role": "user", "content": user_message})

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": LLAMA_MODEL, "messages": messages, "temperature": 0.7, "max_tokens": 250, "response_format": {"type": "json_object"}}

    # Exponential backoff for 429 errors
    max_retries = 3
    base_delay = 1  # Initial delay in seconds
    for attempt in range(max_retries):
        try:
            response = requests.post(GROQ_API_URL, headers=headers, json=payload)
            st.session_state.last_request_time = time.time()  # Update last request time
            response.raise_for_status()

            # Check rate limit headers
            remaining_requests = response.headers.get("x-ratelimit-remaining-requests")
            remaining_tokens = response.headers.get("x-ratelimit-remaining-tokens")
            if remaining_requests and int(remaining_requests) < 10:
                st.session_state.rate_limit_warning = True
                st.warning("Approaching rate limit. Please slow down your requests.")

            llm_raw_response_content = response.json()["choices"][0]["message"]["content"]
            llm_parsed_response = json.loads(llm_raw_response_content)
            intent = llm_parsed_response.get("intent", "other")
            item_id = llm_parsed_response.get("item_id")
            quantity = llm_parsed_response.get("quantity", 1)
            agent_response_text = llm_parsed_response.get("response_text", "I'm not sure how to respond to that. 🤔")

            if intent == 'order' and item_id:
                if not check_availability(item_id):
                    agent_response_text = f"Sorry, {flat_menu.get(item_id, {}).get('name', item_id)} is out of stock. 🛑"
                elif update_order(item_id, quantity):
                    suggested_item = recommendation_agent.run_task("suggest_item", current_order_state)
                    if suggested_item:
                        agent_response_text += f" How about some {flat_menu[suggested_item]['name']} with that? 🍟"
            elif intent == 'thank_you':
                agent_response_text = "You're most welcome! Is there anything else I can assist you with? 😊"
            elif intent == 'greeting':
                agent_response_text = "Hello there! How can I help you with your order today? 🌟"
            elif intent == 'farewell':
                agent_response_text = "Goodbye! Hope to serve you again soon! 👋"

            return {"intent": intent, "item_id": item_id, "quantity": quantity, "response_text": agent_response_text}

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                retry_after = response.headers.get("retry-after", base_delay * (2 ** attempt))
                try:
                    retry_after = float(retry_after)
                except ValueError:
                    retry_after = base_delay * (2 ** attempt)
                st.warning(f"Rate limit exceeded. Retrying in {retry_after:.2f} seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_after)
                continue
            else:
                st.error(f"Error with LLM: {e}")
                return {"intent": "error", "item_id": None, "quantity": None, "response_text": "Something went wrong. Please try again. 😕"}
        except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
            st.error(f"Error with LLM: {e}")
            return {"intent": "error", "item_id": None, "quantity": None, "response_text": "Something went wrong. Please try again. 😕"}

    # Max retries exceeded
    st.error("Max retries exceeded due to rate limits. Please wait a moment and try again.")
    return {"intent": "error", "item_id": None, "quantity": None, "response_text": "I'm sorry, we're experiencing high demand. Please wait a moment and try again. 😔"}

# --- Streamlit UI Layout ---
with st.container():
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        st.markdown('<h3 class="section-subtitle">Voice Ordering Assistant</h3>', unsafe_allow_html=True)
        st.markdown('<p style="font-size: 0.9rem; margin-bottom: 1rem;">Speak your order or upload an audio file</p>', unsafe_allow_html=True)
        
        if not st.session_state.voice_session_started:
            st.button("Connect Voice 🎙️", on_click=lambda: threading.Thread(target=run_voice_session).start())
        if st.session_state.voice_session_started:
            st.write("Voice session active. Speak to order! 🗣️")
        
        audio_cols = st.columns(2)
        with audio_cols[0]:
            audio_bytes = audio_recorder(text="Start Recording 🎙️", recording_color="#27AE60", neutral_color="#2ECC71", icon_size="2x", key="audio_recorder_start", pause_threshold=3.0, sample_rate=44100)
        with audio_cols[1]:
            st.markdown('<button style="background: linear-gradient(135deg, #FF8C00, #FF4500); color: white; border-radius: 0.75rem; padding: 0.8rem 1.5rem; border: none; cursor: pointer; width: 100%; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1); transition: all 0.3s ease;" onclick="document.getElementById(\'file_uploader\').click()">Upload Audio ⬆️</button>', unsafe_allow_html=True)

        uploaded_audio_file = st.file_uploader("Upload an audio file (WAV, MP3, M4A) 🎵", type=["wav", "mp3", "m4a"], key="file_uploader", label_visibility="collapsed")

        if audio_bytes and not st.session_state.is_processing_audio:
            st.session_state.is_processing_audio = True
            st.audio(audio_bytes, format="audio/wav")
            st.markdown("<p style='text-align: center;'>Converting audio to text...🎧</p>", unsafe_allow_html=True)
            try:
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav")
                wav_file_path = "temp_audio_recorded.wav"
                audio_segment.export(wav_file_path, format="wav")
                r = sr.Recognizer()
                with sr.AudioFile(wav_file_path) as source:
                    audio_data = r.record(source)
                transcribed_text = r.recognize_google(audio_data)
                st.success(f"Transcribed: \"{transcribed_text}\" ✅", icon="✅")
                process_user_input(transcribed_text)
                os.remove(wav_file_path)
            except Exception as e:
                st.error(f"Audio processing error: {e} ⚠️")
            finally:
                st.session_state.is_processing_audio = False
                st.rerun()

        if uploaded_audio_file is not None and not st.session_state.is_processing_audio:
            st.session_state.is_processing_audio = True
            st.audio(uploaded_audio_file, format=uploaded_audio_file.type)
            st.markdown("<p style='text-align: center;'>Converting uploaded audio to text...🎧</p>", unsafe_allow_html=True)
            try:
                audio_segment = AudioSegment.from_file(uploaded_audio_file)
                wav_file_path = "temp_audio_uploaded.wav"
                audio_segment.export(wav_file_path, format="wav")
                r = sr.Recognizer()
                with sr.AudioFile(wav_file_path) as source:
                    audio_data = r.record(source)
                transcribed_text = r.recognize_google(audio_data)
                st.success(f"Transcribed: \"{transcribed_text}\" ✅", icon="✅")
                process_user_input(transcribed_text)
                os.remove(wav_file_path)
            except Exception as e:
                st.error(f"Audio processing error: {e} ⚠️")
            finally:
                st.session_state.is_processing_audio = False
                st.rerun()

        st.markdown('<div class="chat-header"><div class="bot-avatar">🤖</div><h3 class="section-subtitle">Agentic Foodie Assistant</h3><span style="background-color: hsl(var(--secondary-hsl)); color: white; padding: 0.2rem 0.6rem; border-radius: 9999px; font-size: 0.8rem; margin-left: 10px;">✨ Smart Ordering</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="chat-history-container">', unsafe_allow_html=True)
        for chat in st.session_state.conversation_history:
            if chat["role"] == "user":
                st.markdown(f'<div class="chat-row user"><div class="chat-bubble user-bubble">{chat["text"]}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-row agent"><div class="bot-avatar">🤖</div><div class="chat-bubble agent-bubble">{chat["text"]}</div></div>', unsafe_allow_html=True)
        if st.session_state.is_llm_thinking:
            st.markdown("""
                <div class="chat-row agent">
                    <div class="bot-avatar">🤖</div>
                    <div class="chat-bubble agent-bubble">
                        <div class="bouncing-dots">
                            <div class="dot"></div>
                            <div class="dot"></div>
                            <div class="dot"></div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        user_input = st.chat_input("Type your order or question here... ✍️", on_submit=lambda: process_user_input(st.session_state.chat_input_key), key="chat_input_key")
        st.markdown('<div class="suggestion-buttons-container">', unsafe_allow_html=True)
        col_sug1, col_sug2, col_sug3 = st.columns(3)
        with col_sug1:
            st.button("Menu? 📋", key="suggest_menu", on_click=process_user_input, args=("What's on the menu?",), use_container_width=True)
        with col_sug2:
            st.button("Promotions? 🎉", key="suggest_promo", on_click=process_user_input, args=("Are there any promotions?",), use_container_width=True)
        with col_sug3:
            st.button("Recommend! ✨", key="suggest_recommend", on_click=process_user_input, args=("Can you recommend something?",), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="menu-section-title"><h2>Our Menu</h2></div>', unsafe_allow_html=True)
        st.markdown('<p class="menu-section-subtitle">Delicious food, made fresh daily</p>', unsafe_allow_html=True)
        for category, items in menu.items():
            st.markdown(f'<h3 class="menu-item-category">{category.replace("_", " ").title()}</h3>', unsafe_allow_html=True)
            for item in items:
                dietary_badges = ""
                if item.get("dietary"):
                    for diet in item["dietary"]:
                        if diet == "vegetarian":
                            dietary_badges += '<span class="dietary-badge dietary-vegetarian">🌱 Veg</span>'
                        elif diet == "vegan":
                            dietary_badges += '<span class="dietary-badge dietary-vegan">🌿 Vegan</span>'
                        elif diet == "spicy":
                            dietary_badges += '<span class="dietary-badge dietary-spicy">🌶️ Spicy</span>'
                st.markdown(f"""
                    <div class="menu-item-card">
                        <div class="menu-item-header">
                            <img src="{item.get('image', 'https://placehold.co/100x100/CCCCCC/333333?text=Food')}" class="menu-item-image" alt="{item['name']}">
                            <div class="menu-item-details">
                                <p class="menu-item-name">{item['name']}</p>
                                <p class="menu-item-description">{item['description']}</p>
                                <div>{dietary_badges}</div>
                            </div>
                            <span class="menu-item-price">${item['price']:.2f}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                st.button("➕ Add to Order", key=f"add_to_order_{item['id']}", on_click=add_item_to_order_from_button, args=(item['id'],), help=f"Add {item['name']} to your order", use_container_width=True)
                st.markdown("<br>", unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="order-summary-title"><h2>Your Order</h2></div>', unsafe_allow_html=True)
        if not st.session_state.current_order:
            st.markdown("""
                <div class="empty-cart-message">
                    <p class="empty-cart-icon">🛒</p>
                    <p>Your cart is empty. Add some delicious items! 😋</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            for i, item in enumerate(st.session_state.current_order):
                st.markdown(f"""
                    <div class="order-item-row">
                        <div class="order-item-name">{item['name']}</div>
                        <div class="qty-controls">
                            <div class="qty-button">{st.button("−", key=f"minus_qty_{item['id']}_{i}", on_click=set_order_item_quantity, args=(item['id'], item['quantity'] - 1), help="Decrease quantity")}</div>
                            <div class="qty-display">{item['quantity']}</div>
                            <div class="qty-button">{st.button("+", key=f"plus_qty_{item['id']}_{i}", on_click=set_order_item_quantity, args=(item['id'], item['quantity'] + 1), help="Increase quantity")}</div>
                        </div>
                        <div class="order-item-price">${(item['price'] * item['quantity']):.2f}</div>
                        <div class="remove-button">{st.button("🗑️", key=f"remove_item_{item['id']}_{i}", on_click=remove_order_item, args=(item['id'],), help=f"Remove {item['name']}", use_container_width=False)}</div>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown('<div class="order-summary-totals">', unsafe_allow_html=True)
        subtotal = get_order_total()
        tax_rate = 0.08
        tax = subtotal * tax_rate
        grand_total = subtotal + tax

        st.markdown(f"""
            <div class="total-row">
                <span>Subtotal:</span>
                <span>${subtotal:.2f}</span>
            </div>
            <div class="total-row">
                <span>Tax (8%):</span>
                <span>${tax:.2f}</span>
            </div>
            <div class="total-row grand-total">
                <span>Total:</span>
                <span>${grand_total:.2f}</span>
            </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.button("Place Order 🎉", type="primary", disabled=not st.session_state.current_order, key="place_order_btn", use_container_width=True)
        if st.session_state.place_order_btn:
            final_order_str = ", ".join([f"{item['quantity']} x {item['name']}" for item in st.session_state.current_order])
            total = grand_total
            confirmation_message = f"Thank you for your order! You've ordered: {final_order_str}. Your total is ${total:.2f}. Your order has been sent to the kitchen. Enjoy your meal! 🥳"
            st.toast(confirmation_message, icon="✅")
            add_message_to_chat(confirmation_message, "agent")
            speak_text(confirmation_message)
            st.session_state.current_order = []
            st.rerun()

# --- Platform Check for Async Execution ---
if platform.system() == "Emscripten":
    asyncio.ensure_future(start_voice_session())
else:
    if __name__ == "__main__":
        threading.Thread(target=run_voice_session).start()
