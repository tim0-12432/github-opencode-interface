# Using Trixie because of Python3.13 compatibility
FROM node:25-trixie

# Install minimal additional tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    jq \
    git \
    ca-certificates \
    golang-go \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip python3-rich python3-github \
    && rm -rf /var/lib/apt/lists/*

# Install OpenCode
RUN curl -fsSL https://opencode.ai/install | bash

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Set up workspace
WORKDIR /workspace

# Copy Python orchestrator and library
COPY docker/scripts/ /usr/lib/python3/dist-packages/github_opencode_interface/
COPY docker/prompts/ /prompts/

# Create orchestrator entry point
RUN echo '#!/bin/bash\npython3 -m github_opencode_interface.orchestrator "$@"' > /usr/local/bin/orchestrator \
    && chmod +x /usr/local/bin/orchestrator

# Copy opencode config directory
COPY docker/opencode/ /root/.config/opencode/
COPY auth.json /root/.local/share/opencode/auth.json

ENTRYPOINT ["/usr/local/bin/orchestrator"]
