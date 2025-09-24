# Video Assets (NGINX)

This service is a lightweight NGINX container that serves MP4 files produced by the Python service.  
Files are written to a shared Docker volume and exposed over HTTP at `/videos/<id>.mp4`.

## Structure
```
assets/
├─ Dockerfile             # builds nginx with our config
└─ nginx/
   └─ assets.conf         # nginx config
```

## Build & Run (standalone test)
```bash
docker build -t video-assets ./assets
docker volume create video_files
docker run --rm -d -p 8080:80   -v video_files:/srv/assets:ro   video-assets
```
Now any file in `video_files` is served at:
```
http://localhost:8080/videos/<file>.mp4
```

## Usage in Compose
Example excerpt from `docker-compose.yml`:
```yaml
volumes:
  video_files: {}

services:
  video-producer:
    build: .
    environment:
      - OUTPUT_DIR=/data/videos
      - ASSETS_PUBLIC_URL=http://video-assets
    volumes:
      - video_files:/data

  video-assets:
    build: ./assets
    volumes:
      - video_files:/srv/assets:ro
```
- Producer writes to `/data/videos/<id>.mp4`
- NGINX serves at `http://video-assets/videos/<id>.mp4`

## Notes
- Always write to `.mp4.part` then rename to `.mp4` (atomic publish).
- Use unique filenames (UUID/hash) so caching works without conflicts.
- For dev, open in browser: `http://localhost:8080/videos/test.mp4`
