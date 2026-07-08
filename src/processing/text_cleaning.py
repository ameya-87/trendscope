import os
import re
import pandas as pd
import unicodedata
from datetime import datetime
from typing import Optional

URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
HASHTAG_TOKEN_PATTERN = re.compile(r"(^|\s)#\w+")
EMOJI_PATTERN = re.compile("[" \
    u"\U0001F600-\U0001F64F"  # emoticons \
    u"\U0001F300-\U0001F5FF"  # symbols & pictographs \
    u"\U0001F680-\U0001F6FF"  # transport & map symbols \
    u"\U0001F1E0-\U0001F1FF"  # flags (iOS) \
    u"\U00002500-\U00002BEF"  # chinese char \
    u"\U00002702-\U000027B0" \
    u"\U000024C2-\U0001F251" \
    "]+", flags=re.UNICODE)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def normalize_text(text: str) -> str:
    """Apply Unicode normalization (NFKC)."""
    return unicodedata.normalize("NFKC", text)


def remove_urls(text: str) -> str:
    return URL_PATTERN.sub(" ", text)


def remove_html(text: str) -> str:
    return HTML_TAG_PATTERN.sub(" ", text)


def remove_emojis(text: str) -> str:
    return EMOJI_PATTERN.sub(" ", text)


def remove_hashtags(text: str) -> str:
    """Remove hashtag tokens entirely (e.g., '#AI' is removed)."""
    # Replace hashtag tokens with a space
    return HASHTAG_TOKEN_PATTERN.sub(" ", text)


def clean_text(text: Optional[str]) -> str:
    """
    End-to-end cleaning: normalize -> strip HTML -> strip URLs -> strip emojis -> strip hashtags -> lowercase -> collapse spaces.
    """
    if text is None:
        return ""
    s = str(text)
    s = normalize_text(s)
    s = remove_html(s)
    s = remove_urls(s)
    s = remove_emojis(s)
    s = remove_hashtags(s)
    s = s.lower()
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def clean_dataframe(df: pd.DataFrame, text_column: str = "text", output_column: str = "cleaned_text") -> pd.DataFrame:
    """
    Add a cleaned text column to the DataFrame.
    If text_column is missing, creates an empty cleaned column.
    """
    if text_column in df.columns:
        df[output_column] = df[text_column].apply(clean_text)
    else:
        df[output_column] = ""
    return df


def process_and_save(input_csv_path: str, output_csv_path: str | None = None, text_column: str = "text") -> str:
    """
    Load a raw CSV with a unified schema that includes a 'text' column,
    apply cleaning, and save to data/processed (or provided path).
    Returns the path to the cleaned CSV.
    """
    df = pd.read_csv(input_csv_path)
    df = clean_dataframe(df, text_column=text_column, output_column="cleaned_text")

    if output_csv_path is None:
        _ensure_dir(os.path.join("data", "processed"))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_csv_path = os.path.join("data", "processed", f"cleaned_text_{ts}.csv")

    df.to_csv(output_csv_path, index=False)
    return output_csv_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Clean text in a unified schema CSV.")
    parser.add_argument("input", help="Path to input CSV (expects a 'text' column)")
    parser.add_argument("--text_column", default="text", help="Name of text column to clean")
    parser.add_argument("--output", default=None, help="Optional output CSV path")
    args = parser.parse_args()

    out = process_and_save(args.input, output_csv_path=args.output, text_column=args.text_column)
    print(f"✅ Cleaned text saved to {out}")