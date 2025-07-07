# Agentic Foodie 🍔
![Alt text]([https://example.com/image.jpg](https://github.com/AmiraSayedMohamed/LablabHackathon-Voice-Powered-Restaurant-Ordering-Assistant/blob/master/appImage.jpg))

A voice-powered restaurant ordering web application built with Streamlit, leveraging AI and real-time audio processing to provide a seamless and interactive dining experience. Users can place orders via voice or text, explore a dynamic menu, and receive personalized recommendations powered by Groq's Llama AI model.

## Features

- **Voice-Activated Ordering**: Speak orders using a microphone or upload audio files (WAV, MP3, M4A), transcribed via Google's Speech-to-Text API.
- **Interactive Menu**: Browse a visually appealing menu with categories (burgers, pizza, appetizers, salads), including prices, descriptions, and dietary badges (vegetarian, vegan, spicy).
- **AI Recommendations**: Groq's Llama AI suggests upsells, promotions (e.g., Combo Deal), and complementary items based on user inputs and order history.
- **Real-Time Order Management**: View and modify the cart, adjust quantities, and see a detailed summary with subtotal, tax, and total.
- **Conversational Interface**: Engage with a friendly AI assistant through a chat interface, displaying conversation history with styled user and agent messages.
- **LiveKit Integration**: Real-time audio communication for voice-based ordering using LiveKit's WebRTC capabilities.

## Technologies Used

- **Python 3.8+**
- **Streamlit**: Web interface for the application.
- **Groq API (Llama AI)**: Natural language processing for intent recognition and recommendations.
- **LiveKit**: Real-time audio communication for voice ordering.
- **SpeechRecognition**: Converts audio inputs to text.
- **Pydub**: Handles audio file processing.
- **Python-dotenv**: Manages environment variables.

## Prerequisites

- Python 3.8 or higher
- A Groq API key (sign up at [Groq](https://groq.com/))
- A LiveKit account with API key, secret, and WebSocket URL (sign up at [LiveKit](https://livekit.io/))
- Git installed for version control
- A GitHub account for repository hosting
- A Streamlit Cloud account for deployment

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/agentic-foodie.git
   cd agentic-foodie
   ```

2. **Set Up a Virtual Environment (recommended):
bash**
 ```bash
   python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
3. **Install Dependencies: Create a requirements.txt file with the following content:**
    ```bash
    streamlit==1.46.1
   requests==2.32.3
   python-dotenv==1.1.0
   speechrecognition==3.14.3
   pydub==0.25.1
   audio-recorder-streamlit==0.0.10
   livekit-api==1.0.3
   livekit==1.0.11
   ```
4. **Configure Environment Variables: Create a .env file in the project root with the following:**
    ```bash
    GROQ_API_KEY=your_groq_api_key
   LIVEKIT_API_KEY=your_livekit_api_key
   LIVEKIT_API_SECRET=your_livekit_api_secret
   LIVEKIT_WS_URL=your_livekit_websocket_url
     ```
-------
# Running Locally
1. Start the Streamlit app:
    ```bash
    streamlit run app.py
    ```
2. Open your browser and navigate to http://localhost:8501 to interact with the application.
---------
# Deployment to Streamlit Cloud
1.Push to GitHub:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/your-username/agentic-foodie.git
git push -u origin main
  ```
2. Deploy on Streamlit Cloud:
   - Log in to Streamlit Cloud.
   - Create a new app and link it to your GitHub repository.
   - Specify the main script (e.g., app.py) in the app settings.
   - Add the following environment variables in Streamlit Cloud’s settings:
    -  GROQ_API_KEY
    - LIVEKIT_API_KEY
    -  LIVEKIT_API_SECRET
    - LIVEKIT_WS_URL
  
Deploy the app and access it via the provided URL.
