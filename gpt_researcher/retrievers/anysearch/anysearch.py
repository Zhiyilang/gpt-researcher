# AnySearch Search Retriever for GPT Researcher
#
# AnySearch (https://anysearch.com) is search infrastructure built for AI
# agents: general web search, 23 vertical domains (finance, academic, security,
# legal, code, ...), parallel batch search and URL content extraction behind a
# single unified endpoint. The API key is optional -- anonymous traffic works
# with a lower rate limit -- so this retriever also runs with zero
# configuration, and degrades to an empty result list instead of raising.

import json
import logging
import os

import requests

API_URL = "https://api.anysearch.com/v1/search"

# AnySearch caps max_results at 10 (documented range 1-10).
_MAX_RESULTS_CAP = 10


class AnySearchSearch:
    """
    AnySearch API Retriever
    """

    # AnySearch returns cleaned page content inline whenever the source
    # provides it (its extract capability), so a separate scraping pass is
    # unnecessary.
    requires_scraping = False

    def __init__(self, query, headers=None, query_domains=None):
        """
        Initializes the AnySearchSearch object.

        Args:
            query (str): The search query string.
            headers (dict, optional): Accepted for interface parity with the
                other API retrievers; merged into the request headers.
            query_domains (list, optional): Unused -- AnySearch has no
                site-restriction parameter. Kept so the retriever can be
                constructed uniformly with the others.

        Environment variables (all optional):
            ANYSEARCH_API_KEY   API key. Omit for anonymous access.
            ANYSEARCH_TAG       Vertical-domain tag, e.g. "code.doc".
                                See https://www.anysearch.com/docs/api-endpoints
            ANYSEARCH_PARAMS    JSON object with the tag's required params,
                                e.g. {"library": "golang"} for code.doc.
            ANYSEARCH_ZONE      "cn" or "intl".
            ANYSEARCH_LANGUAGE  e.g. "zh-CN" or "en".
            ANYSEARCH_FORMAT    "markdown" (default) or "json" -- controls the
                                format of the returned content field.
        """
        self.query = query
        self.query_domains = query_domains or None
        self.api_key = self.get_api_key()
        self.headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
        if headers:
            self.headers.update(headers)

    def get_api_key(self):
        """
        AnySearch works anonymously, so a missing key is not an error.
        """
        return os.environ.get("ANYSEARCH_API_KEY")

    def _build_payload(self, max_results):
        """Assemble the request body, including optional vertical-domain
        routing from environment configuration."""
        try:
            count = int(max_results)
        except (TypeError, ValueError):
            count = 7
        count = max(1, min(count, _MAX_RESULTS_CAP))

        payload = {
            "query": self.query,
            "max_results": count,
            # markdown keeps the cleaned page content readable for the LLM
            "format": os.environ.get("ANYSEARCH_FORMAT", "markdown"),
        }

        tag = os.environ.get("ANYSEARCH_TAG")
        if tag:
            payload["tag"] = tag
            raw_params = os.environ.get("ANYSEARCH_PARAMS")
            if raw_params:
                try:
                    params = json.loads(raw_params)
                except ValueError:
                    logging.getLogger(__name__).warning(
                        "ANYSEARCH_PARAMS is not valid JSON (%r); ignoring.", raw_params
                    )
                else:
                    if isinstance(params, dict):
                        payload["params"] = params

        zone = os.environ.get("ANYSEARCH_ZONE")
        if zone:
            payload["zone"] = zone

        language = os.environ.get("ANYSEARCH_LANGUAGE")
        if language:
            payload["language"] = language

        return payload

    def search(self, max_results=7) -> list[dict]:
        """
        Searches the query through the AnySearch unified search endpoint.

        Returns:
            list[dict]: Normalized results, one dict per hit:
                {"title": str, "href": str, "body": str}
            ``body`` prefers AnySearch's cleaned page content (the extract
            capability) and falls back to the snippet.
        """
        try:
            response = requests.post(
                API_URL,
                headers=self.headers,
                json=self._build_payload(max_results),
                timeout=30,
            )
            response.raise_for_status()
            json_response = response.json()
        except (requests.RequestException, ValueError) as e:
            logging.getLogger(__name__).warning(
                f"Error: {e}. Failed fetching sources. Resulting in empty response."
            )
            return []

        # AnySearch answers HTTP 200 with a business envelope; code != 0 is an
        # error even on 200 (e.g. an invalid vertical tag).
        if not isinstance(json_response, dict) or json_response.get("code") != 0:
            logging.getLogger(__name__).warning(
                "AnySearch returned a non-success envelope: %s",
                json_response.get("message") if isinstance(json_response, dict) else json_response,
            )
            return []

        data = json_response.get("data") or {}
        results = data.get("results") or []
        if not isinstance(results, list):
            return []

        search_results = []
        for result in results:
            if not isinstance(result, dict):
                continue
            href = result.get("url") or ""
            if not href:
                continue
            search_results.append(
                {
                    "title": result.get("title") or "",
                    "href": href,
                    "body": result.get("content") or result.get("snippet") or "",
                }
            )

        return search_results
