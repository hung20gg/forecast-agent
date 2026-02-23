```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t quanghung20gg/forecast-vectordb-init:v0.1 \
  setup/ \
  --push
```