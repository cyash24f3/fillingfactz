from pydantic import BaseModel, ConfigDict, Field

from filing_checker.documents import list_filings
from filing_checker.models import VerdictCandidate
from filing_checker.retrieval import (
    search_filings,
    read_passage,
    read_page_context,
)
import re

from filing_checker.context_views import compact_passage


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoArguments(ToolArguments):
    pass


class SearchArguments(ToolArguments):
    query: str = Field(min_length=1, max_length=400)
    filing_id: str | None = None
    per_filing: int = Field(default=1, ge=1, le=3)


class SearchAndReadArguments(SearchArguments):
    additional_queries: list[str] = Field(default_factory=list, max_length=2)


class ReadArguments(ToolArguments):
    passage_id: str = Field(min_length=1)


class PageContextArguments(ToolArguments):
    filing_id: str = Field(min_length=1)
    pdf_page: int = Field(ge=1)


def list_filing_records():
    return {"filings": list_filings()}


def read_passage_record(passage_id):
    passage = read_passage(passage_id)

    return {
        "passage": compact_passage(passage),
        "read_passage_ids": [passage.passage_id],
    }


QUERY_STOP_WORDS = set(
    """
    a an the and or of to in on at by for from with
    is are was were be been being has have had
    do does did not no as this that
    crowdstrike holdings inc company
    latest most recent recently reported approximately exactly
    """.split()
)


def clean_query(query):
    words = re.findall(
        r"[A-Za-z0-9]+",
        query.casefold(),
    )

    relevant = [word for word in words if word not in QUERY_STOP_WORDS]

    return " ".join(relevant) or query


def search_and_read(
    query,
    filing_id=None,
    per_filing=1,
    additional_queries=None,
):
    queries = list(dict.fromkeys(
        clean_query(value) for value in [query, *(additional_queries or [])]
    ))
    scores = {}
    matches = {}
    searched = []
    for value in queries:
        found = search_filings(
            query=value,
            filing_id=filing_id,
            per_filing=3 if len(queries) > 1 else per_filing,
        )
        searched = list(dict.fromkeys([*searched, *found["searched_filings"]]))
        ranks = {}
        for match in found["matches"]:
            fid = match["filing_id"]
            ranks[fid] = ranks.get(fid, 0) + 1
            pid = match["passage_id"]
            matches[pid] = match
            # Reward agreement across query variants without comparing
            # query-dependent BM25 score magnitudes.
            scores[pid] = scores.get(pid, 0) + 1 / (60 + ranks[fid])

    selected = []
    for fid in searched:
        ranked = sorted(
            (pid for pid in matches if matches[pid]["filing_id"] == fid),
            key=lambda pid: scores[pid],
            reverse=True,
        )
        selected.extend(ranked[:per_filing])
    passages = [read_passage(pid) for pid in selected]

    return {
        "query": queries[0],
        "queries": queries,
        "searched_filings": searched,
        "read_passage_ids": [passage.passage_id for passage in passages],
        "passages": [compact_passage(passage) for passage in passages],
    }


TOOLS = {
    "list_filings": {
        "description": (
            "List the supplied filings, their IDs, reporting periods, and filing dates."
        ),
        "arguments": NoArguments,
        "handler": list_filing_records,
    },
    "search_filings": {
        "description": (
            "Search the supplied filings using topic keywords. "
            "Leave filing_id empty to search every filing. "
            "Results contain passage IDs and navigation snippets. "
            "Read full passages before citing them."
        ),
        "arguments": SearchArguments,
        "handler": search_filings,
    },
    "read_passage": {
        "description": (
            "Read a complete source passage using an ID returned by search_filings."
        ),
        "arguments": ReadArguments,
        "handler": read_passage_record,
    },
}

TOOLS["list_filings"]["expose"] = False
TOOLS["search_filings"]["expose"] = False

TOOLS["search_and_read"] = {
    "description": (
        "Search filings and return complete source passages "
        "in one operation. Omit filing_id to search all filings. "
        "Default: one passage per filing. "
        "Optional additional_queries are fused before selecting passages. "
        "Returned passages count as read."
    ),
    "arguments": SearchAndReadArguments,
    "handler": search_and_read,
}

TOOLS["read_page_context"] = {
    "description": (
        "Read page-heading chunks from a PDF page and its neighbours to resolve "
        "table units, column dates, and tables continued across pages. Returns "
        "other passage IDs for navigation; read those separately before citing."
    ),
    "arguments": PageContextArguments,
    "handler": read_page_context,
}


def tool_schemas():
    schemas = []

    for name, specification in TOOLS.items():
        if not specification.get("expose", True):
            continue
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": specification["description"],
                    "parameters": (specification["arguments"].model_json_schema()),
                },
            }
        )

    schemas.append(
        {
            "type": "function",
            "function": {
                "name": "submit_verdict",
                "description": (
                    "Submit the final verdict after researching "
                    "the statement. Cite passage IDs already read "
                    "and copy supporting quotations. "
                    "For current claims supported by an earlier filing "
                    "but superseded by a later filing, choose OUTDATED "
                    "and cite both periods. Respect explicitly historical claims. "
                    "Call this alone, without other tools in "
                    "the same response."
                ),
                "parameters": VerdictCandidate.model_json_schema(),
            },
        }
    )

    return schemas


def execute_tool(name, arguments):
    if name not in TOOLS:
        raise ValueError("Unknown tool: " + name)

    specification = TOOLS[name]

    checked = specification["arguments"].model_validate(
        arguments,
        strict=True,
    )

    return specification["handler"](**checked.model_dump())
