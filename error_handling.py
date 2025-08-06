import logging
from typing import Optional
import aiohttp
import discord
import trio
from config import config_manager


class BotError(Exception):
    """Base exception class for bot-related errors"""
    pass


class APIError(BotError):
    """Exception raised for API-related errors"""
    pass


async def safe_query(api_client, prompt: str) -> Optional[str]:
    """
    Wrapper for API queries with proper error handling and retries
    """
    max_retries = config_manager.config["max_retries"]
    retry_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            response = await api_client.query(prompt)
            if response:
                return response
            raise APIError("Empty response received")

        except aiohttp.ClientResponseError as e:
            logging.error(f"API error (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                raise APIError(f"Failed after {max_retries} attempts")

        except aiohttp.ClientConnectionError:
            logging.error(f"Connection error (attempt {attempt + 1}/{max_retries})")
            if attempt == max_retries - 1:
                raise APIError(f"Failed to connect after {max_retries} attempts")

        await trio.sleep(retry_delay * (attempt + 1))  # Exponential backoff

    return None