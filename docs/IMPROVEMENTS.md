# Arkeo Marketplace Improvements

This document tracks improvements made to the Arkeo marketplace compared to the original implementation.

## ✅ Implemented

### Architecture
- **Centralized Configuration** (`js/config.js`)
  - All settings in one place
  - Feature flags for easy toggling
  - Frozen object to prevent accidental modification

- **Utility Library** (`js/utils.js`)
  - Reusable caching system with TTL
  - Error handling with toast notifications
  - Formatting helpers (ARKEO, addresses, dates)
  - API wrapper with automatic caching
  - DOM utilities

### Performance
- **Smart Caching**
  - LocalStorage caching with configurable TTL
  - Cache-first loading with fallback to API
  - Shows cached data when offline

- **Auto-Refresh**
  - Data refreshes every 30 seconds
  - Only refreshes when tab is visible
  - Clears cache before refresh for fresh data

### UX Improvements
- **Mobile Responsive**
  - Tablet breakpoint (1024px)
  - Mobile breakpoint (768px)
  - Small mobile breakpoint (380px)
  - Touch-friendly interactions
  - Reduced motion support

- **Error Handling**
  - Global error boundary
  - Toast notifications for errors
  - Graceful fallback to cached data
  - Retry buttons on failure

- **Accessibility**
  - Semantic HTML
  - Proper meta tags
  - Theme color for mobile browsers
  - Open Graph tags for sharing

### New Features
- **Marketplace Momentum Section**
  - Top providers earnings chart
  - Time range filters
  - Visual demonstration of marketplace activity

- **Provider Wizards**
  - Step-by-step provider onboarding
  - Keplr wallet integration
  - Real blockchain transactions

## 🔜 Planned

### Architecture
- [ ] Split into modular components
- [ ] TypeScript migration
- [ ] Unit tests
- [ ] E2E tests

### Performance
- [ ] WebSocket real-time updates
- [ ] Lazy-load chain icons
- [ ] Service worker for offline support
- [ ] Image optimization

### Features
- [ ] Provider details page
- [ ] Contract history view
- [ ] Earnings calculator
- [ ] Provider comparison tool
- [ ] Alert notifications
- [ ] Dark/light mode toggle

### Integration
- [ ] Connect to directory backend for real earnings data
- [ ] Mobile app deep linking
- [ ] Wallet connect support (beyond Keplr)

---

## 🚨 Issues to Discuss with Phil

### 1. Directory Service Centralization (HIGH PRIORITY)
**Problem:** The directory service (earnings, transactions, provider stats) is a single point of failure.
- If Phil's directory goes down, marketplace loses aggregated data
- Only one operator currently runs the indexer
- Frontend depends on this for real-time stats

**Proposed Solutions:**
1. **Public API endpoint** — Expose directory API publicly so others can build on it
2. **Multiple operators** — Let anyone run a directory instance (already open source)
3. **Decentralized indexing** — Consider The Graph or similar
4. **Marketplace failover** — Query multiple directories, use cached data if all fail

**Questions for Phil:**
- Is there a public directory API endpoint we can use?
- Can we run our own directory instance for redundancy?
- What's the plan for decentralizing this?

### 2. Provider Metadata CORS
**Problem:** Browser can't fetch provider metadata directly (CORS blocks HTTP requests)
**Current workaround:** Pre-cached known provider metadata
**Better solution:** Directory should aggregate and serve provider metadata

---

## 🪙 Tokenomics Roadmap

### ✅ Implemented Now
- **ARKEO Payment Discount (15%)** — Pay with ARKEO = 15% more requests vs USDC
- **Burn Counter** — Dashboard shows total ARKEO burned (visible commitment to deflation)
- **Provider Visibility by Bond** — Higher bond = better placement in marketplace

### 🔜 Phase 2 (Next Sprint)
- **Burn Mechanism** — 1-2% of each transaction burned
- **Staking Rewards Display** — Show APY for staking ARKEO
- **Fee Sharing** — Stakers earn % of marketplace fees

### 🚀 Phase 3 (Future)
- **Premium Features** — Stake ARKEO to unlock analytics, priority support
- **Referral Program** — Earn ARKEO for onboarding providers/subscribers
- **Governance Integration** — Stake to vote on marketplace parameters
- **Buyback & Burn** — Marketplace takes small fee, buys ARKEO, burns it

### x402 AI Agent Synergy
- AI agents pay per-request in ARKEO (constant demand)
- Every agent request = micro-burn
- Agent volume scales with AI adoption = organic buy pressure

---

*Last updated: February 7, 2026*
