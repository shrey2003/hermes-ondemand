"""Internet Agent API web-search provider for Hermes."""

from plugins.web.internet_agent.provider import InternetAgentWebSearchProvider


def register(ctx) -> None:
    """Register the Internet Agent API as Hermes's ``web_search`` backend."""
    ctx.register_web_search_provider(InternetAgentWebSearchProvider())
