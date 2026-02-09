# Marketplace V2 — Response & Production Plan

Thanks for the thorough review, Phil. You're right on several points and this alignment is exactly what's needed to move fast. Here's where I agree, where I'd clarify, and the plan to get V2 live.

---

## Where You're Spot On

**Transactions & Earnings are estimated.** Correct — derived from contract nonce × rates, not a live indexer. Will add prominent "Estimated" badges.

**Reputation scores are browser-side heuristics.** Yes — weighted composite of on-chain bond, contracts, service count. Transparent and real data, but not a network consensus metric.

**No payment backend.** Correct. Discovery and onboarding layer today, not transaction execution.

**CORS on provider metadata.** Real issue. Pre-cached for 6 verified providers as workaround. The directory API solves this.

**x402 not integrated into PAYG.** Correct. The x402 proxy on Red_5 is a parallel payment path proving USDC works. It bypasses native contracts/arkauth.

---

## Clarifications

**"Subscribe wizard displays random contract IDs."** The wizard pulls real on-chain contract data from the REST API. Contract IDs are actual chain values. Happy to dig into any specific fields that look off.

**"x402 live demo uses hardcoded output."** The x402 proxy (161.35.97.215:3637) is live infrastructure — systemd service, Coinbase CDP facilitator, real USDC on Base mainnet. The UI shows a sample response for display (executing a paid request from a static page needs wallet interaction), but the backend is real and tested.

**"Business logic not auditable."** Entire codebase is open source on GitHub. That said, production should have an authoritative backend — agreed.

---

## What's Live Today

| Feature | Status | Source |
|---------|--------|--------|
| Provider discovery | ✅ Live | REST API (`/arkeo/providers`) |
| Service listings | ✅ Live | REST API (`/arkeo/services`) |
| Contract data | ✅ Live | REST API (`/arkeo/contracts`) with full pagination |
| Provider metadata | ⚠️ Pre-cached | CORS workaround for 6 verified providers |
| Bond amounts | ✅ Live | On-chain |
| Transaction/Earnings | ⚠️ Estimated | Derived from contract nonce × rates |
| Reputation scores | ⚠️ Heuristic | Weighted on-chain metrics |
| x402 proxy (Red_5) | ✅ Live | Real USDC payments, Base mainnet |
| PAYG contract execution | ❌ Not implemented | Needs arkauth + backend |
| Wallet transactions | 🎭 Demo | Keplr prompts work, not submitted |

---

## Production Plan

### Now: Launch-Ready Fixes (This Week)
I'm handling these immediately. No blockers.

| Item | Description |
|------|-------------|
| **SSL on x402 endpoint** | Reverse proxy with Let's Encrypt on Red_5. Fixes mixed-content. |
| **Prominent "Estimated" labels** | Clear badges on transactions, earnings, reputation. |
| **Subscribe wizard audit** | Verify all displayed data maps to real on-chain values. |
| **Remove/gate demo features** | Wallet interactions that don't execute get clearly marked. |
| **Mobile responsiveness** | Quick audit for phone/tablet. |

### Needed from Phil: Directory API
**This is the one blocker.** A public metadata/metrics endpoint that:
- Serves provider metadata without CORS issues
- Provides authoritative transaction/metrics data
- Replaces pre-cached workarounds with live data

Once I have this, V2 goes live and replaces V1 as the public marketplace. This is what I'll be using for all provider and subscriber outreach going forward.

### Next: Live Payments
Once V2 is live with real discovery, these are the next builds:

| Item | Description |
|------|-------------|
| **USDC Gateway (Option A)** | Payment verification → ARKEO contract funding → arkauth signing. Full USDC payment loop. |
| **Arkauth signing service** | Signs per-request arkauth on behalf of subscribers. |
| **Contract manager** | Opens, tops up, closes PAYG contracts programmatically. |
| **Transaction indexer** | Replaces estimated metrics with real on-chain history. |

### Ongoing: AI Agent Marketplace
| Item | Description |
|------|-------------|
| **x402 Bazaar registration** | Arkeo listed on Coinbase's discovery layer for AI agents. |
| **MCP server** | AI agents discover and use Arkeo natively. |
| **Multi-provider x402** | Extend x402 beyond Red_5 to all providers. |

---

## Bottom Line

The V2 marketplace has real discovery pulling live chain data, provider profiles, onboarding wizards, and a working x402 proof of concept. The current V1 isn't something I can put in front of providers and subscribers for BD. V2 is.

I'm executing the launch-ready fixes now. The directory API is the one thing needed from the core team to make this complete. Once that's in place, V2 goes live.

Your Option A architecture for the USDC gateway is the right production path for payments. The x402 proof of concept on Red_5 validates the demand. We build from here.
