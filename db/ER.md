## Saudi Stocks Database – Entity Relationship Overview
The `companies` table is the core entity in the database, serving as the central reference for all listed symbols.  
The `prices` table (190,248 rows) stores historical market data and is the only table currently enforced with a foreign key to `companies`.  
Other tables like `financials`, `dividends`, `announcements`, `news`, and `social_posts` extend the model with fundamentals and sentiment data, forming a solid foundation for market analytics.


```mermaid
erDiagram

    COMPANIES {
        varchar(10) symbol PK
        varchar name_ar
        varchar name_en
        varchar sector_ar
        varchar sector_en
        varchar share_type
        bigint total_shares
        bigint paid_capital
        varchar isin
        date founded_date
        varchar fiscal_year_end
        varchar auditor
        numeric market_cap
        varchar company_url
        timestamp last_updated
        varchar sector_code
        varchar market
    }

    PRICES {
        varchar(10) symbol FK
        date date PK
        numeric open
        numeric high
        numeric low
        numeric close
        numeric prev_close
        bigint volume
        numeric turnover
        integer num_trades
        numeric change
        numeric change_pct
    }

    DAILY_PRICES {
        varchar(10) symbol PK
        date trade_date PK
        numeric open_price
        numeric high_price
        numeric low_price
        numeric close_price
        numeric prev_close
        numeric change_value
        numeric change_pct
        bigint volume
        numeric value_traded
        integer num_trades
        numeric best_bid_price
        integer best_bid_qty
        numeric best_offer_price
        integer best_offer_qty
    }

    DIVIDENDS {
        varchar(10) symbol PK
        date eligibility_date PK
        date announcement_date
        date distribution_date
        numeric amount_per_share
    }

    FINANCIALS {
        varchar(10) symbol PK
        date period_end PK
        varchar period_type PK
        numeric total_revenue
        numeric net_profit_before_zakat
        numeric zakat_tax
        numeric net_profit
        numeric eps
        numeric total_assets
        numeric total_liabilities
        numeric total_equity
        numeric operating_cash_flow
        numeric investing_cash_flow
        numeric financing_cash_flow
        numeric cash_end
    }

    ANNOUNCEMENTS {
        int id PK
        varchar(10) symbol
        timestamp announcement_date
        text title_ar
        numeric price_on_date
        numeric change_pct_on_date
    }

    NEWS {
        int id PK
        varchar source
        timestamp published_date
        text title
        text summary
        varchar url
        numeric sentiment_score
        text related_symbols
        timestamp fetched_at
    }

    NEWS_EMBEDDINGS {
        int news_id PK
        double_precision_array embedding
        timestamp news_date
        timestamp embedding_created_at
    }

    SOCIAL_POSTS {
        int id PK
        varchar platform
        varchar account
        varchar post_id
        text content
        timestamp published_date
        int likes
        int retweets
        int replies
        varchar url
        text related_symbols
        timestamp fetched_at
    }

    COMPANIES ||--o{ PRICES : has
    NEWS ||--|| NEWS_EMBEDDINGS : has
```