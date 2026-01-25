# GitHub OpenCode Interface

- **Resolver**: Automatically resolve GitHub issues using AI (OpenCode + LLM).
- **Suggestor**: Automatically create follow-up issues on GitHub using AI.
- **Reviewer**: Create a report for a GitHub repo based on the opinion of 6 different AI reviewers.

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

## Workflow Diagrams

### Resolver

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

### Suggestor

```
┌──────────────────────────────────────────────────────────────────────┐
│                              [ START ]                               │
│                                  │                                   │
│                                  ▼                                   │
│                        [ SUGGEST-ISSUES ]                            │
│              generates up to N suggestions                           │
│                 outputs suggested_issues.json                        │
│                                  │                                   │
│                                  ▼                                   │
│               ┌───────────────────────────────────┐                  │
│               │     FOR EACH SUGGESTION (ARRAY)   │                  │
│               └───────────────────────────────────┘                  │
│                                  │                                   │
│                                  ▼                                   │
│                         [ REFINE-ISSUE ]                             │
│           validate, check duplicates (gh), refine content            │
│                                  │                                   │
│                                  ▼                                   │
│                         ┌───────────────┐                            │
│                         │ create == ?   │                            │
│                         └──────┬────────┘                            │
│                            false│true                                │
│                                 │                                    │
│     ┌──────────────────────┐    │   ┌──────────────────────────────┐ │
│     │        SKIP          │    │   │      gh issue create         │ │
│     │     (log reason)     │    │   └──────────────────────────────┘ │
│     └──────────────────────┘    │                                    │
│              │                  │                                    │
│              └──────────┬───────┘                                    │
│                         ▼                                            │
│                    (next item)                                       │
│                                  │                                   │
│                                  ▼                                   │
│                               [ END ]                                │
│                     output: created issue URLs                       │
└──────────────────────────────────────────────────────────────────────┘
```

### Review Reporter

```
┌──────────────────────────────────────────────────────────────────────┐
│                              START                                   │
│                                │                                     │
│                           [ SETUP ]                                  │
│                    validate + clone + context                        │
│                                │                                     │
│                 ┌──────────────┴──────────────┐                      │
│                 │   Branch exists remote?     │                      │
│                 └──────────────┬──────────────┘                      │
│                      YES       │        NO                           │
│                       │        │        │                            │
│                   checkout  create branch                            │
│                       │        │        │                            │
│                       └────────┴────────┘                            │
│                                │                                     │
│                        [ SECURITY-REPORT ]                           │
│                                │                                     │
│                          ┌─────┴─────┐                               │
│                        PASS        FAIL ──────────► [ ERROR ]        │
│                          │                            exit 1         │
│                          │                                           │
│                     [ ARCHITECTURE-REPORT ]                          │
│                          │                                           │
│                    ┌─────┴─────┐                                     │
│                  PASS        FAIL ──────────► [ ERROR ]              │
│                    │                            exit 1               │
│                    │                                                 │
│                  [ CUSTOMER-REPORT ]                                 │
│                    │                                                 │
│              ┌─────┴─────┐                                           │
│            PASS        FAIL ──────────► [ ERROR ]                    │
│              │                            exit 1                     │
│              │                                                       │
│            [ ENGINEERING-REPORT ]                                    │
│              │                                                       │
│        ┌─────┴─────┐                                                 │
│      PASS        FAIL ──────────► [ ERROR ]                          │
│        │                            exit 1                           │
│        │                                                             │
│      [ TESTING-REPORT ]                                              │
│        │                                                             │
│  ┌─────┴─────┐                                                       │
│ PASS       FAIL ──────────► [ ERROR ]                                │
│  │                            exit 1                                 │
│  │                                                                   │
│ [ RESOURCE-REPORT ]                                                  │
│  │                                                                   │
│  │                                                                   │
│ ┌┴────┐                                                              │
│ PASS FAIL ──────────► [ ERROR ]                                      │
│  │                      exit 1                                       │
│  │                                                                   │
│ [ AGGREGATION ]                                                      │
│ combine 6 reports                                                    │
│  │                                                                   │
│  │                                                                   │
│ ┌┴────┐                                                              │
│ PASS FAIL ──────────► [ ERROR ]                                      │
│  │                      exit 1                                       │
│  │                                                                   │
│ [ FINALIZATION ]                                                     │
│ commit + push + PR                                                   │
│  │                                                                   │
│ [ SUCCESS ]                                                          │
│  output: PR URL + report                                             │
└──────────────────────────────────────────────────────────────────────┘
```
