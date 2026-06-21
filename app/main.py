from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import httpx

app = FastAPI()

NG_URL = "https://audio.ngfiles.com"
CHUNK_SIZE = 64 * 1024


@app.get("/{song:path}")
async def proxy_mp3(song: str):
    if ".." in song:
        raise HTTPException(status_code=400, detail="Invalid path")

    target_url = f"{NG_URL}/{song}"

    client = httpx.AsyncClient(timeout=30.0)
    try:
        req = client.build_request("GET", target_url)
        resp = await client.send(req, stream=True, follow_redirects=True)
    except httpx.RequestError:
        await client.aclose()
        raise HTTPException(status_code=502, detail="Upstream request failed")

    if resp.status_code != 200:
        await resp.aclose()
        await client.aclose()
        raise HTTPException(status_code=404, detail="Song not found")

    content_type = resp.headers.get("content-type", "")
    if "audio" not in content_type and "mpeg" not in content_type:
        await resp.aclose()
        await client.aclose()
        raise HTTPException(status_code=400, detail="Not an audio file")

    content_length = resp.headers.get("content-length")
    filename = song.rsplit("/", 1)[-1]

    async def stream(response, client):
        try:
            async for chunk in response.aiter_bytes(chunk_size=CHUNK_SIZE):
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    resp_headers = {
        "Content-Disposition": f'attachment; filename="{filename}.mp3"',
    }
    if content_length:
        resp_headers["content-length"] = content_length

    return StreamingResponse(
        stream(resp, client),
        media_type="audio/mpeg",
        headers=resp_headers,
    )