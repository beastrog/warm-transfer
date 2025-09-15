# Warm Transfer System

A robust warm transfer solution enabling seamless call handoffs between agents and external phone numbers. This system provides real-time audio communication, automated conversation summarization, and flexible transfer capabilities.

## 🌟 Key Features

### Core Functionality
- **Multi-Agent Warm Transfer**: Seamlessly transfer calls between agents with conversation context
- **Phone Integration**: Transfer calls to external phone numbers via Twilio
- **Real-time Transcription**: Automatic transcription of ongoing conversations
- **AI-Powered Summaries**: Automated conversation summaries for smooth handoffs
- **Modern Web Interface**: Responsive UI with real-time updates

### Technical Highlights
- **WebRTC Audio**: Powered by LiveKit for high-quality, low-latency audio
- **AI Processing**: Utilizes LLMs (Groq/OpenAI) for intelligent summarization
- **RESTful API**: Well-documented endpoints for extensibility
- **Responsive Design**: Works on desktop and mobile devices

## 🛠 Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.9+)
- **Realtime**: LiveKit Server SDK
- **AI/ML**: Groq (primary) and OpenAI (fallback) for LLM processing
- **Database**: SQLite for persistent storage (transcripts, call statuses)
- **Authentication**: JWT-based token system

### Frontend
- **Framework**: Next.js 13+ with TypeScript
- **UI**: TailwindCSS + HeadlessUI
- **State Management**: React Query
- **WebRTC**: LiveKit React SDK
- **Real-time Updates**: Server-Sent Events (SSE)

## 📁 Project Structure

```
/warm-transfer
  /backend
    ├── main.py              # FastAPI application and routes
    ├── models.py            # Pydantic models and request/response schemas
    ├── requirements.txt     # Python dependencies
    ├── db_operations.py     # Database interface and models
    ├── .env.example        # Example environment configuration
    ├── /services
    │   ├── livekit_client.py # LiveKit integration
    │   ├── llm_client.py    # LLM integration (Groq/OpenAI)
    │   └── transcripts.py   # Transcript management
    └── /tests              # Test suites
        ├── test_api.py
        └── test_services.py

  /frontend
    ├── package.json        # Frontend dependencies
    ├── next.config.js      # Next.js configuration
    ├── tailwind.config.js  # Tailwind CSS configuration
    ├── /pages
    │   ├── index.tsx       # Caller interface
    │   ├── agent-a.tsx     # Agent A dashboard
    │   ├── agent-b.tsx     # Agent B dashboard
    │   └── api/            # API route handlers
    ├── /components         # Reusable UI components
    ├── /lib                # Utility functions
    ├── /styles             # Global styles
    └── /utils              # Helper utilities
        └── api.ts          # API client

  /docs
    ├── architecture.md     # System architecture
    ├── api.md             # API documentation
    └── setup.md           # Detailed setup guide

  start.ps1                # Windows start script
  README.md                # This file
  .gitignore              # Git ignore rules
  LICENSE                 # MIT License
```

## 🔧 Environment Configuration

### Backend (`.env`)

#### Required
```
# LiveKit Configuration
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_secret
LIVEKIT_WS_URL=wss://your-livekit-instance.livekit.cloud

# Application Settings
DEBUG=true  # Set to false in production
ENVIRONMENT=development  # or 'production'
```

#### Optional (for advanced features)
```
# Twilio Configuration (for phone transfers)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890  # Must be a Twilio number in E.164 format

# AI/ML Configuration (for conversation summaries)
OPENAI_API_KEY=your_openai_api_key  # Fallback if Groq is not available
GROQ_API_KEY=your_groq_api_key      # Preferred LLM provider

# Caller Configuration
CALLER_IDENTITY=caller  # Default identity for callers
```

