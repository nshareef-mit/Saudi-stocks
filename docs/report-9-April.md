1. We collected a broad historical corpus of market news and company announcements from the database, not limited to stock 2222, each stored with its publication date and precomputed embedding vector (1536 dimensions).  
2. Since trading models require one observation per trading day, we first ensured that both features (X) and targets (y) were aligned at the daily level.  
3. The target variable (y) was constructed from the JSON market file: using `previousClosePrice`, we computed daily index return as  
   \(\text{return}_D = \frac{\text{prevClose}_{D+1} - \text{prevClose}_D}{\text{prevClose}_D}\).  
4. This produced one target value (tasi_return) per trading day.  
5. For features (X), we aggregated all embeddings published on the same calendar day.  
6. The primary aggregation strategy was mean pooling: averaging all embedding vectors per day to obtain one 1536‑dimensional semantic vector.  
7. We also included optional structural features such as daily news_count to capture information flow intensity.  
8. This ensured the regression dataset had one row per trading day with matching X and y dimensions.  
9. The resulting raw dataset had shape ≈ 809 days × 1536 embedding features (plus optional counts).  
10. Because 1536 dimensions are high relative to the number of observations, we applied Principal Component Analysis (PCA).  
11. PCA reduced the feature space to 50 components while retaining ~78% of total embedding variance.  
12. This dimensionality reduction improved numerical stability and reduced overfitting risk.  
13. The final regression matrix therefore consisted of 809 rows × 50 principal components (+ optional news_count).  
14. We then trained regularized linear models (Ridge regression) using time‑ordered splits to avoid look‑ahead bias.  
15. Initial experiments showed limited predictive power for next‑day returns, indicating that aggregated daily news embeddings alone do not yet provide a statistically robust trading edge.


--------------------

Analysis: 

What the Results Are Actually Telling You

Your test R² of −0.36 is worse than a naive mean-prediction baseline, and your direction accuracy of 45% is below a random coin flip. These are not just "weak results" — they are informative signals that something is structurally wrong, not just that the news signal is weak. The Sharpe of 1.38 vs. buy-and-hold's 3.45 confirms the model adds no value over passively holding TASI. Before trying fancier models, you need to fix the foundations.

Critical Issue 1: Temporal Leakage Risk

This is the most important thing to audit. Your stated objective is to use information available at the end of day t to forecast the return on day t+1. Double-check your data pipeline carefully. Specifically, if a news article is published on the morning of day t+1, it must not appear in your features for predicting the return of day t+1. Any leakage of same-day or forward-looking news will produce artificially inflated training R² (which yours is, at 0.21) while still tanking test performance — exactly the pattern you see. The news_date timestamp in your embeddings table needs to be treated as a cutoff: only articles published before market open on day t+1 (or conservatively, before the close of day t) should be eligible as features for the t→t+1 target.

Critical Issue 2: Mean Pooling Destroys the Signal

Averaging all 1536-dimensional embedding vectors across every article published on a given day is the simplest possible aggregation, but it is likely destroying the very signal you're looking for. Consider what happens when you have 50 news articles on a given day: corporate earnings announcements, geopolitical news, general economic commentary, sports scores that sneak through scraping — all of these get averaged together into a single centroid vector that points roughly nowhere in semantic space. Instead of mean pooling alone, try the following three alternatives and compare them experimentally.

The first is recency-weighted pooling: give more weight to articles published later in the day, closer to market close, since those are more likely to be market-moving. The second is dispersion features: alongside the mean vector, compute the variance or standard deviation across embeddings for that day. High dispersion in the news signal often corresponds to uncertainty or disagreement, which is itself a predictive market signal. The third is rolling window aggregation: instead of using only today's mean embedding, include 3-day and 5-day trailing means as additional features. Markets often react with a lag, and a persistent news theme can take multiple days to be priced in.

Critical Issue 3: You Have 809 Samples

This is a hard constraint that shapes everything. With roughly 809 trading days, even after PCA to 50 components you are working with a feature-to-sample ratio that makes it very easy to overfit. A single 80/20 split gives you only about 162 test samples — far too few for statistically reliable Sharpe or R² estimates. You need to switch to walk-forward cross-validation (also called expanding window or rolling window CV). The idea is to train on the first K months, test on month K+1, then retrain on K+1 months, test on K+2, and so on. This gives you many non-overlapping test windows and a far more honest estimate of out-of-sample performance. With 809 days you might get 10–15 folds of about 2 months each, which is much more robust.

Critical Issue 4: PCA May Not Be the Right Dimensionality Reduction

PCA finds directions of maximum variance in your embeddings, but maximum variance in news semantics is not the same as maximum predictive relevance to TASI returns. A direction of high variance might correspond to whether an article is about technology vs. real estate, which could be irrelevant to the market index. Consider replacing PCA with Partial Least Squares (PLS) regression, which finds components that explain maximum covariance between X (embeddings) and y (returns) simultaneously. With financial embeddings, PLS often outperforms PCA precisely because it is supervised — it projects the feature space toward the directions that actually co-vary with the target. Try PLS with 5, 10, 20, and 50 components and compare walk-forward performance.

Recommended Immediate Experimental Plan

The first priority is to reconstruct your features with strict temporal alignment: write an explicit check that verifies no feature for day t uses data timestamped after market close on day t. This single audit will either confirm or eliminate the leakage hypothesis.

The second step is to replace the single 80/20 split with walk-forward CV and re-measure direction accuracy (not R², since direction accuracy is your actual trading objective) across all folds. If direction accuracy is consistently around 45–48% across folds, that tells you the signal is genuinely absent. If it varies wildly between folds (e.g., 60% in some, 40% in others), the model is unstable and the features need rethinking.

The third step is to add the dispersion features (daily variance of embeddings, news count) and run PLS instead of PCA+Ridge. These two changes together are more likely to surface a real signal than any amount of model tuning.

A Note on the Tadawul Specifically

TASI has some structural properties that make this problem harder than equivalent experiments on S&P 500. Trading is heavily concentrated in a small number of mega-cap names (notably Aramco, which is stock 2222 in your notebook), and the index is strongly influenced by oil prices and government announcements that often come outside normal news cycles or in Arabic-language official channels. If your news corpus is primarily in English or is not specifically filtered for Tadawul-relevant sources, the semantic signal may simply not be present in a form that maps to market returns. You may want to also compute a relevance filter: use a fixed "anchor" embedding representing something like "Saudi stock market performance" and compute the cosine similarity of each daily article to that anchor before weighting its contribution to the daily feature vector. This is a simple but effective way to make your mean-pooling more focused.

What Success Would Look Like

A realistic and economically meaningful result for this problem would be direction accuracy of 53–56% and a strategy Sharpe in the 0.8–1.5 range out-of-sample across walk-forward folds. Beating the 3.45 buy-and-hold Sharpe for TASI is a very high bar, especially during a sustained bull period (post-2020 through the Vision 2030 rally). The better framing is: does the strategy produce risk-adjusted returns that are statistically significantly different from zero, not that it beats buy-and-hold in a bull market. The t-test on your rolling strategy Sharpe across walk-forward folds will tell you much more than a single R² number.