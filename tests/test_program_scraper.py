import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pipeline.enrichment.program_scraper import scrape_program


@pytest.mark.asyncio
async def test_extracts_python():
    html = "<html><body><p>This course covers Python and Django</p></body></html>"
    mock_resp = MagicMock(text=html, raise_for_status=MagicMock(), is_redirect=False)
    with patch("pipeline.enrichment.program_scraper.httpx.AsyncClient") as mc:
        mc.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
        mc.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await scrape_program("https://example.com/program")
    assert "Python" in result
    assert "Django" in result


@pytest.mark.asyncio
async def test_no_java_from_javascript():
    html = "<html><body><p>Learn JavaScript and React</p></body></html>"
    mock_resp = MagicMock(text=html, raise_for_status=MagicMock(), is_redirect=False)
    with patch("pipeline.enrichment.program_scraper.httpx.AsyncClient") as mc:
        mc.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
        mc.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await scrape_program("https://example.com/program")
    assert "Java" not in result
    assert "JavaScript" in result
    assert "React" in result


@pytest.mark.asyncio
async def test_network_error_returns_empty():
    with patch("pipeline.enrichment.program_scraper.httpx.AsyncClient") as mc:
        mc.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(side_effect=Exception("timeout"))))
        mc.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await scrape_program("https://example.com/broken")
    assert result == []


@pytest.mark.asyncio
async def test_deduplicates():
    html = "<html><body><p>Python Python Python</p></body></html>"
    mock_resp = MagicMock(text=html, raise_for_status=MagicMock(), is_redirect=False)
    with patch("pipeline.enrichment.program_scraper.httpx.AsyncClient") as mc:
        mc.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
        mc.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await scrape_program("https://example.com/program")
    assert result.count("Python") == 1


@pytest.mark.asyncio
async def test_case_insensitive_match():
    html = "<html><body><p>We use python and DOCKER</p></body></html>"
    mock_resp = MagicMock(text=html, raise_for_status=MagicMock(), is_redirect=False)
    with patch("pipeline.enrichment.program_scraper.httpx.AsyncClient") as mc:
        mc.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
        mc.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await scrape_program("https://example.com/program")
    assert "Python" in result   # canonical casing, not "python"
    assert "Docker" in result   # canonical casing, not "DOCKER"
