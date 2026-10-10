FROM ollama/ollama:latest

# Listen on all network interfaces, so other Render services can reach it
ENV OLLAMA_HOST=0.0.0.0:11434
# Keep the model in memory instead of unloading it after 5 minutes
ENV OLLAMA_KEEP_ALIVE=-1

# Download the model while building the image, so it never re-downloads on restart
RUN ollama serve & \
    pid=$! ; \
    for i in $(seq 1 30); do ollama list >/dev/null 2>&1 && break; sleep 1; done; \
    ollama pull gemma4:e2b; \
    kill $pid

EXPOSE 11434