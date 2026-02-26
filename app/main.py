from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import httpx

app = FastAPI()

NG_URL = "https://audio.ngfiles.com"

@app.get("/{song}")
async def proxy_mp3(song: str):
    target_url = f"{NG_URL}/{song}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(target_url, follow_redirects=True)
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Upstream request failed")

        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Song not found")

        content_type = response.headers.get("content-type", "")
        if "audio" not in content_type:
            raise HTTPException(status_code=400, detail="Not an audio file")

        return StreamingResponse(
            iter([response.content]),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'attachment; filename="{song}.mp3"'
            }
        )