# ChatGPT-Style UI/UX Overhaul Plan

## Goal
Transform MultiMind AI from enterprise dashboard to ChatGPT-style chat interface

## ChatGPT UI Characteristics
1. Clean white/light background
2. Centered chat interface
3. Message bubbles (user: light gray, assistant: white with shadow)
4. Fixed input bar at bottom
5. Minimal sidebar (just conversation history)
6. No complex dashboards - pure chat experience
7. Simple, conversational responses

## Changes Required

### 1. Theme Change
- Switch from dark (#0D1117) to light background
- Use ChatGPT's color palette (whites, light grays, blue accents)

### 2. Layout Restructure
- Remove sidebar navigation except conversation history
- Center chat with max-width container
- Fixed input bar at bottom of viewport

### 3. Message Display
- User bubbles: light gray (#F7F7F8)
- Assistant bubbles: white with subtle shadow
- Remove structured sections - keep conversational format

### 4. Landing Page
- Start directly in chat (no Knowledge Health dashboard)
- Show greeting message on first load

### 5. Navigation Simplified
- Only keep essential elements: Chat, Documents, Settings
- Remove complex dashboards from main navigation

## Questions for Clarification

**Which specific ChatGPT UI elements are essential?**  
The signature ChatGPT interface changed over time - do you want:
- Classic sidebar with black logo (2022-2023)?
- New sidebar with conversation list (2024+)?
- Mobile-first responsive design?

**Keep or remove the "structured response" format?**  
ChatGPT uses plain conversational responses. Should I:
- Remove the Answer/Source/Confidence sections entirely?
- Keep them in a simpler format within the chat bubble?

**Dashboard features - keep accessible?**  
The current enterprise features (Knowledge Doctor, Conflict Detection, etc.) - should they:
- Remain accessible via a separate "Tools" menu?
- Be removed entirely?
- Be integrated as special commands in chat?