import * as secp from '@noble/secp256k1';
import { sha256 } from '@noble/hashes/sha256';
import { ripemd160 } from '@noble/hashes/ripemd160';
import { hmac } from '@noble/hashes/hmac';

if (secp.etc && secp.etc.hmacSha256Sync === undefined) {
  secp.etc.hmacSha256Sync = (key, ...msgs) => hmac(sha256, key, secp.etc.concatBytes(...msgs));
}

const CONTRACT_ID = process.argv[2] || '942';
const PRIVATE_KEY = process.argv[3] || '';
const SENTINEL = 'https://red5-arkeo.duckdns.org';
const SERVICE = 'arkeo-mainnet-fullnode';

if (!PRIVATE_KEY) { console.log('Usage: node demo.mjs <contract_id> <private_key_hex>'); process.exit(1); }

function hexToBytes(hex) { const b = new Uint8Array(hex.length / 2); for (let i = 0; i < b.length; i++) b[i] = parseInt(hex.substr(i * 2, 2), 16); return b; }
function bytesToHex(bytes) { return Array.from(bytes, b => b.toString(16).padStart(2, '0')).join(''); }

function bech32Encode(prefix, data) {
  const CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l';
  const GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3];
  function polymod(values) { let chk = 1; for (const v of values) { const top = chk >> 25; chk = ((chk & 0x1ffffff) << 5) ^ v; for (let i = 0; i < 5; i++) if ((top >> i) & 1) chk ^= GEN[i]; } return chk; }
  const hrpExp = []; for (let i = 0; i < prefix.length; i++) hrpExp.push(prefix.charCodeAt(i) >> 5); hrpExp.push(0); for (let i = 0; i < prefix.length; i++) hrpExp.push(prefix.charCodeAt(i) & 31);
  const words = []; let acc = 0, bits = 0; for (const b of data) { acc = (acc << 8) | b; bits += 8; while (bits >= 5) { bits -= 5; words.push((acc >> bits) & 31); } } if (bits > 0) words.push((acc << (5 - bits)) & 31);
  const values = hrpExp.concat(words).concat([0,0,0,0,0,0]); const mod = polymod(values) ^ 1; const cs = []; for (let i = 0; i < 6; i++) cs.push((mod >> (5*(5-i))) & 31);
  return prefix + '1' + words.concat(cs).map(v => CHARSET[v]).join('');
}

let nonce = 0;

const privKeyBytes = hexToBytes(PRIVATE_KEY);
const pubKeyBytes = secp.getPublicKey(privKeyBytes, true);
const amino = new Uint8Array(38);
amino[0]=0xeb;amino[1]=0x5a;amino[2]=0xe9;amino[3]=0x87;amino[4]=0x21;
amino.set(pubKeyBytes, 5);
const pubKeyBech32 = bech32Encode('arkeopub', amino);
const addr = bech32Encode('arkeo', ripemd160(sha256(pubKeyBytes)));

