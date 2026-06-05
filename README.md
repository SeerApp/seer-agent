# Seer Agent

Comprehensive tool and skill context for agents building on Solana. 

**Problem**: AI agents are trained on a massive amount of web2 data. Things are different for web3. 

A lot of domain knowledge remains siloed among developers who have struggled hard to discover it. 

Broken Anchor builds. Broken Solana CLI builds. Known exploit vectors. An agent has to rediscover those every time it begins work. 

Where it lacks coding knowledge, it makes extrapolations from web2 training data, leading to dangerous security assumptions and poor architectural decisions. 

Where it lacks tooling knowledge, it burns tokens rediscovering (sometimes obvious) information by browsing the internet.

**Solution**: A Hermes agent plugin with a unified knowledge base covering the "solved" questions in Solana development. 

## What It Is

A unified, open-source agentic context of Solana tools, codebases, edge-cases, exploits, and best practices.

## What It Is Not

Seer Agent is not a replacement for good judgement, informative spec, and clear requirements. 

## Features

### Comprehensive Knowledge of Tooling

Seer Agent knows all of the best tools to use for various use-cases when working on Solana. Whether it is well-known open-source libraries like LiteSVM, infrastructure services like Helius, or advanced debugging solutions like the Seer debugger. 

It knows when each tool is appropriate, where to find the docs, and how to use it.

### Comprehensive Knowledge of Codebases

Seer Agent doesn't have to guess about the behaviour of dependencies. If it is unsure, it will download relevant git repositories, inspect them, analyse them, and base decision on empirical knowldge.

### Comprehensive Knowledge of Security

Seer Agent can compare ongoing work against well-known security exploits to ensure safety.

## Installation

```
hermes plugins install SeerApp/seer-agent
hermes plugins enable seer-agent
```

## Contributing

If you are: 

- A developer with knowledge of a specific edge-case
- A member of a team working on an important and useful product
- An agentic developer who has struggled with agentic development on Solana
- A security researcher with insight into best practices

We invite you to open an issue on this repo. 

How should your insight be integrated into the Solana developer agent of the future? 

## Tests

From the plugin root:

```bash
uv run pytest
```

