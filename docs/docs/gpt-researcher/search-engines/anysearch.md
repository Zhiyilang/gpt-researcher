# AnySearch

[AnySearch](https://anysearch.com) is search infrastructure built for AI agents: general web search, 23 vertical domains (finance, academic, security, legal, code, ...), parallel batch search and URL content extraction behind one unified endpoint.

Unlike the other API retrievers in this list, AnySearch **works without an API key** — anonymous traffic is rate-limited per IP and consumes the daily free quota. A free API key (1000 requests/day, 2000 after verification) raises the limits. Get one at [anysearch.com/console/api-keys](https://www.anysearch.com/console/api-keys).

## Usage

```bash
# .env — optional; without it the retriever runs anonymously
ANYSEARCH_API_KEY=as_sk_...

# optional vertical-domain routing (see the API reference)
ANYSEARCH_TAG=code.doc
ANYSEARCH_PARAMS={"library": "golang"}
# optional region / language
ANYSEARCH_ZONE=intl
ANYSEARCH_LANGUAGE=en
```

```python
from gpt_researcher import GPTResearcher

researcher = GPTResearcher(
    query="What changed in Go 1.26?",
    report_type="research_report",
)
```

Or select it explicitly:

```bash
RETRIEVER=anysearch python -m gpt_researcher.cli "What changed in Go 1.26?"
```

Mix it with other retrievers:

```bash
RETRIEVER=tavily,anysearch
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANYSEARCH_API_KEY` | No | API key. Omit for anonymous access (lower rate limits). |
| `ANYSEARCH_TAG` | No | Vertical-domain tag, e.g. `code.doc`, `finance.news`. Each tag may require extra params (see below). |
| `ANYSEARCH_PARAMS` | No | JSON object with the tag's required params, e.g. `{"library": "golang"}` for `code.doc`, `{"type": "stock"}` for `finance.news`. |
| `ANYSEARCH_ZONE` | No | `cn` or `intl`. |
| `ANYSEARCH_LANGUAGE` | No | e.g. `zh-CN` or `en`. |
| `ANYSEARCH_FORMAT` | No | `markdown` (default) or `json` — format of the returned `content` field. |

## What you get

Each hit is normalized to the standard retriever shape:

```python
{"title": str, "href": str, "body": str}
```

`body` prefers AnySearch's cleaned page content (its extract capability — that is why `requires_scraping` is `False` for this retriever) and falls back to the snippet when the source provides no content.

## Notes

- `max_results` is clamped to AnySearch's documented range of 1–10.
- Errors (network, HTTP, quota, invalid tag) degrade to an empty result list with a warning instead of raising, matching the behaviour of the other API retrievers.
- API reference: [POST /v1/search](https://www.anysearch.com/docs/api-endpoints/v1-search) · [POST /v1/extract](https://www.anysearch.com/docs/api-endpoints/v1-extract) · [GET /v1/sub-domains](https://www.anysearch.com/docs/api-endpoints/v1-sub-domains).
