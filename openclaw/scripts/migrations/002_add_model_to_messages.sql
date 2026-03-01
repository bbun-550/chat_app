-- Migration 002: add model column to messages
-- Each message now records which model was used (user intent / assistant generation)
ALTER TABLE messages ADD COLUMN model TEXT NOT NULL DEFAULT 'gemini-3-flash-preview';
