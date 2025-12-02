-- ============================================
-- RFP CRAWLER - SIMPLIFIED DATABASE SCHEMA
-- ============================================
-- PostgreSQL is ONLY for storage, not matching logic

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- CRAWLED PAGES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS crawled_pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT NOT NULL UNIQUE,
    domain VARCHAR(255) NOT NULL,
    page_title TEXT,
    status_code INTEGER,
    crawled_at TIMESTAMP DEFAULT NOW(),
    is_rfp_related BOOLEAN DEFAULT FALSE,
    relevance_score FLOAT,
    depth INTEGER DEFAULT 0,
    parent_url TEXT,
    response_time_ms INTEGER
);

CREATE INDEX idx_crawled_pages_url ON crawled_pages(url);
CREATE INDEX idx_crawled_pages_domain ON crawled_pages(domain);
CREATE INDEX idx_crawled_pages_is_rfp ON crawled_pages(is_rfp_related);
CREATE INDEX idx_crawled_pages_crawled_at ON crawled_pages(crawled_at);

-- ============================================
-- RFPs TABLE (Main Storage)
-- ============================================
CREATE TABLE IF NOT EXISTS rfps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rfp_number VARCHAR(100) UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    agency VARCHAR(255),
    source_url TEXT NOT NULL,
    
    -- Financial
    budget_min DECIMAL(15, 2),
    budget_max DECIMAL(15, 2),
    currency VARCHAR(10) DEFAULT 'USD',
    
    -- Dates
    posted_date DATE,
    deadline_date DATE,
    
    -- Location
    country VARCHAR(100),
    state VARCHAR(100),
    city VARCHAR(100),
    
    -- Contact
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    
    -- Category
    category VARCHAR(100),
    
    -- Full extracted data (JSON)
    raw_data JSONB,
    
    -- AI MATCHING SCORES (calculated by Python/Ollama)
    jaccard_score FLOAT,
    cosine_score FLOAT,
    tfidf_score FLOAT,
    ner_score FLOAT,
    llm_score FLOAT,
    overall_score FLOAT NOT NULL,
    match_reasoning TEXT,
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_overall_score CHECK (overall_score >= 0 AND overall_score <= 1)
);

-- Indexes for fast queries
CREATE INDEX idx_rfps_overall_score ON rfps(overall_score DESC);
CREATE INDEX idx_rfps_deadline ON rfps(deadline_date);
CREATE INDEX idx_rfps_status ON rfps(status);
CREATE INDEX idx_rfps_country ON rfps(country);
CREATE INDEX idx_rfps_agency ON rfps(agency);

-- ============================================
-- CRAWL QUEUE TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS crawl_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT NOT NULL UNIQUE,
    domain VARCHAR(255) NOT NULL,
    priority INTEGER DEFAULT 5,
    depth INTEGER DEFAULT 0,
    parent_url TEXT,
    discovered_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    
    CONSTRAINT valid_priority CHECK (priority >= 1 AND priority <= 10)
);

CREATE INDEX idx_crawl_queue_status ON crawl_queue(status);
CREATE INDEX idx_crawl_queue_priority ON crawl_queue(priority DESC);
CREATE INDEX idx_crawl_queue_domain ON crawl_queue(domain);

-- ============================================
-- CRAWL STATISTICS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS crawl_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crawl_session_id UUID DEFAULT uuid_generate_v4(),
    domain VARCHAR(255),
    pages_crawled INTEGER DEFAULT 0,
    pages_failed INTEGER DEFAULT 0,
    rfps_found INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP
);

CREATE INDEX idx_crawl_stats_started ON crawl_statistics(started_at);

-- ============================================
-- VIEWS FOR QUICK QUERIES
-- ============================================

-- High priority RFPs (score >= 70%)
CREATE OR REPLACE VIEW high_priority_rfps AS
SELECT 
    id, rfp_number, title, agency, budget_min, budget_max,
    deadline_date, overall_score, jaccard_score, cosine_score,
    tfidf_score, ner_score, llm_score, source_url
FROM rfps
WHERE overall_score >= 0.70 AND status = 'active'
ORDER BY overall_score DESC, deadline_date ASC;

-- Recent RFPs (last 7 days)
CREATE OR REPLACE VIEW recent_rfps AS
SELECT id, title, agency, posted_date, deadline_date, overall_score
FROM rfps
WHERE created_at >= NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;

-- ============================================
-- SEED DATA
-- ============================================
INSERT INTO crawl_queue (url, domain, priority, depth, status) VALUES
('https://sam.gov/search/', 'sam.gov', 10, 0, 'pending'),
('https://gem.gov.in/search', 'gem.gov.in', 10, 0, 'pending')
ON CONFLICT (url) DO NOTHING;

-- ============================================
-- GRANT PERMISSIONS
-- ============================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO rfp_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO rfp_user;

DO $$
BEGIN
    RAISE NOTICE '✅ Simplified RFP database initialized!';
    RAISE NOTICE '📊 Tables: crawled_pages, rfps, crawl_queue, crawl_statistics';
    RAISE NOTICE '🎯 All matching logic handled by AI agents (Phase 5)';
END $$;