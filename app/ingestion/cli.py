from app.ingestion.indexer import build_index


if __name__ == "__main__":
    count = build_index()
    print(f"Indexed {count} chunks.")
