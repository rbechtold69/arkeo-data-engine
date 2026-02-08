# Skip Go Protocol — Arkeo Onboarding Guide

**Date:** 2026-02-08
**Status:** Arkeo is NOT yet listed on Skip Go

---

## 1. How Chains Get Added to Skip Go

Skip Go uses an **open-source registry** at **[skip-mev/skip-go-registry](https://github.com/skip-mev/skip-go-registry)**. The onboarding process is:

1. **Fork** the `skip-mev/skip-go-registry` repo
2. **Create** a folder `chains/<chain-id>/` (for Arkeo: `chains/arkeo-main-v1/`)
3. **Add** an `assetlist.json` file following their schema
4. **Submit a PR** to the main branch

That's it — no form, no application. It's a GitHub PR process, community-driven.

### Evidence
- PR #259 (Feb 2026): `restorenode` added `civitia-1` chain — just created `chains/civitia-1/assetlist.json`
- Each Cosmos chain folder contains a single `assetlist.json` file

---

## 2. What the `assetlist.json` Needs

Based on existing entries (e.g., `akashnet-2`), the file follows this schema:

```json
{
    "$schema": "../../assetlist.schema.json",
    "chain_name": "arkeo",
    "assets": [
        {
            "asset_type": "cosmos",
            "denom": "uarkeo",
            "coingecko_id": "arkeo",
            "recommended_symbol": "ARKEO"
        }
    ]
}
```

**Key fields:**
- `chain_name` — must match cosmos/chain-registry name (`arkeo`)
- `denom` — the native token denom (`uarkeo`)
- `coingecko_id` — CoinGecko listing ID (`arkeo`)
- `recommended_symbol` — display symbol
- Can also add IBC denoms for bridged assets on Arkeo

The schema file is at `assetlist.schema.json` in the repo root.

---

## 3. Prerequisites & Arkeo's Readiness

| Requirement | Status | Details |
|-------------|--------|---------|
| **Cosmos chain-registry entry** | ✅ Ready | `arkeo` exists in `cosmos/chain-registry` with full chain.json |
| **Chain ID** | ✅ Ready | `arkeo-main-v1` |
| **IBC to Osmosis** | ✅ Ready | channel-1 (Arkeo) ↔ channel-103074 (Osmosis) |
| **REST API** | ✅ Ready | https://rest-seed.arkeo.network |
| **RPC** | ✅ Ready | https://rpc-seed.arkeo.network |
| **CoinGecko listing** | ✅ Ready | `arkeo` on CoinGecko |
| **Active relayers** | ⚠️ Verify | Need to confirm IBC relayer is actively running |
| **Skip Go registry entry** | ❌ Missing | No `chains/arkeo-main-v1/` folder exists |

**Arkeo is ready for onboarding.** All core prerequisites are met.

---

## 4. What Skip Go Integration Enables

Once listed, Arkeo would be accessible via:
- **IBC routing** through Osmosis (the primary Cosmos DEX on Skip Go)
- **Cross-chain swaps** — users could swap any supported token to ARKEO
- **Skip Go Widget** — any dApp using the Skip Go widget would show Arkeo as a destination
- **skip.go app** (https://go.skip.build) — direct UI for cross-chain transfers

---

## 5. Contact Info

Skip Protocol rebranded to **Cosmos Labs** (cosmoslabs.io). Key channels:
- **GitHub:** https://github.com/skip-mev (still active under skip-mev org)
- **Discord:** Search for "Skip Protocol Discord" or "Cosmos Labs Discord"
- **Twitter/X:** @SkipProtocol
- **Docs:** https://docs.skip.build
- **For registry questions:** Open a GitHub issue on `skip-mev/skip-go-registry`

---

## 6. Timeline

Based on PR activity, community PRs are reviewed within **days to 1-2 weeks**. The civitia PR (#259) was opened Feb 5, 2026 and is still pending review as of Feb 8.

---

## 7. Action Items for Randy

### Immediate (can do today):
1. **Fork** `skip-mev/skip-go-registry`
2. **Create** `chains/arkeo-main-v1/assetlist.json` with content:
   ```json
   {
       "$schema": "../../assetlist.schema.json",
       "chain_name": "arkeo",
       "assets": [
           {
               "asset_type": "cosmos",
               "denom": "uarkeo",
               "coingecko_id": "arkeo",
               "recommended_symbol": "ARKEO"
           }
       ]
   }
   ```
3. **Submit PR** with title like `chore: add arkeo-main-v1 assetlist`
4. **Validate** the JSON against the repo's schema (run any CI checks)

### Optional enhancements:
- Add IBC-bridged assets on Arkeo (e.g., OSMO, ATOM if they exist)
- Reach out on Skip/Cosmos Labs Discord to expedite review
- Check the `assetlist.schema.json` for any additional optional fields worth filling

### Verify first:
- Confirm IBC relayer between Arkeo and Osmosis is actively maintained
- Test an IBC transfer Arkeo → Osmosis to confirm it works end-to-end
