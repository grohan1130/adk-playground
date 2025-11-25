"""Weather and time tool functions for ADK agents."""
import datetime
from zoneinfo import ZoneInfo


def get_weather(city: str) -> dict:
    """Retrieves current weather for a city.

    Args:
        city: Name of the city to get weather for.

    Returns:
        Dictionary with status and weather report or error message.
    """
    if city.lower() == "new york":
        return {
            "status": "success",
            "report": "The weather in New York is sunny with a temperature of 25 degrees Celsius (77 degrees Fahrenheit)."
        }
    elif city.lower() == "san francisco":
        return {
            "status": "success",
            "report": "The weather in San Francisco is foggy with a temperature of 18 degrees Celsius (64 degrees Fahrenheit)."
        }
    elif city.lower() == "london":
        return {
            "status": "success",
            "report": "The weather in London is rainy with a temperature of 12 degrees Celsius (54 degrees Fahrenheit)."
        }
    else:
        return {
            "status": "error",
            "error_message": f"Weather information for '{city}' is not available."
        }


def get_current_time(city: str) -> dict:
    """Returns current time in specified city.

    Args:
        city: Name of the city to get time for.

    Returns:
        Dictionary with status and time report or error message.
    """
    timezone_map = {
        "new york": "America/New_York",
        "san francisco": "America/Los_Angeles",
        "london": "Europe/London",
        "tokyo": "Asia/Tokyo",
        "paris": "Europe/Paris"
    }

    city_lower = city.lower()
    if city_lower in timezone_map:
        tz_identifier = timezone_map[city_lower]
    else:
        return {
            "status": "error",
            "error_message": f"Sorry, I don't have timezone information for {city}."
        }

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    report = f'The current time in {city} is {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}'
    return {"status": "success", "report": report}
