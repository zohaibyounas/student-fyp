-- Create dreams table for Islamic Dream Analyzer
CREATE TABLE IF NOT EXISTS dreams (
    id SERIAL PRIMARY KEY,
    dream_text TEXT NOT NULL,
    sentiment TEXT,
    islamic TEXT,
    meaning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);