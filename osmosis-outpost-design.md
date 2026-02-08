# Osmosis Outpost Design: USDC → ARKEO Auto-Swap

**Date:** 2026-02-08
**Status:** Research & Design
**Author:** Clawd (research for Randy)

---

## Executive Summary

This document explores approaches for enabling users to pay for Arkeo data contracts using USDC, with automatic conversion to ARKEO via Osmosis. After evaluating four approaches, **Skip Go API integration** is the recommended path — it requires zero governance, zero contract deployment, and can be built in days.

---

## 1. IBC Channel Status ✅

**Arkeo ↔ Osmosis IBC is live and active.**

| Direction | Channel ID | Connection |
|-----------|-----------|------------|
| Arkeo → Osmosis | `channel-1` | `connection-2` |
| Osmosis → Arkeo | `channel-103074` | `connection-10730` |

- Client: `07-tendermint-1` (Arkeo side) / `07-tendermint-3489` (Osmosis side)
- Protocol: `ics20-1` (standard token transfer)
- Status: **ACTIVE** (preferred channel per chain registry)

Arkeo also has IBC channels to other chains (12 total channels on Arkeo), but the Osmosis channel is the primary one relevant here.

---

## 2. Osmosis CosmWasm Status

**CosmWasm is enabled on Osmosis** and supports smart contract deployment. However:

- **Deployment is permissioned** — contract code uploads require **governance approval** (on-chain proposal)
- Osmosis uses a whitelist approach; you cannot permissionlessly upload arbitrary wasm
- Once a code ID is approved, anyone can instantiate contracts from it
- Tools: `osmosisd` CLI or Beaker framework
- Osmosis also has a native `x/cosmwasmpool` module for CosmWasm-powered liquidity pools

**Implication:** Deploying a custom outpost contract on Osmosis requires an on-chain governance proposal, which takes ~5 days voting period and needs community support.

---

## 3. Osmosis IBC Capabilities

From Skip API chain data, Osmosis supports:

| Capability | Status |
|-----------|--------|
| **Packet Forward Middleware (PFM)** | ✅ Enabled |
| **IBC Hooks** | ✅ Enabled |
| **Memo support** | ✅ Enabled |
| **Authz** | ✅ Enabled |

This is critical — IBC Hooks on Osmosis means incoming IBC transfers can trigger contract execution automatically.

---

## 4. Arkeo IBC Capabilities

**Arkeo does NOT appear in Skip's chain registry**, which means:

