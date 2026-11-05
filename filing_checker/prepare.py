import json

from filing_checker.ingestion import prepare_corpus


if __name__ == "__main__":
    result = prepare_corpus()

    print(json.dumps(result, indent=2))
