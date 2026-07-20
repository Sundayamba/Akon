# Akon Deployment Guide

## Target deployment

- Backend: Render Web Service
- Database: Render PostgreSQL
- Frontend: Vercel
- AI provider: Gemini

## Backend deployment on Render

Create a new Render Web Service from the GitHub repository.

Recommended settings:

- Root Directory: `backend`
- Runtime: Python 3
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Backend environment variables on Render

Set these in Render dashboard:

```env
APP_NAME=Akon
APP_ENV=production
API_VERSION=0.5.7

DEFAULT_AI_PROVIDER=gemini
ALLOW_AI_FALLBACK=false

GEMINI_API_KEY=your-real-gemini-key
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MAX_OUTPUT_TOKENS=1200

DATABASE_URL=your-render-postgres-internal-database-url

SECRET_KEY=your-long-random-production-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

PUBLIC_FRONTEND_URL=https://your-vercel-domain.vercel.app
CORS_ALLOWED_ORIGINS=https://your-vercel-domain.vercel.app
TRUSTED_HOSTS=localhost,127.0.0.1,testserver,*.onrender.com
EXPOSE_DOCS=false

## Conversation persistence requirement

Akon's conversation history and consent-controlled memories require persistent
PostgreSQL storage in production.

Do not deploy production with the default local SQLite URL. Render web-service
filesystems may be replaced during deployment or service restart.

Required production configuration:

```env
APP_ENV=production
DATABASE_URL=your-render-postgres-internal-database-url
```

The backend refuses to start in production when `DATABASE_URL` uses SQLite.
