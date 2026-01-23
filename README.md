# GitHub OpenCode Interface

- **Resolver**: Automatically resolve GitHub issues using AI (OpenCode + LLM).

## Quick Start

```bash
# 1. Clone
git clone https://github.com/yourorg/github-issue-resolver.git
cd github-issue-resolver

# 2. Configure
cp config.env.example config.env
# Edit config.env with your tokens

# 3. Copy auth
cp /.local/share/opencode/auth.json auth.json

# 4. Run
./resolve.py owner/repo 123
```

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          START                                  │
│                            │                                    │
│              ┌─────────────┴─────────────┐                      │
│              │   Branch exists remote?   │                      │
│              └─────────────┬─────────────┘                      │
│                   YES      │      NO                            │
│                    │       │       │                            │
│              checkout   create new branch                       │
│                    │       │       │                            │
│                    └───────┴───────┘                            │
│                            │                                    │
│                      [ ANALYZE ]                                │
│                            │                                    │
│                     [ IMPLEMENT ] ◄─────────────────┐           │
│                            │                        │           │
│                       [ TEST ]                      │           │
│                            │                        │           │
│                    ┌───────┴───────┐                │           │
│                   PASS           FAIL               │           │
│                    │          (5x max)              │           │
│                    │               │                │           │
│                    │         [ FIX-TESTS ]──►loop   │           │
│                    │               │                │           │
│                    │          FAIL 5x               │           │
│                    │               │                │           │
│                    │        ┌──────┴───────┐        │           │
│                    │        │   PARTIAL    │        │           │
│                    │        │  commit+push │        │           │
│                    │        │  +comment    │        │           │
│                    │        └──────────────┘        │           │
│                    │                                │           │
│                 [ REVIEW ]                          │           │
│                    │                                │           │
│              ┌─────┴─────┐                          │           │
│            PASS        FAIL ────────────────────────┘           │
│              │       (2x max)                                   │
│              │           │                                      │
│              │      FAIL 2x                                     │
│              │           │                                      │
│              │    ┌──────┴──────┐                               │
│              │    │   PARTIAL   │                               │
│              │    └─────────────┘                               │
│              │                                                  │
│         [ SUCCESS ]                                             │
│         commit+PR+comment                                       │
└─────────────────────────────────────────────────────────────────┘
```
