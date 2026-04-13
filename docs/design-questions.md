1- We have about 300 companies listed in TASI, and we aim to understand how daily news and announcements affect the overall TASI index. Each company is embedded once using its description, and each news article is embedded once per day (e.g., 10 news = 10 embeddings), avoiding unnecessary duplication like 10 × 300 embeddings. should we just use the 10 embeddings for each tasi price , or should we think of aggregating multiple daily news embeddings into a single meaningful market-level representation. This aggregated daily signal will be used to train a regression model to predict TASI returns. The ultimate goal is not only prediction accuracy, but also extracting interpretable rules about which types of news drive market movements.


Discussion of Q1 : 
I think we should aggregate, but the how matters enormously — especially given our  interpretability goal. Using raw embeddings directly creates a variable-length input problem (10 news one day, 3 another), forces the model to implicitly learn aggregation, and essentially buries interpretability. A deliberate aggregation strategy surfaces it.


If we simply pass the 10 embeddings as-is to a regression model, we face three compounding issues. First, the number of news items varies daily, so our feature space is unstable. Second, any pooling we're forced to do at the model input stage (to fix dimensionality) is implicit and uncontrolled. Third, and most critically for our goal, the model learns a black-box mapping from a news blob to a return — we lose the ability to say "news of type X about sector Y caused the market to move."


we already have 300 company embeddings, rather than treating news and company descriptions as two separate assets, we can use the company embeddings as a semantic vocabulary to decompose each news article.

For each daily news embedding, we can compute its cosine similarity against all 300 company embeddings. This gives us a 300-dimensional relevance vector per news article — essentially asking "which companies does this article resonate with?" we then aggregate these relevance vectors across the day's news (mean, max, or weighted sum) to get a single 300-dimensional daily market signal vector.

If we further group companies by sector (banking, petrochemicals, real estate, etc.), we can collapse the 300-dim vector into a ~15–20 dimensional sector-relevance signal that is far more tractable and directly interpretable. A regression coefficient on the "banking sector relevance" feature then directly answers: "when banking news is prominent, what does TASI do?"

Weighted Aggregation Matters More Than Simple Pooling

A plain mean of the 10 daily news embeddings treats a major Aramco announcement the same as a minor corporate disclosure. we should weight news by relevance or importance. A practical weighting scheme involves computing a news importance score by summing the cosine similarities of each article against all company embeddings, scaled by market capitalization. Aramco alone constitutes a disproportionate share of TASI, so news that scores highly against large-cap companies should carry more weight in your daily aggregate. This produces a market-cap-weighted semantic signal that is structurally aligned with how the index actually moves.

Topic Modeling as a Parallel Track for Interpretability

For the rule-extraction goal specifically, I'd strongly recommend running BERTopic or a similar topic model across your full corpus of news articles. This gives each article a topic distribution (e.g., 40% "monetary policy", 35% "oil prices", 25% "earnings"), and we can represent each day as a topic proportion vector. Training your regression on these topic proportions is directly interpretable: the model tells we that "a 10% increase in the daily prominence of oil-price-related news is associated with a +0.3% TASI return," which is exactly the kind of rule we want.

The practical architecture then becomes a two-stream system: the company-relevance aggregated embedding for predictive power, and the topic-distribution vector for interpretability. we can train two separate regression models and compare them, or concatenate both feature sets and apply SHAP values to disentangle which stream drives the predictions.

SHAP for Rule Extraction from the Regression Model

Once we have your aggregated feature vector (whether sector-relevance, topic-distribution, or both), SHAP (SHapley Additive Explanations) applied to the regression model is your most principled tool for extracting rules. SHAP force plots will show we on any given day which features pushed the predicted return up or down. Across many days we can then extract patterns like: "days where oil-sector relevance is high and monetary-policy topic is prominent consistently show positive SHAP contributions to predicted returns." These are empirically grounded rules, not just correlation statistics.


--------------


Q2 . 

News published on day D may reflect events **after market close**, meaning they actually affect TASI on day D+1. You should decide upfront whether your embedding for a given day represents:

- **Same-day news** → predicts same-day return (only works if news is pre-market)
- **Previous-day news** → predicts next-day return (safer and more realistic)

Shifting the news by one day (`news_date → next trading day`) is the safer default and avoids look-ahead leakage. This is a small change but it changes the meaning of your entire model.