async function signedQuery(path, method = 'GET', body = null) {
  nonce++;
  const preimage = CONTRACT_ID + ':' + pubKeyBech32 + ':' + nonce;
  const signDoc = JSON.stringify({account_number:"0",chain_id:"",fee:{amount:[],gas:"0"},memo:"",msgs:[{type:"sign/MsgSignData",value:{data:Buffer.from(preimage).toString('base64'),signer:addr}}],sequence:"0"});
  const msgHash = sha256(new TextEncoder().encode(signDoc));
  const sig = secp.sign(msgHash, privKeyBytes);
  let sigBytes = sig.toCompactRawBytes();
  
  const N = BigInt('0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141');
  const s = BigInt('0x' + bytesToHex(sigBytes.slice(32)));
  if (s > N / 2n) {
    const newS = N - s;
    const newSHex = newS.toString(16).padStart(64, '0');
    const newSBytes = hexToBytes(newSHex);
    const normalized = new Uint8Array(64);
    normalized.set(sigBytes.slice(0, 32));
    normalized.set(newSBytes, 32);
    sigBytes = normalized;
  }
  
  const sigBase64 = Buffer.from(sigBytes).toString('base64');
  const pubBase64 = Buffer.from(pubKeyBytes).toString('base64');
  const arkauth = `${pubBase64}:${sigBase64}:${preimage}:${nonce}`;
  
  const url = `${SENTINEL}/${SERVICE}${path}`;
  const opts = { headers: { 'X-Arkauth': arkauth } };
  if (method === 'POST' && body) {
    opts.method = 'POST';
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const resp = await fetch(url, opts);
  const text = await resp.text();
  try { return { status: resp.status, data: JSON.parse(text) }; }
  catch { return { status: resp.status, data: text }; }
}

console.log('');
console.log('╔══════════════════════════════════════════════╗');
console.log('║     🚀 ARKEO MARKETPLACE — LIVE DEMO 🚀      ║');
console.log('║   Decentralized RPC Data, Paid Per Query     ║');
console.log('╚══════════════════════════════════════════════╝');
console.log('');
console.log(`Contract: #${CONTRACT_ID}`);
console.log(`Provider: Red_5 (${SENTINEL})`);
console.log(`Signing Key: ${addr}`);
console.log('');

// Query 1: Network status
console.log('━━━ 🌐 QUERY 1: Network Status ━━━');
const status = await signedQuery('/status');
if (status.status === 200) {
  const r = status.data.result;
  console.log(`  Node: ${r.node_info.moniker}`);
  console.log(`  Network: ${r.node_info.network}`);
  console.log(`  Latest Block: ${r.sync_info.latest_block_height}`);
  console.log(`  Block Time: ${r.sync_info.latest_block_time}`);
  console.log(`  Catching Up: ${r.sync_info.catching_up}`);
}
console.log('');

// Query 2: Latest block details
console.log('━━━ 📦 QUERY 2: Latest Block ━━━');
const block = await signedQuery('/block');
if (block.status === 200) {
  const h = block.data.result.block.header;
  const txs = block.data.result.block.data.txs || [];
  console.log(`  Height: ${h.height}`);
  console.log(`  Time: ${h.time}`);
  console.log(`  Proposer: ${h.proposer_address.slice(0,16)}...`);
  console.log(`  Transactions: ${txs.length}`);
  console.log(`  Chain ID: ${h.chain_id}`);
}
console.log('');

// Query 3: Active validators
console.log('━━━ 🏛️ QUERY 3: Active Validators ━━━');
const vals = await signedQuery('/validators?per_page=100');
if (vals.status === 200) {
  const r = vals.data.result;
  const validators = r.validators || [];
  console.log(`  Total Active: ${r.total}`);
  console.log(`  Top 5 by Voting Power:`);
  const sorted = validators.sort((a, b) => parseInt(b.voting_power) - parseInt(a.voting_power));
  for (const v of sorted.slice(0, 5)) {
    console.log(`    → ${v.address.slice(0,12)}... | Power: ${parseInt(v.voting_power).toLocaleString()}`);
  }
}
console.log('');

// Query 4: Genesis info
console.log('━━━ ⚙️ QUERY 4: Chain Info ━━━');
const info = await signedQuery('/abci_info');
if (info.status === 200) {
  const r = info.data.result.response;
  console.log(`  App: ${r.data}`);
  console.log(`  Version: ${r.version}`);
  console.log(`  Last Block: ${r.last_block_height}`);
}
console.log('');

// Query 5: Specific block (genesis)
console.log('━━━ 🏁 QUERY 5: Block #1 (Genesis) ━━━');
const genesis = await signedQuery('/block?height=1');
if (genesis.status === 200) {
  const h = genesis.data.result.block.header;
  console.log(`  Genesis Time: ${h.time}`);
  console.log(`  Chain ID: ${h.chain_id}`);
  console.log(`  Validators Hash: ${h.validators_hash.slice(0,20)}...`);
}
console.log('');

// Query 6: Unconfirmed transactions (mempool)
console.log('━━━ 📬 QUERY 6: Mempool Status ━━━');
const mempool = await signedQuery('/num_unconfirmed_txs');
if (mempool.status === 200) {
  const r = mempool.data.result;
  console.log(`  Pending Txs: ${r.total}`);
  console.log(`  Total Bytes: ${r.total_bytes}`);
}
console.log('');

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log(`✅ ${nonce} paid queries — all auto-signed by SDK`);
console.log(`💸 Cost: ${nonce * 25000} uarkeo (${(nonce * 25000 / 1e8).toFixed(4)} ARKEO)`);
console.log(`⚡ No wallet popups, no manual signing`);
console.log(`🔑 One API key = unlimited programmatic access`);
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('');
