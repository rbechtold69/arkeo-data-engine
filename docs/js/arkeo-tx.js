// Arkeo Transaction Helper
// Uses protobuf.js for proper message encoding

const ARKEO_PROTO = `
syntax = "proto3";
package arkeo.arkeo;

message MsgBondProvider {
  string creator = 1;
  string provider = 2;
  string service = 3;
  string bond = 4;
}

message MsgModProvider {
  string creator = 1;
  string provider = 2;
  string service = 3;
  string metadata_uri = 4;
  uint64 metadata_nonce = 5;
  int32 status = 6;
  int64 min_contract_duration = 7;
  int64 max_contract_duration = 8;
  repeated Coin subscription_rate = 9;
  repeated Coin pay_as_you_go_rate = 10;
  int64 settlement_duration = 11;
}

message Coin {
  string denom = 1;
  string amount = 2;
}
`;

class ArkeoTxHelper {
  constructor() {
    this.root = null;
    this.initialized = false;
  }

  async init() {
    if (this.initialized) return;
    
    // Load protobuf.js from CDN
    if (!window.protobuf) {
      await this.loadScript('https://cdn.jsdelivr.net/npm/protobufjs@7.2.6/dist/protobuf.min.js');
    }
    
    // Parse the proto definition
    this.root = protobuf.parse(ARKEO_PROTO).root;
    this.MsgBondProvider = this.root.lookupType('arkeo.arkeo.MsgBondProvider');
    this.MsgModProvider = this.root.lookupType('arkeo.arkeo.MsgModProvider');
    this.Coin = this.root.lookupType('arkeo.arkeo.Coin');
    
    this.initialized = true;
    console.log('ArkeoTxHelper initialized');
  }

  loadScript(src) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = src;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  encodeBondProvider(creator, provider, service, bond) {
    const message = this.MsgBondProvider.create({
      creator: creator,
      provider: provider,
      service: service,
      bond: bond
    });
    return this.MsgBondProvider.encode(message).finish();
  }

  encodeModProvider(params) {
    const payAsYouGoRate = params.payAsYouGoRate.map(coin => 
      this.Coin.create({ denom: coin.denom, amount: coin.amount })
    );
    
    const message = this.MsgModProvider.create({
      creator: params.creator,
      provider: params.provider,
      service: params.service,
      metadataUri: params.metadataUri || '',
      metadataNonce: params.metadataNonce || 1,
      status: params.status || 1,
      minContractDuration: params.minContractDuration || 10,
      maxContractDuration: params.maxContractDuration || 1000000,
      subscriptionRate: [],
      payAsYouGoRate: payAsYouGoRate,
      settlementDuration: params.settlementDuration || 10
    });
    return this.MsgModProvider.encode(message).finish();
  }

  // Create a proper Any-wrapped message
  wrapAsAny(typeUrl, value) {
    // Manually create the Any message
    // Any = { type_url: string, value: bytes }
    const typeUrlBytes = new TextEncoder().encode(typeUrl);
    
    // Encode as protobuf:
    // field 1 (type_url): tag=10 (field 1, wire type 2), length, string
    // field 2 (value): tag=18 (field 2, wire type 2), length, bytes
    const result = [];
    
    // type_url field
    result.push(10); // tag
    this.writeVarint(result, typeUrlBytes.length);
    for (const b of typeUrlBytes) result.push(b);
    
    // value field  
    result.push(18); // tag
    this.writeVarint(result, value.length);
    for (const b of value) result.push(b);
    
    return new Uint8Array(result);
  }

  writeVarint(arr, value) {
    while (value > 127) {
      arr.push((value & 0x7f) | 0x80);
      value >>>= 7;
    }
    arr.push(value);
  }

  bytesToBase64(bytes) {
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }
}

// Global instance
window.arkeoTx = new ArkeoTxHelper();
