Front end

Use any OpenAI-compatible client to interact with the backend server.

In this case, we use [Open WebUI](https://github.com/open-webui/open-webui) as an example.

Docker command:

Pull the latest image:

```bash
docker pull ghcr.io/open-webui/open-webui:main-slim
```

Run the container with the backend server:

```bash
docker run -d -p 3000:8080 -v open-webui:/app/backend/data -e OFFLINE_MODE=true -e HF_HUB_OFFLINE=1 --name open-webui ghcr.io/open-webui/open-webui:main-slim
```





