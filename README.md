# Warm Transfer System

A comprehensive solution for seamless call handoff between agents and external phone numbers, featuring real-time audio, AI-powered summaries, and an intuitive web interface.

## 🚀 Features

- **Warm Transfer**: Seamless call handoff between agents
- **Phone Integration**: Transfer calls to external numbers via Twilio
- **AI-Powered Summaries**: Automatic call summarization using Groq/OpenAI
- **Real-time Audio**: Powered by LiveKit for high-quality voice communication
- **Modern Web UI**: Responsive design built with Next.js and TailwindCSS
- **Call Recording**: Automatic transcript generation and storage

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI
- **Real-time Communication**: LiveKit
- **Database**: SQLite
- **AI/ML**: Groq/OpenAI for summarization
- **Telephony**: Twilio for phone integration

### Frontend
- **Framework**: Next.js with TypeScript
- **UI**: TailwindCSS
- **Real-time**: LiveKit React SDK
- **State Management**: React Hooks

## 🛠️ Setup Instructions

### Prerequisites
- Python 3.9+
- Node.js 18+
- LiveKit server (cloud or self-hosted)
- Twilio account for phone transfers
- Groq API key for LLM features

### API Keys Configuration

#### 1. LiveKit Setup
1. Sign up at [LiveKit Cloud](https://cloud.livekit.io/) or deploy your own server
2. Get your API key and secret from the LiveKit dashboard
3. Set the following environment variables in `.env` file:

```bash
# LiveKit Configuration
LIVEKIT_URL=wss://your-livekit-instance.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
```

#### 2. Twilio Setup
1. Sign up at [Twilio](https://www.twilio.com/)
2. Get your Account SID and Auth Token
3. Purchase a phone number
4. Add to your `.env` file:

```bash
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890  # Your Twilio phone number
```

#### 3. LLM Setup (Groq)
1. Sign up at [Groq](https://console.groq.com/)
2. Get your API key
3. Add to your `.env` file:

```bash
# LLM Configuration
GROQ_API_KEY=your_groq_api_key
```

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd warm-transfer
```

### 2. Set Up Backend

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env  # Edit with your configuration

# Run the backend server
uvicorn main:app --reload
```

### 3. Set Up Frontend

```bash
# Navigate to frontend directory
cd ../frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.local.example .env.local  # Edit with your configuration

# Run the development server
npm run dev
```

### 4. Access the Application

- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

### Backend (`.env`)

```env
# LiveKit Configuration
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_secret
LIVEKIT_WS_URL=wss://your-livekit-instance.livekit.cloud

# Application Settings
DEBUG=true  # Set to false in production
ENVIRONMENT=development

# Twilio Configuration (optional)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# AI Configuration (optional)
GROQ_API_KEY=your_groq_api_key
OPENAI_API_KEY=your_openai_api_key

# Caller Configuration
CALLER_IDENTITY=caller
```

### Frontend (`.env.local`)

```env
# API Configuration
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_LIVEKIT_URL=wss://your-livekit-instance.livekit.cloud

# Feature Flags
NEXT_PUBLIC_ENABLE_ANALYTICS=false
```

## 📞 Using the System - Workflow Logic

### 1. Starting a Call
1. Open the Caller Interface
2. Enter your name and click "Join Call"
3. You will be connected to the call with Agent A

### 2. Initiating a Transfer (Agent A)
1. In the Agent A dashboard, you'll see the caller's information
2. Click on "Transfer to Agent" or "Transfer to Phone"
3. For agent transfer, Agent B will receive a notification to join
4. For phone transfer, enter the phone number and click "Transfer"
5. The system will generate a summary and connect the call

### 3. Accepting a Transfer (Agent B)
1. Open the Agent B dashboard
2. You'll see an incoming transfer request with the call summary
3. Click "Accept Transfer" to join the call
4. You'll be connected to both the caller and Agent A

## 🧪 Testing

### Running Tests

```bash
# Navigate to backend directory
cd backend

# Run tests
pytest tests/
```

## 🚀 Deployment

### Backend

1. **Production Server**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

2. **Using Gunicorn** (recommended for production):
   ```bash
   gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b :8000 main:app
   ```

### Frontend

1. **Build for Production**:
   ```bash
   npm run build
   ```

2. **Start Production Server**:
   ```bash
   npm start
   ```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- LiveKit for real-time communication
- Twilio for telephony services
- Groq/OpenAI for AI-powered summarization
- The open-source community for invaluable tools and libraries

---

<div align="center">
  Made with ❤️ for seamless call transfers
</div>