- ❌ **No PFM** on Arkeo (not confirmed in Skip's DB)
- ❌ **No IBC Hooks** on Arkeo (likely not compiled in)
- ✅ **Memo support** — standard IBC memo field works
- ❌ **No CosmWasm** on Arkeo (it's a custom Cosmos SDK chain focused on data provider marketplace)

**Implication:** We cannot do the "ideal" multi-hop PFM flow (send from Arkeo → swap on Osmosis → return to Arkeo in one tx). The swap must be initiated from the Osmosis side or orchestrated by an off-chain service.

---

## 5. Approach Comparison

### Approach A: Custom CosmWasm Outpost Contract on Osmosis

**How it works:**
```
User sends USDC to outpost contract on Osmosis
  → Contract swaps USDC → ARKEO on pool #2977
  → Contract IBC-transfers ARKEO to user's arkeo1... address
  → User has ARKEO on Arkeo chain
```

**Pros:**
- Fully on-chain, trustless
- One transaction from user's perspective (on Osmosis)
- Can add custom logic (slippage protection, fee collection)

**Cons:**
- ⚠️ Requires Osmosis **governance proposal** to upload code
- 2-4 weeks for governance + voting
- Needs Phil/team involvement for proposal credibility
- Ongoing maintenance burden
- Cannot auto-open Arkeo contracts (Arkeo has no IBC hooks to receive contract calls)

**Complexity:** High | **Timeline:** 4-8 weeks

---

### Approach B: IBC Hooks (Osmosis Swaprouter)

**How it works:**
Osmosis has a built-in **Swaprouter** contract that can be triggered via IBC Hooks. If you send tokens to Osmosis with the right memo, it auto-swaps and forwards.

```
User on any chain with IBC Hooks
  → IBC transfer USDC to Osmosis with memo:
    {"wasm": {"contract": "<swaprouter>", "msg": {"osmosis_swap": {...}}}}
  → Swaprouter swaps USDC → ARKEO
  → Swaprouter IBC-transfers ARKEO to user on Arkeo
```

**Pros:**
- Uses existing Osmosis infrastructure (no new contract needed!)
- Swaprouter is already deployed and governance-approved
- Works from any IBC Hooks-enabled chain

**Cons:**
- ⚠️ Arkeo doesn't have IBC Hooks, so this can't be initiated FROM Arkeo
- Must be initiated from a chain that HAS IBC Hooks (Osmosis, Noble, etc.)
- User needs USDC on Osmosis (or a chain with hooks → Osmosis)
- Swaprouter contract address needs to be verified

**Complexity:** Medium | **Timeline:** 1-2 weeks (integration only)

---

### Approach C: Skip Go API (⭐ RECOMMENDED)

**How it works:**
Skip Go API provides cross-chain swap routing. It handles the entire USDC → ARKEO conversion path automatically.

```
Frontend/backend calls Skip Go API:
  1. GET /v2/fungible/route — get optimal route
  2. GET /v2/fungible/msgs — get transaction messages
  3. User signs and broadcasts the transaction
  4. Skip handles multi-hop routing automatically
```

**Skip's Cosmos support includes:**
- Osmosis DEX swaps ✅
- IBC transfers ✅
- PFM multi-hop ✅
- CCTP for USDC bridging ✅

**Architecture:**
```
┌─────────────────────────────────────────────────┐
│                  Data Engine UI                   │
│           "Pay with USDC" button                  │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│              Skip Go API                          │
│  Route: USDC (any chain) → ARKEO (Arkeo chain)  │
│  Steps: IBC → Osmosis Swap → IBC to Arkeo       │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌──────────┐  IBC   ┌──────────┐  IBC   ┌────────┐
│  Noble   │───────▶│ Osmosis  │───────▶│ Arkeo  │
│  (USDC)  │        │ Pool#2977│        │        │
└──────────┘        │USDC→ARKEO│        │  User  │
                    └──────────┘        │ wallet │
                                        └────────┘
```

**Pros:**
- ✅ **No governance needed** — uses existing infrastructure
- ✅ **No contract deployment** — purely API integration
- ✅ Works from ANY chain Skip supports (Ethereum, Cosmos, Solana via CCTP)
- ✅ Skip handles routing, slippage, error recovery
- ✅ Battle-tested infrastructure (used by Osmosis frontend, Keplr, etc.)
- ✅ Can be done entirely by Randy/dev team, no Phil needed
- ✅ Free API (with optional API key for higher limits)

**Cons:**
- Dependency on Skip as a service (but they're the standard in Cosmos)
- ⚠️ Arkeo may not be in Skip's chain registry yet (needs verification/onboarding)
- User still needs to sign a separate tx to open Arkeo data contracts after receiving ARKEO
- Skip takes a small fee on routes (configurable)

**If Arkeo isn't in Skip yet:**
- Skip onboarding for new Cosmos chains is straightforward
- Requires: chain registry entry ✅ (Arkeo is in cosmos/chain-registry), IBC channels ✅, active relayers ✅
- Can request addition via Skip Discord or GitHub

**Complexity:** Low | **Timeline:** 3-7 days (if Arkeo is supported) or 2-4 weeks (if onboarding needed)

---

### Approach D: Off-Chain Relay Service

**How it works:**
Build a simple backend service that:
1. Monitors an Osmosis wallet for incoming USDC
2. Swaps USDC → ARKEO on pool #2977
3. IBC transfers ARKEO to the sender's Arkeo address (parsed from memo)

```
User sends USDC to osmo1<relay-address> with memo: "arkeo1<their-address>"
  → Relay detects deposit
  → Relay swaps on Osmosis DEX
  → Relay IBC transfers ARKEO to user
```

**Pros:**
- No governance needed
- Full control over logic
- Can add Arkeo contract opening in the future

**Cons:**
- ⚠️ Centralized / custodial (relay holds funds briefly)
- Needs operational infrastructure (monitoring, error handling)
- Trust requirement
- Hot wallet security concerns

**Complexity:** Medium | **Timeline:** 1-2 weeks

---

## 6. Recommended Approach: Skip Go API

### Why Skip?

1. **Zero governance overhead** — no proposals, no waiting
2. **Zero infrastructure** — no contracts to deploy or maintain
3. **Maximum reach** — users can pay from Ethereum, Cosmos, or anywhere Skip supports
4. **Battle-tested** — Skip powers the routing for Osmosis.zone, Keplr wallet, and dozens of other frontends
5. **Randy can build it alone** — no dependency on Phil or Arkeo governance

### Implementation Plan

#### Phase 1: Verify Skip Support (Day 1)
- [ ] Check if Arkeo (`arkeo-main-v1`) is in Skip's supported chains
- [ ] If not: submit onboarding request to Skip team (Discord/GitHub)
- [ ] Test route: `USDC (Noble) → ARKEO (Arkeo)` via Skip API

```bash
# Test route query
curl "https://api.skip.build/v2/fungible/route" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "source_asset_denom": "uusdc",
    "source_asset_chain_id": "noble-1",
    "dest_asset_denom": "uarkeo",
    "dest_asset_chain_id": "arkeo-main-v1",
    "amount_in": "10000000"
  }'
```

#### Phase 2: Frontend Integration (Days 2-5)
- [ ] Add Skip Go client library (`@skip-go/client`)
- [ ] Build "Pay with USDC" flow in data engine UI
- [ ] Handle wallet connection (Keplr/Leap)
- [ ] Display route preview (fees, estimated ARKEO received)
- [ ] Execute transaction and track status

#### Phase 3: End-to-End Flow (Days 5-7)
- [ ] User clicks "Open Data Contract" → sees ARKEO cost
- [ ] User clicks "Pay with USDC" → Skip route calculated
- [ ] User approves tx → USDC swapped → ARKEO arrives on Arkeo
- [ ] User then opens the data contract with their ARKEO
- [ ] (Future: automate the contract-opening step)

### Future Enhancement: Auto-Open Contracts

The two-step flow (swap → open contract) could be collapsed if:
1. **Arkeo adds IBC Hooks** — then an incoming IBC transfer could trigger contract opening
2. **Arkeo adds ICA (Interchain Accounts)** — then Osmosis could send instructions to Arkeo
3. **Backend service** — watches for ARKEO arrivals and auto-opens contracts

This is a Phase 2 optimization. Phase 1 works with the two-step flow.

---

## 7. Pool #2977 Status

The ARKEO/USDC pool on Osmosis (pool #2977) needs to be verified for:
- [ ] Sufficient liquidity for expected swap volumes
- [ ] Current spread/slippage at various amounts ($10, $100, $1000)
- [ ] Whether it's a concentrated liquidity pool or classic

Check: `https://app.osmosis.zone/pool/2977`

---

## 8. Risks & Limitations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Arkeo not in Skip registry | Medium | Submit onboarding request; fallback to Approach B or D |
| Pool #2977 low liquidity | Medium | Monitor liquidity; set max slippage; could incentivize LPs |
| IBC transfer delays | Low | Standard ~30s for Cosmos IBC; show status tracking |
| Skip API downtime | Low | Skip has high uptime; could add fallback to direct Osmosis swap |
| Two-step UX (swap then open contract) | Medium | Clear UI guidance; future: auto-open via IBC hooks |
| USDC depegging | Low | Standard stablecoin risk; not specific to this design |

---

## 9. What Can Be Done Without Phil/Governance

| Task | Needs Phil? | Needs Governance? |
|------|-------------|-------------------|
| Skip API integration | ❌ No | ❌ No |
| Frontend "Pay with USDC" | ❌ No | ❌ No |
| Verify pool #2977 liquidity | ❌ No | ❌ No |
| Skip chain onboarding (if needed) | ❌ No | ❌ No |
| Custom outpost contract | ✅ Yes (credibility) | ✅ Yes (Osmosis gov) |
| Adding IBC Hooks to Arkeo | ✅ Yes (chain upgrade) | ✅ Yes (Arkeo gov) |
| Adding PFM to Arkeo | ✅ Yes (chain upgrade) | ✅ Yes (Arkeo gov) |

**Bottom line:** The Skip API approach can be fully implemented by Randy without any external dependencies.

---

## 10. Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|-------------|
| Skip API verification | 1 day | None |
| Skip onboarding (if needed) | 1-3 weeks | Skip team |
| Frontend integration | 3-5 days | Skip support confirmed |
| Testing & polish | 2-3 days | Frontend done |
| **Total (best case)** | **~1 week** | Arkeo already in Skip |
| **Total (worst case)** | **~4 weeks** | Need Skip onboarding |

---

## Appendix A: Key Resources

- **Skip Go API Docs:** https://docs.skip.build/go/general/getting-started
- **Skip Go Client (npm):** `@skip-go/client`
- **Osmosis Pool #2977:** https://app.osmosis.zone/pool/2977
- **Arkeo Chain Registry:** https://github.com/cosmos/chain-registry/tree/master/arkeo
- **IBC Channel (Arkeo↔Osmosis):** channel-1 / channel-103074
- **Osmosis CosmWasm Docs:** https://docs.osmosis.zone/cosmwasm/

## Appendix B: Alternative — Osmosis Swaprouter via IBC Hooks

If Skip doesn't work out, the Osmosis Swaprouter is the next best option. This contract is already deployed on Osmosis and can be triggered via IBC memo hooks. The flow would be:

1. User has USDC on Noble (or Osmosis)
2. IBC transfer to Osmosis with wasm execute memo targeting swaprouter
3. Swaprouter swaps USDC → ARKEO
4. Swaprouter forwards ARKEO via IBC to Arkeo chain

This requires finding the current swaprouter contract address on Osmosis and building the correct memo format. No governance needed since the contract already exists.

## Appendix C: Osmosis IBC Hooks Memo Format

```json
{
  "wasm": {
    "contract": "osmo1<swaprouter-address>",
    "msg": {
      "osmosis_swap": {
        "output_denom": "ibc/<ARKEO_ON_OSMOSIS_DENOM>",
        "slippage": {
          "twap": {
            "slippage_percentage": "5",
            "window_seconds": 10
          }
        },
        "receiver": "osmo1...",
        "on_failed_delivery": "do_nothing",
        "next_memo": {
          "forward": {
            "receiver": "arkeo1...",
            "port": "transfer",
            "channel": "channel-103074"
          }
        }
      }
    }
  }
}
```
