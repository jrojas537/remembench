import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from app.adapters.web_search import WebSearchAdapter
from app.schemas import ImpactEventCreate

@pytest.fixture
def adapter():
    with patch('app.adapters.web_search.settings') as mock_settings:
        mock_settings.tavily_api_key = "test_tavily"
        mock_settings.exa_api_key = "test_exa"
        return WebSearchAdapter()

@pytest.mark.anyio
async def test_web_search_tavily_success(adapter):
    """Test standard flow where Tavily yields structured output."""
    mock_tavily = AsyncMock()
    mock_tavily.search.return_value = {
        "results": [
            {
                "title": "Major snow storm in Detroit",
                "content": "A massive system closed all roads",
                "url": "http://test.com/news"
            }
        ]
    }
    adapter.tavily_client = mock_tavily
    
    events = await adapter.fetch_events(
        start_date=datetime(2026, 2, 10),
        end_date=datetime(2026, 2, 15),
        industry="pizza_full_service",
        geo_label="Detroit"
    )
    
    assert len(events) == 1
    assert type(events[0]) == ImpactEventCreate
    assert events[0].source == "web_search_tavily"
    assert "Major snow storm" in events[0].description
    mock_tavily.search.assert_called_once()

@pytest.mark.anyio
async def test_web_search_tavily_fails_fallback_duckduckgo(adapter):
    """Test chain-of-responsibility fallback to DDG."""
    # Tavily fails
    mock_tavily = AsyncMock()
    mock_tavily.search.side_effect = Exception("Tavily Outage")
    adapter.tavily_client = mock_tavily
    
    # Exa fails
    adapter.exa_client = None 

    # DDG succeeds
    mock_ddg = AsyncMock()
    mock_ddg.text.return_value = [
         {
             "title": "Pizza delivery halted",
             "body": "No deliveries today.",
             "href": "http://ddg.test/1"
         }
    ]
    adapter.ddgs = mock_ddg
    
    events = await adapter.fetch_events(
        start_date=datetime(2026, 2, 10),
        end_date=datetime(2026, 2, 15),
        industry="pizza_full_service",
        geo_label="Detroit"
    )
    
    assert len(events) == 1
    assert events[0].source == "web_search_duckduckgo"
    mock_tavily.search.assert_called_once()
    mock_ddg.text.assert_called_once()
