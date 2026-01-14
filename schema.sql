-- Run this in your Supabase SQL Editor to create the table

CREATE TABLE IF NOT EXISTS scraped_articles (
    id BIGSERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    authors TEXT,
    publish_date TEXT,
    text TEXT,
    summary TEXT,
    top_image TEXT,
    topic TEXT,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster topic searches
CREATE INDEX IF NOT EXISTS idx_scraped_articles_topic ON scraped_articles(topic);

-- Create index for URL lookups (duplicate checking)
CREATE INDEX IF NOT EXISTS idx_scraped_articles_url ON scraped_articles(url);

-- Enable Row Level Security (optional, adjust as needed)
-- ALTER TABLE scraped_articles ENABLE ROW LEVEL SECURITY;
