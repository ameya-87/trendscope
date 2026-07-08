import os
from datetime import datetime
from typing import Tuple, List
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def load_cleaned_text(csv_path: str, text_column: str = "cleaned_text") -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if text_column not in df.columns:
        raise ValueError(f"Input CSV must contain '{text_column}' column.")
    return df


def build_tfidf(texts: List[str], max_features: int = 5000) -> Tuple[TfidfVectorizer, any]:
    vec = TfidfVectorizer(stop_words="english", max_features=max_features)
    X = vec.fit_transform(texts)
    return vec, X


def run_kmeans(X, n_clusters: int = 5, random_state: int = 42) -> KMeans:
    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=random_state)
    km.fit(X)
    return km


def extract_top_terms(vec: TfidfVectorizer, km: KMeans, top_n: int = 10) -> pd.DataFrame:
    terms = vec.get_feature_names_out()
    centers = km.cluster_centers_
    rows = []
    for cid, center in enumerate(centers):
        top_idx = center.argsort()[::-1][:top_n]
        top_terms = [terms[i] for i in top_idx]
        rows.append({"cluster": cid, "top_terms": ", ".join(top_terms)})
    return pd.DataFrame(rows)


def assign_clusters(df: pd.DataFrame, km: KMeans, X, id_columns: List[str] | None = None) -> pd.DataFrame:
    labels = km.predict(X)
    out = df.copy()
    out["cluster"] = labels
    # Keep common identification columns if present
    if id_columns:
        for c in id_columns:
            if c not in out.columns:
                out[c] = None
    return out


def process_topics(input_csv_path: str, text_column: str = "cleaned_text", n_clusters: int = 5, top_n: int = 10) -> Tuple[str, str]:
    """
    End-to-end topic modeling:
      1) Load cleaned text CSV
      2) Build TF-IDF
      3) KMeans clustering
      4) Save cluster top terms and per-row cluster assignments to data/processed
    Returns: (topics_terms_csv, topics_assignments_csv)
    """
    df = load_cleaned_text(input_csv_path, text_column=text_column)
    texts = df[text_column].fillna("").astype(str).tolist()

    vec, X = build_tfidf(texts)
    km = run_kmeans(X, n_clusters=n_clusters)

    topics_df = extract_top_terms(vec, km, top_n=top_n)
    assignments_df = assign_clusters(df, km, X, id_columns=["source", "keyword", "published_at"]) if isinstance(df, pd.DataFrame) else pd.DataFrame()

    _ensure_dir(os.path.join("data", "processed"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    topics_path = os.path.join("data", "processed", f"topics_terms_{ts}.csv")
    assigns_path = os.path.join("data", "processed", f"topics_assignments_{ts}.csv")

    topics_df.to_csv(topics_path, index=False)
    assignments_df.to_csv(assigns_path, index=False)

    return topics_path, assigns_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run topic modeling over cleaned text CSV.")
    parser.add_argument("input", help="Path to cleaned text CSV (expects 'cleaned_text' column)")
    parser.add_argument("--clusters", type=int, default=5, help="Number of clusters (default: 5)")
    parser.add_argument("--top_n", type=int, default=10, help="Top terms per cluster (default: 10)")
    parser.add_argument("--text_column", default="cleaned_text", help="Text column name (default: cleaned_text)")
    args = parser.parse_args()

    t_path, a_path = process_topics(args.input, text_column=args.text_column, n_clusters=args.clusters, top_n=args.top_n)
    print(f"✅ Topics terms saved to {t_path}")
    print(f"✅ Topic assignments saved to {a_path}")