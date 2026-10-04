"""Offline TF-IDF embeddings used when the Hugging Face model is unavailable."""

from sklearn.feature_extraction.text import TfidfVectorizer
from langchain_core.embeddings import Embeddings


class TfidfEmbeddings(Embeddings):
    """Adapt a fitted scikit-learn vectorizer to LangChain's embeddings interface."""

    def __init__(self, vectorizer: TfidfVectorizer):
        self.vectorizer = vectorizer

    @classmethod
    def fit(cls, texts: list[str]) -> "TfidfEmbeddings":
        # Character n-grams preserve distinctions such as MSE-I vs MSE-II and
        # tolerate small wording differences between a question and a table.
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
        vectorizer.fit(texts)
        return cls(vectorizer)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.vectorizer.transform(texts).toarray().tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.vectorizer.transform([text]).toarray()[0].tolist()