### Frontend (`.env.local`)
```
# API Configuration
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_LIVEKIT_URL=wss://your-livekit-instance.livekit.cloud

# Feature Flags (optional)
NEXT_PUBLIC_ENABLE_ANALYTICS=false
NEXT_PUBLIC_SENTRY_DSN=your_sentry_dsn
```

## 📞 Twilio Phone Transfer

The system includes seamless integration with Twilio Programmable Voice for transferring calls to external phone numbers.

### Setup Instructions

1. **Obtain Twilio Credentials**
   - Sign up at [Twilio](https://www.twilio.com/)
   - Get your `ACCOUNT_SID` and `AUTH_TOKEN` from the Twilio Console
   - Purchase or use a trial phone number

2. **Configure Environment Variables**
   Add these to your `.env` file in the backend directory:
   ```env
   # Twilio Configuration
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_PHONE_NUMBER=+12345556789  # Your Twilio number in E.164 format
   ```

3. **Verify Phone Numbers**
   - Log in to your Twilio Console
   - Navigate to Phone Numbers > Verified Caller IDs
   - Add any numbers you want to call (required for trial accounts)

### Usage

1. **Initiate Transfer**
   - In the Agent A dashboard, enter a phone number in E.164 format (e.g., `+14155551212`)
   - Click "Transfer to Phone"
   - The system will generate a summary and initiate the call

2. **Call Flow**
   - The system calls the specified number using your Twilio number
   - When answered, it plays the generated summary
   - The call is then bridged to the original caller

### Troubleshooting

- **Call Fails to Connect**
  - Verify the number is in E.164 format (e.g., `+14155551212`)
  - For trial accounts, ensure the number is verified in Twilio
  - Check the backend logs for detailed error messages

- **Audio Quality Issues**
  - Ensure stable internet connection
  - Check Twilio's [Network Connectivity Requirements](https://www.twilio.com/docs/voice/client/javascript/voice-client-js-and-mobile-sdks-network-connectivity-requirements)

### Security Considerations

- Never expose your Twilio credentials in client-side code
- Use environment variables for all sensitive information
- Restrict Twilio API keys to necessary permissions
- Monitor your Twilio usage to prevent unexpected charges

## 📸 Screenshots

### Caller Interface
![Caller Interface](/screenshots/caller-interface.png)
- Clean, minimal interface for callers
- Shows connection status and call controls
- Mobile-responsive design

### Agent A Dashboard
![Agent A Dashboard](/screenshots/agent-a-dashboard.png)
- Real-time transcript display
- Transfer options (to Agent B or phone)
- Call controls and participant list
- Transfer status indicators

### Agent B Dashboard
![Agent B Dashboard](/screenshots/agent-b-dashboard.png)
- Conversation summary display
- Call controls
- Participant status
- Transfer history

### Phone Transfer Flow
![Phone Transfer](/screenshots/phone-transfer.png)
- Phone number input with validation
- Transfer status tracking
- Call summary preview

> Note: Replace the placeholder image paths with actual screenshots from your deployment.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- npm or yarn
- LiveKit server (self-hosted or cloud)
- (Optional) Twilio account for phone transfers

### Backend Setup

1. **Create and activate virtual environment**
   ```bash
   cd warm-transfer/backend
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   # Unix/macOS
   source .venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run migrations**
   ```bash
   # Initialize database
   python -c "from db_operations import init_db; init_db()"
   ```

5. **Start the server**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
   The API will be available at `http://localhost:8000`
   
   > **Note**: For production, use a proper ASGI server like `uvicorn` with `gunicorn`

### Frontend Setup

1. **Install dependencies**
   ```bash
   cd ../frontend
   npm install
   ```

2. **Configure environment**
   ```bash
   cp .env.local.example .env.local
   # Edit .env.local with your configuration
   ```

3. **Start the development server**
   ```bash
   npm run dev
   ```
   The frontend will be available at `http://localhost:3000`

### Using Docker (Alternative)

1. **Build and start containers**
   ```bash
   docker-compose up --build
   ```
   
2. **Access the application**
   - Frontend: `http://localhost:3000`
   - Backend API: `http://localhost:8000`
   - API Docs: `http://localhost:8000/docs`

## 🔄 Detailed Workflow

### 1. Caller Joins
- **User Action**: Caller visits `/` and clicks "Join Call"
- **System Action**:
  - Backend creates `roomA`
  - Generates WebRTC token for the caller
  - Establishes WebRTC connection
- **UI Feedback**: Shows "Connected" status and call controls

### 2. Agent A Joins
- **User Action**: Agent A visits `/agent-a` and clicks "Join"
- **System Action**:
  - Joins `roomA`
  - Displays real-time transcript
  - Shows participant list
- **UI Feedback**: Shows active call with caller information

### 3. Transfer Initiation
- **User Action**: Agent A clicks "Transfer"
- **System Action**:
  - Creates `roomB`
  - Generates AI summary of conversation
  - Returns tokens for all participants
  - Broadcasts transfer notification in `roomA`
- **UI Feedback**: Shows transfer in progress with loading state

### 4. Caller Transfer
- **System Action**:
  - Automatically moves caller to `roomB`
  - Preserves audio connection
  - Updates UI to show new room context
- **UI Feedback**: Brief notification of transfer

### 5. Agent A Moves
- **System Action**:
  - Moves Agent A to `roomB`
  - Displays conversation summary
  - Shows participant list
- **UI Feedback**: Summary card with key points

### 6. Agent B Joins
- **User Action**: Agent B visits `/agent-b` and enters room ID
- **System Action**:
  - Validates room access
  - Joins `roomB`
  - Fetches and displays summary
- **UI Feedback**: Shows summary and active participants

### 7. Call Completion
- **User Action**: Agent A may leave the call
- **System Action**:
  - Updates participant list
  - Maintains connection between caller and Agent B
- **UI Feedback**: Shows updated participant status

### Phone Transfer Flow
1. Agent A initiates phone transfer
2. System validates phone number
3. Calls target number via Twilio
4. Plays summary to the callee
5. Bridges the call to original caller
6. Updates UI with call status

## Error Handling
- Failed transfers automatically revert
- Network issues trigger reconnection
- Failed AI fallback to simple transcript
- Comprehensive error logging

## 📝 Additional Notes

### Data Persistence
- Transcripts and call data are stored in SQLite database
- Restarting the server preserves call history
- Automatic backups can be configured

### AI Integration
- **Primary**: Groq API (fastest response)
- **Fallback**: OpenAI API (if Groq unavailable)
- **Local Fallback**: Basic keyword extraction (no API key required)

### Security Considerations
- All WebRTC traffic is encrypted
- API endpoints require valid JWT tokens
- Rate limiting on authentication endpoints
- Input validation on all API endpoints

### Performance
- Optimized for low-latency audio
- Efficient WebRTC connection management
- Background processing for AI tasks

### Monitoring
- Structured JSON logging
- Performance metrics endpoint
- Health check at `/health`

## 🛠 Troubleshooting

### Common Issues

#### No Audio
- Check browser permissions for microphone access
- Verify LiveKit server is accessible
- Check console for WebRTC errors

#### Transfer Fails
- Verify room names match exactly
- Check network connectivity
- Review server logs for errors

#### AI Summary Not Working
- Verify API keys are set
- Check rate limits on AI providers
- Review network requests in browser dev tools

### Getting Help
- Check the [LiveKit documentation](https://docs.livekit.io/)
- Review the [Twilio API docs](https://www.twilio.com/docs/voice)
- Open an issue on GitHub

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LiveKit](https://livekit.io/) for the amazing WebRTC infrastructure
- [Twilio](https://www.twilio.com/) for phone integration
- [Groq](https://groq.com/) and [OpenAI](https://openai.com/) for AI capabilities
- The open-source community for invaluable tools and libraries

---

<div align="center">
  Made with ❤️ for seamless call transfers
</div>
