from textblob import TextBlob


class SentimentAnalyzer:
    def score(self, text):
        if not text or not text.strip():
            return 0.0
        blob = TextBlob(str(text))
        return round(blob.sentiment.polarity, 2)