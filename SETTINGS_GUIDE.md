# ⚙️ Settings System - Complete Guide

## Overview

Complete application settings management system with:
- **Exchange Configuration** - API keys, testnet settings
- **LLM Configuration** - DeepSeek/OpenAI/Local LM Studio
- **Risk Management** - Default trading parameters
- **Evolution Settings** - Generation defaults
- **UI Preferences** - Theme, auto-refresh, notifications

## Features

### 🔐 Secure Storage
- Encrypted API keys using Fernet encryption
- Settings saved to `~/.exhaustionlab/settings.json`
- Encryption key stored separately with 600 permissions
- Secrets masked in API responses

### 🔗 5 Settings Categories
1. **Exchange** - Binance API, testnet, default symbol/timeframe
2. **LLM** - Provider, API URL, model, temperature, tokens
3. **Risk** - Position size, daily loss, drawdown limits
4. **Evolution** - Generations, population, LLM usage
5. **UI** - Theme, refresh interval, notifications

### ✅ Validation
- Test exchange connection button
- Test LLM connection button
- Real-time validation feedback
- Form validation before save

## User Journey

1. Click **⚙️ Settings** button in hero section
2. Modal opens with 5 tabs
3. Switch between tabs to configure each section
4. Test connections with 🔍 buttons
5. Save with **💾 Save Settings**
6. Or reset to defaults with **🔄 Reset**

## API Endpoints

- `GET /api/settings` - Get settings (secrets masked)
- `GET /api/settings/full` - Get with secrets (internal use)
- `POST /api/settings` - Update settings
- `POST /api/settings/reset` - Reset to defaults
- `GET /api/settings/validate/exchange` - Test exchange
- `GET /api/settings/validate/llm` - Test LLM

## Implementation

**Backend**: `settings_service.py` (330 LOC)  
**API**: `api.py` (+85 LOC, 6 endpoints)  
**Frontend**: `index.html` (+254 LOC), `settings.js` (240 LOC), `styles.css` (+95 LOC)

**Total**: ~1,000 lines of code

## Status

✅ **COMPLETE AND READY TO USE**

All settings are fully functional with encryption, validation, and persistence!

---

**Date**: 2025-11-16  
**Status**: 🟢 READY
