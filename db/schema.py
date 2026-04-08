from typing import List
from .connection import DatabaseConnection


class SchemaManager:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    # ✅ CREATE ALL TABLES
    def create_all_tables(self):
        statements = [
            self._create_companies_table(),
            self._create_prices_table(),
            self._create_daily_prices_table(),
            self._create_financials_table(),
            self._create_dividends_table(),
            self._create_announcements_table(),
            self._create_news_table(),
            self._create_news_embeddings_table(),  # ✅ ADDED
            self._create_social_posts_table(),
        ]

        for statement in statements:
            self.db.execute_query(statement)

    # ✅ DROP ALL TABLES
    def drop_all_tables(self):
        statements = [
            "DROP TABLE IF EXISTS social_posts CASCADE;",
            "DROP TABLE IF EXISTS news_embeddings CASCADE;",  # ✅ ADDED
            "DROP TABLE IF EXISTS news CASCADE;",
            "DROP TABLE IF EXISTS announcements CASCADE;",
            "DROP TABLE IF EXISTS dividends CASCADE;",
            "DROP TABLE IF EXISTS financials CASCADE;",
            "DROP TABLE IF EXISTS daily_prices CASCADE;",
            "DROP TABLE IF EXISTS prices CASCADE;",
            "DROP TABLE IF EXISTS companies CASCADE;",
        ]

        for statement in statements:
            self.db.execute_query(statement)

    # ✅ VERIFY TABLES
    def verify_tables(self):
        tables = [
            "companies",
            "prices",
            "daily_prices",
            "financials",
            "dividends",
            "announcements",
            "news",
            "news_embeddings",  # ✅ ADDED
            "social_posts",
        ]

        for table in tables:
            row_count = self._get_row_count(table)
            print(f"{table}: {row_count} rows")

    def _get_row_count(self, table_name: str) -> int:
        result = self.db.fetch_all(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s;",
            (table_name,),
        )
        if result and result[0][0] == 1:
            count_result = self.db.fetch_all(f"SELECT COUNT(*) FROM {table_name};")
            return count_result[0][0] if count_result else 0
        return 0

    # ✅ COMPANIES
    def _create_companies_table(self) -> str:
        return """
        CREATE TABLE IF NOT EXISTS companies (
            symbol VARCHAR(10) PRIMARY KEY,
            name_ar VARCHAR(255),
            name_en VARCHAR(255),
            sector_ar VARCHAR(100),
            sector_en VARCHAR(100),
            share_type VARCHAR(50),
            total_shares BIGINT,
            paid_capital BIGINT,
            isin VARCHAR(20),
            founded_date DATE,
            fiscal_year_end VARCHAR(5),
            auditor VARCHAR(100),
            market_cap NUMERIC(15,2),
            company_url VARCHAR(500),
            last_updated TIMESTAMP DEFAULT NOW(),
            sector_code VARCHAR(10),
            market VARCHAR(30) DEFAULT 'MAIN_MARKET'
        );
        """

    # ✅ PRICES
    def _create_prices_table(self) -> str:
        return """
        CREATE TABLE IF NOT EXISTS prices (
            symbol VARCHAR(10) NOT NULL,
            date DATE NOT NULL,
            open NUMERIC(14,4),
            high NUMERIC(14,4),
            low NUMERIC(14,4),
            close NUMERIC(14,4),
            prev_close NUMERIC(14,4),
            volume BIGINT,
            turnover NUMERIC(22,4),
            num_trades INTEGER,
            change NUMERIC(14,4),
            change_pct NUMERIC(10,4),
            PRIMARY KEY (symbol, date),
            FOREIGN KEY (symbol)
                REFERENCES companies(symbol)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS prices_symbol_date_idx
        ON prices(symbol, date DESC);
        """

    # ✅ DAILY PRICES
    def _create_daily_prices_table(self) -> str:
        return """
        CREATE TABLE IF NOT EXISTS daily_prices (
            symbol VARCHAR(10) NOT NULL,
            trade_date DATE NOT NULL,
            open_price NUMERIC(10,2),
            high_price NUMERIC(10,2),
            low_price NUMERIC(10,2),
            close_price NUMERIC(10,2),
            prev_close NUMERIC(10,2),
            change_value NUMERIC(10,2),
            change_pct NUMERIC(6,2),
            volume BIGINT,
            value_traded NUMERIC(15,2),
            num_trades INTEGER,
            best_bid_price NUMERIC(10,2),
            best_bid_qty INTEGER,
            best_offer_price NUMERIC(10,2),
            best_offer_qty INTEGER,
            PRIMARY KEY (symbol, trade_date),
            FOREIGN KEY (symbol)
                REFERENCES companies(symbol)
                ON DELETE CASCADE
        );
        """

    # ✅ FINANCIALS
    def _create_financials_table(self) -> str:
        return """
        CREATE TABLE IF NOT EXISTS financials (
            symbol VARCHAR(10) NOT NULL,
            period_end DATE NOT NULL,
            period_type VARCHAR(10) NOT NULL,
            total_revenue NUMERIC(15,2),
            net_profit_before_zakat NUMERIC(15,2),
            zakat_tax NUMERIC(15,2),
            net_profit NUMERIC(15,2),
            eps NUMERIC(10,2),
            total_assets NUMERIC(15,2),
            total_liabilities NUMERIC(15,2),
            total_equity NUMERIC(15,2),
            operating_cash_flow NUMERIC(15,2),
            investing_cash_flow NUMERIC(15,2),
            financing_cash_flow NUMERIC(15,2),
            cash_end NUMERIC(15,2),
            PRIMARY KEY (symbol, period_end, period_type),
            FOREIGN KEY (symbol)
                REFERENCES companies(symbol)
                ON DELETE CASCADE
        );
        """

    # ✅ DIVIDENDS
    def _create_dividends_table(self) -> str:
        return """
        CREATE TABLE IF NOT EXISTS dividends (
            symbol VARCHAR(10) NOT NULL,
            announcement_date DATE,
            eligibility_date DATE NOT NULL,
            distribution_date DATE,
            amount_per_share NUMERIC(10,2),
            PRIMARY KEY (symbol, eligibility_date),
            FOREIGN KEY (symbol)
                REFERENCES companies(symbol)
                ON DELETE CASCADE
        );
        """

    # ✅ ANNOUNCEMENTS
    def _create_announcements_table(self) -> str:
        return """
        CREATE TABLE IF NOT EXISTS announcements (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10),
            announcement_date TIMESTAMP,
            title_ar TEXT,
            price_on_date NUMERIC(10,2),
            change_pct_on_date NUMERIC(6,2),
            FOREIGN KEY (symbol)
                REFERENCES companies(symbol)
                ON DELETE CASCADE
        );
        """

    # ✅ NEWS
    def _create_news_table(self) -> str:
        return """
        CREATE TABLE IF NOT EXISTS news (
            id SERIAL PRIMARY KEY,
            source VARCHAR(100),
            published_date TIMESTAMP,
            title TEXT,
            summary TEXT,
            url VARCHAR(500) UNIQUE,
            sentiment_score NUMERIC(4,2),
            related_symbols TEXT,
            fetched_at TIMESTAMP DEFAULT NOW()
        );
        """

    # ✅ NEWS EMBEDDINGS (NEW)
    def _create_news_embeddings_table(self) -> str:
        return """
        CREATE TABLE IF NOT EXISTS news_embeddings (
            news_id INTEGER PRIMARY KEY,
            embedding DOUBLE PRECISION[],
            news_date TIMESTAMP NOT NULL,
            embedding_created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (news_id)
                REFERENCES news(id)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_news_embeddings_date
        ON news_embeddings(news_date);
        """

    # ✅ SOCIAL POSTS
    def _create_social_posts_table(self) -> str:
        return """
        CREATE TABLE IF NOT EXISTS social_posts (
            id SERIAL PRIMARY KEY,
            platform VARCHAR(50),
            account VARCHAR(100),
            post_id VARCHAR(50) UNIQUE,
            content TEXT,
            published_date TIMESTAMP,
            likes INTEGER,
            retweets INTEGER,
            replies INTEGER,
            url VARCHAR(500),
            related_symbols TEXT,
            fetched_at TIMESTAMP DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_social_account
        ON social_posts(account);

        CREATE INDEX IF NOT EXISTS idx_social_date
        ON social_posts(published_date);
        """