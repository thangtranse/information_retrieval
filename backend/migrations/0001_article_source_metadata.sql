ALTER TABLE crawl_urls
    ADD COLUMN IF NOT EXISTS source_kind VARCHAR(16) NOT NULL DEFAULT 'url';

-- statement-breakpoint
ALTER TABLE crawl_urls
    ADD COLUMN IF NOT EXISTS display_title TEXT;

-- statement-breakpoint
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'crawl_urls_source_kind_check'
    ) THEN
        ALTER TABLE crawl_urls
            ADD CONSTRAINT crawl_urls_source_kind_check
            CHECK (source_kind IN ('url', 'manual'));
    END IF;
END
$$;
