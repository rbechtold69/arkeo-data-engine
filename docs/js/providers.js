// Shared KNOWN_PROVIDERS config — single source of truth
// Used by index.html, subscribe.html, provider.html
// Last verified: 2026-02-11

const KNOWN_PROVIDERS = {
  // Liquify - 2 services, ONLINE
  'arkeopub1addwnpepqdgt6w2qqkt4jydfud507nl740gxeag7gaaj5hzc8w7x9p0ka8ln6e8kkvk': {
    name: 'Liquify',
    description: 'Professional blockchain infrastructure provider',
    website: 'https://liquify.com',
    location: 'Europe',
  },
  // Arkeo Core Provider - 5 services, ONLINE
  'arkeopub1addwnpepq22m27n5ryy787muswzjqjk0k9k7lfp4hlcxe4hywpa97plfag5gcsh0983': {
    name: 'Arkeo Core Provider',
    description: 'Arkeo Core Provider for primary development and support',
    website: 'https://arkeo.network',
    location: 'Americas',
  },
  // Everstake - 6 services, ONLINE
  'arkeopub1addwnpepqdnr9x5c386meywavzmy5wa2xfwkn26j26az9ll6kfn6ez6ytp7kvht860d': {
    name: 'Everstake',
    description: 'Enterprise-grade staking infrastructure',
    website: 'https://everstake.one',
    location: 'Europe',
  },
  // Stake Village (IP-based) - 6 services, ONLINE
  'arkeopub1addwnpepqvj8mevcpdamq9cp5478t8k36tpmc7tfa536m989vanh9kp88qsvggzjm5t': {
    name: 'Stake Village',
    description: 'Validator and infrastructure provider',
    website: 'https://stakevillage.net',
    location: 'Europe',
  },
  // Stake Village (domain-based) - 3 services, ONLINE
  'arkeopub1addwnpepq2lmfqggxp29nj3ekl3ltxncv79y4yen55p2wvqqky6asnkqh5l0yjn2kfd': {
    name: 'Stake Village',
    description: 'Validator and infrastructure provider',
    website: 'https://stakevillage.net',
    location: 'Europe',
  },
  // Nodefleet - 3 services, ONLINE
  'arkeopub1addwnpepqgvlg57udnpwh4y6k7yedt6pnfd0gutcqkkzu5w2xmyp6vtwkjhs7ge3rv7': {
    name: 'Nodefleet.org',
    description: 'Blockchain node infrastructure services',
    website: 'https://nodefleet.org',
    location: 'Americas',
  },
  // Roomit - 2 services, ONLINE
  'arkeopub1addwnpepqduv5lky7ckq8efzzu08rm62ml6mvahjv6y87agfk8wvhqcz5xhdguz8zyg': {
    name: 'Roomit',
    description: 'Blockchain infrastructure provider',
    website: 'https://roomit.xyz',
    location: 'Asia',
  },
  // 0xFury - 2 services, ONLINE
  'arkeopub1addwnpepqdvlra44yykhmmpwtfavs35a5w6h8xqtuceedkuxur6v0gs8yfxa59h7wnm': {
    name: '0xFury',
    description: 'Enterprise-grade blockchain infrastructure solutions',
    website: 'https://0xfury.com',
    location: 'Europe',
  },
  // Red_5 entries removed — clean slate for re-registration
  // Innovation Theory (port 3638) - 2 services, ONLINE
  'arkeopub1addwnpepqdc6phgk8vqky8v7vyyyk0zck0696nne4lpg66r0ju9yvh98ksgm76dh5ez': {
    name: 'Innovation Theory',
    description: 'Blockchain infrastructure provider',
    website: 'https://innovationtheory.com',
    location: 'Americas',
  },
  // Innovation Theory Node (port 3636) - 3 services, ONLINE
  'arkeopub1addwnpepqfn52r6xng2wwfrgz2tm5yvscq42k3yu3ky9cg3kw5s6p0qg7tfx75uwq3z': {
    name: 'Innovation Theory Node',
    description: 'Blockchain node infrastructure',
    website: 'https://innovationtheory.com',
    location: 'Americas',
  },
  // HODL Validators - 2 services, ONLINE
  'arkeopub1addwnpepqwm4225stataymep57cs5y0waw3fhnr67w4e940kpk5jek26en3qxym33wg': {
    name: 'HODL Validators',
    description: 'Staking and infrastructure services',
    website: 'https://hodl.validators.online',
    location: 'Europe',
  },
  // Provider 178.208 - 1 service, ONLINE (unreachable metadata)
  'arkeopub1addwnpepqg3lll0dt65suhu4e7hx898rytl9902gw28dupfyfglx5l74an8sc4kvj92': {
    name: 'Provider 178.208',
    description: 'Arkeo data provider',
    location: 'Unknown',
  },
  // Nodes Guru - 2 services, ONLINE (unreachable metadata)
  'arkeopub1addwnpepqdt79h8767429wpr44gxwavca708rmx8fhf4gxrfp86pqkf30kch7g3j4q5': {
    name: 'Nodes Guru',
    description: 'Professional node infrastructure',
    website: 'https://nodes.guru',
    location: 'Europe',
  },
};

// Helper: find a matching KNOWN_PROVIDERS entry by pubkey (handles prefix matching)
function findKnownProvider(pubkey) {
  if (KNOWN_PROVIDERS[pubkey]) return KNOWN_PROVIDERS[pubkey];
  const match = Object.keys(KNOWN_PROVIDERS).find(k =>
    k.startsWith(pubkey.slice(0, 40)) || pubkey.startsWith(k.slice(0, 40))
  );
  return match ? KNOWN_PROVIDERS[match] : null;
}
