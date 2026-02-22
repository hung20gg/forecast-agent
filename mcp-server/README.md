Build the image

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t quanghung20gg/forecast-mcp-server:v0.2 \
  . \
  --push
```