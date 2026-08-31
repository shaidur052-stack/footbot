"""LLM generation. The ONLY file that knows which provider we use."""

import time
from google import genai
from google.genai import errors
from app.config import GEMINI_API_KEY, GEMINI_MODEL

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Add it to backend/.env as:\n"
        "GEMINI_API_KEY=your_key_here"
    )

client = genai.Client(api_key=GEMINI_API_KEY)

# If the primary model is overloaded, fall through this list.
FALLBACK_MODELS = [
    GEMINI_MODEL,
    "models/gemini-3.5-flash-lite",
    "models/gemini-2.0-flash",
]


def generate(prompt: str) -> str:
    """One-shot generation with retry + model fallback on 503."""
    last_error = None

    for model in FALLBACK_MODELS:
        for attempt in range(2):                  # two tries per model
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                return response.text
            except errors.ServerError as e:       # 503 / overloaded — retry
                last_error = e
                time.sleep(1.5)
            except errors.ClientError:            # 404 / bad key — pointless to retry
                raise

    raise RuntimeError(f"All models unavailable. Last error: {last_error}")


def generate_stream(prompt: str):
    """Yields text chunks. Same retry/fallback policy as generate().

    Transport errors are caught alongside API errors: Gemini sometimes drops
    the connection mid-stream (httpx.RemoteProtocolError), which is neither a
    ServerError nor a ClientError and previously escaped the retry loop and
    killed the request.
    """
    import httpx

    last_error = None

    for model in FALLBACK_MODELS:
        try:
            stream = client.models.generate_content_stream(
                model=model,
                contents=prompt,
            )
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
            return                                # finished cleanly

        except errors.ServerError as e:           # overloaded — try next model
            last_error = e
            time.sleep(1.5)
        except (httpx.RemoteProtocolError, httpx.ReadError,
                httpx.ConnectError, httpx.ReadTimeout) as e:
            # Connection dropped. Almost always transient; retrying the same
            # model usually succeeds.
            last_error = e
            time.sleep(1.0)
        except errors.ClientError:                # bad key/model — don't retry
            raise

    raise RuntimeError(f"All models unavailable. Last error: {last_error}")