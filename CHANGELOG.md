# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- pytest smoke tests for token tracker + 6-agent registry
- GitHub Actions CI workflow (Python 3.11 + 3.12 matrix)
- Ruff linting in CI
- Badges in README (CI, Python, license, MiMo-powered)
- CONTRIBUTING.md with PR workflow

## [0.1.0] - 2026-05-26

### Added
- FastAPI gateway with 6 endpoints
- 6 MEV detection agents: sandwich, frontrun, JIT, atomic-arb, liquidation, synthesis
- Multi-chain mempool monitoring scaffold (Ethereum, Base, Arbitrum, Optimism)
- Per-agent token tracker with SQLite persistence
- WebSocket alert feed scaffold
- Real-run artifact: 50-block Ethereum window, 287 candidate txs, 8M tokens, 10 attacks
- Architecture diagram in `docs/ARCHITECTURE.md`
- Application draft in `docs/MIMO_APPLICATION.md`
- Dockerfile for production deploy
