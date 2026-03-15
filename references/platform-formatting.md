# Platform Formatting Guide

## General Rules

DO NOT use markdown tables. They don't render on mobile chat platforms (Telegram, WhatsApp, Signal). Use plain text with line breaks instead.

## Map Links

Use hyperlinks (not raw URLs) where the platform supports them:
- **Telegram, Discord, terminal**: Use markdown links — `[Label](url)`
- **WhatsApp, Signal, SMS**: These don't support hyperlinks. Put the link on a separate line.

When map links are available, provide **both** Google Maps and Apple Maps links so the user can choose. Show both for the top result; Google Maps only for the rest.

## Platform Detection

If the platform is unknown, default to the hyperlink format (markdown links). Most platforms handle it gracefully.

## Invite Follow-Up

Always end with a brief follow-up prompt appropriate to the skill's context, e.g.:
- "Ask me about a specific [item] for more detail"
- "Want me to try a wider search?"
- "Reply with [item] for more info"
