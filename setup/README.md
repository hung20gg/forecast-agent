```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f setup/Dockerfile.vectordb-init \
  -t quanghung20gg/forecast-vectordb-init:v0.1 \
  setup/ \
  --push
```