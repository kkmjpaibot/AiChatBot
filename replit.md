# KKMJP Super Agent - Insurance Chatbot

## Overview
This is an AI-powered insurance sales chatbot application built with FastAPI and WebSocket technology. The application helps users explore different insurance plans through an interactive conversational interface with multiple AI agents.

## Purpose
- Provide personalized insurance recommendations based on user profiles
- Guide users through multiple insurance campaign options
- Calculate premium estimates based on user data
- Collect and store user information in Google Sheets

## Current State
- ✅ FastAPI backend running on port 5000
- ✅ WebSocket-based real-time chat interface (wss:// for HTTPS)
- ✅ Multiple insurance campaign modules (5 campaigns)
- ✅ NLP processing for intent detection
- ✅ Google Sheets integration (Replit-managed connection)
- ✅ Multi-agent selection (Erica, Daniel, Paivi)

## Recent Changes
**Date: November 11, 2025**
- ✅ Connected Google Sheets using Replit integration
- ✅ Updated Google_Sheet.py to use Replit-managed OAuth authentication
- ✅ Fixed WebSocket protocol to automatically detect HTTP/HTTPS (ws:// or wss://)
- ✅ Updated script.js version to force browser cache refresh

**Date: November 10, 2025**
- Installed Python 3.11 and required dependencies
- Fixed WebSocket connection to use dynamic port (removed hardcoded port 8000)
- Configured FastAPI workflow to run on port 5000 with host 0.0.0.0
- Set up deployment configuration for Autoscale
- Updated .gitignore with Python-specific patterns
- Created project documentation

## Project Architecture

### Backend (FastAPI)
- **main.py**: Main FastAPI application with WebSocket endpoint
- **Google_Sheet.py**: Integration with Google Sheets API using Replit OAuth
- **nlp_processor.py**: NLP intent detection using transformers

### Campaign Modules
1. **Campaign1 (SGSA)**: Satu Gaji Satu Harapan - Income protection plan
2. **Campaign2**: Tabung Warisan - Legacy planning
3. **Campaign3**: Masa Depan Anak Kita - Education savings
4. **Campaign4**: Tabung Perubatan - Medical coverage
5. **Campaign5**: Perlindungan Combo - Comprehensive protection

### Frontend
- **templates/index.html**: Main chat interface
- **static/script.js**: WebSocket client with automatic protocol detection
- **static/style-new.css**: Styling
- **static/**: Images and assets

## Dependencies
Key packages:
- fastapi >= 0.68.0
- uvicorn >= 0.15.0
- transformers >= 4.30.2
- torch >= 2.0.0
- google-api-python-client
- sentence-transformers
- pandas, numpy, scikit-learn

## Environment Variables
- `GOOGLE_SHEET_ID`: Google Sheets spreadsheet ID (default: 109fc5EkBwdHc4pZYEzYMTqknxw0ImGGiI3kgmIo95Vc)
- `GOOGLE_SHEET_NAME`: Sheet name (default: Sheet1)
- Replit automatically manages OAuth credentials for Google Sheets

## Running the Application
The application runs automatically via the configured workflow:
```bash
uvicorn main:app --host 0.0.0.0 --port 5000
```

## Google Sheets Integration
The application uses Replit's managed Google Sheets integration:
- Authentication is handled automatically via Replit OAuth
- No service account file needed
- Access tokens are refreshed automatically
- User data is saved to the configured spreadsheet after each conversation

## Deployment
Configured for Replit Autoscale deployment:
- Automatically scales based on traffic
- Runs on port 5000
- Uses uvicorn as the ASGI server

## User Flow
1. User visits the chat interface
2. Selects an agent (Erica, Daniel, or Paivi)
3. Provides basic information (name, age, etc.)
4. Receives personalized insurance plan recommendations
5. Explores campaign details and premium estimates
6. Data is automatically saved to Google Sheets for follow-up

## Notes
- The application uses WebSocket for real-time bidirectional communication
- WebSocket automatically uses wss:// for HTTPS and ws:// for HTTP
- Port 5000 is required for Replit web preview
- Campaign modules are dynamically loaded at runtime
- Google Sheets connection is managed by Replit (no manual credential setup needed)
