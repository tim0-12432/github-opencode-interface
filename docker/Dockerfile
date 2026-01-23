FROM node:25-bookworm

# Install minimal additional tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    jq \
    git \
    ca-certificates \
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

# Copy orchestrator and prompts
COPY docker/scripts/orchestrator.sh /usr/local/bin/orchestrator
COPY docker/prompts/ /prompts/

# Copy opencode config directory
COPY docker/opencode/ /root/.config/opencode/
COPY auth.json /root/.local/share/opencode/auth.json

RUN chmod +x /usr/local/bin/orchestrator

ENTRYPOINT ["/usr/local/bin/orchestrator"]
