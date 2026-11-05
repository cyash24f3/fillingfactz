import json

from filing_checker.retrieval import (
    search_filings,
    read_passage,
)


if __name__ == "__main__":
    results = search_filings(
        "fiscal year ends January 31",
        per_filing=1,
    )

    print(json.dumps(results, indent=2))

    if results["matches"]:
        first_id = results["matches"][0]["passage_id"]
        passage = read_passage(first_id)

        print("\nFULL PASSAGE:")
        print(
            json.dumps(
                passage.model_dump(mode="json"),
                indent=2,
                ensure_ascii=False,
            )
        )
