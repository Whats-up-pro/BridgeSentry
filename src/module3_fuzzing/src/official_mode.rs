//! Option-A official evaluation path (execution-only).
//!
//! Nothing in this module reads scenario text as an oracle fact. LLM scenarios
//! are used only as *seeds* (which contract/function to call and with which
//! argument values); every reported finding is derived from committed EVM
//! execution: ERC-20 `Transfer` logs, relay deliveries that were actually
//! executed on the destination EVM, and coverage observed by the inspector.
//!
//! A fixture opts in by providing `<benchmark>/official/spec.json`, which
//! declares how to deploy the vulnerable / patched / benign variants, the
//! pre-incident setup (admin calls, honest deposits), the faithful relay rules
//! (source event -> destination call executed by the relayer), paired assets,
//! and the protocol release entrypoints that define the target root-cause path.
//!
//! Oracle (execution-derived asset conservation): the attacker-controlled
//! address set must not end a trace with a net positive balance in any
//! (paired) asset. Attacker-controlled = every address that is not a deployed
//! contract, the deployer, the relayer, a declared victim, or the zero address.

use std::collections::{BTreeMap, HashMap, HashSet};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::str::FromStr;
use std::time::Instant;

use ethers_core::abi::{Abi, Function, ParamType, RawLog, StateMutability, Token};
use ethers_core::types::{H160, H256, U256 as EU256};
use eyre::{eyre, Result};
use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};
use revm::primitives::{keccak256, Address, U256};
use serde::Deserialize;
use serde_json::{json, Value};

use crate::config::RuntimeContext;
use crate::coverage_tracker::CoverageTracker;
use crate::dual_evm::{default_caller, DualEvm, DualEvmSnapshot, TxOutcome};
use crate::evidence::{ExploitEvidenceGates, ObservationStatus};
use crate::official_validator::{finalize_exploit_evidence, SupplementalExploitEvidence};

// ---------------------------------------------------------------------------
// Spec
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Deserialize)]
pub struct OfficialSpec {
    pub fixture_id: String,
    /// variant name -> contracts directory relative to the benchmark dir.
    pub variants: HashMap<String, String>,
    #[serde(default)]
    pub cross_chain: bool,
    pub deploy: Vec<DeployStep>,
    #[serde(default)]
    pub setup: Vec<CallStep>,
    #[serde(default)]
    pub relay: Vec<RelayRule>,
    #[serde(default)]
    pub victims: Vec<String>,
    /// Groups of `"Name"` token contracts that represent the same asset
    /// (e.g. canonical token on source + wrapped token on destination).
    #[serde(default)]
    pub asset_pairs: Vec<Vec<String>>,
    /// `"Contract.function"` entries that constitute the documented
    /// root-cause path (release/mint/unlock entrypoints).
    #[serde(default)]
    pub release_entrypoints: Vec<String>,
    /// Off-chain capability required by the incident (e.g. key compromise).
    /// Recorded for reporting; the official harness never grants it.
    #[serde(default)]
    pub required_offchain_capability: Option<String>,
    #[serde(default)]
    pub notes: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct DeployStep {
    pub name: String,
    pub contract: String,
    pub side: String,
    #[serde(default)]
    pub args: Vec<Value>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct CallStep {
    #[serde(default = "default_from")]
    pub from: String,
    pub to: String,
    #[serde(rename = "fn")]
    pub function: String,
    #[serde(default)]
    pub args: Vec<Value>,
}

fn default_from() -> String {
    "deployer".to_string()
}

#[derive(Debug, Clone, Deserialize)]
pub struct RelayRule {
    pub emitter: String,
    pub event: String,
    pub to: String,
    #[serde(rename = "fn")]
    pub function: String,
    /// Values: `"ev:<param name>"`, a `"$Name"` contract reference, a role
    /// (`"relayer"`, `"deployer"`) or a literal.
    pub args: Vec<Value>,
}

// ---------------------------------------------------------------------------
// World (one deployed variant on a fresh dual EVM)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Side {
    Source,
    Dest,
}

impl Side {
    fn parse(s: &str) -> Result<Self> {
        match s.to_ascii_lowercase().as_str() {
            "source" | "src" => Ok(Side::Source),
            "dest" | "destination" | "dst" => Ok(Side::Dest),
            other => Err(eyre!("unknown side `{other}`")),
        }
    }
    fn as_str(&self) -> &'static str {
        match self {
            Side::Source => "source",
            Side::Dest => "dest",
        }
    }
}

#[derive(Clone)]
struct Deployed {
    name: String,
    contract: String,
    side: Side,
    addr: Address,
    abi: Abi,
}

struct World {
    dual: DualEvm,
    contracts: Vec<Deployed>,
    base: Option<DualEvmSnapshot>,
    excluded: HashSet<Address>,
    asset_of: HashMap<(Side, Address), String>,
    deploy_log: Vec<String>,
}

fn addr_from_hex(s: &str) -> Option<Address> {
    Address::from_str(s.trim()).ok()
}

pub fn deployer() -> Address {
    addr_from_hex("0x000000000000000000000000000000000000dEaD").unwrap()
}
pub fn relayer() -> Address {
    addr_from_hex("0x00000000000000000000000000000000000Be1a7").unwrap()
}
pub fn attacker() -> Address {
    default_caller()
}

fn to_h160(a: Address) -> H160 {
    H160::from_slice(a.as_slice())
}
fn from_h160(a: H160) -> Address {
    Address::from_slice(a.as_bytes())
}

/// Compile every `.sol` under `dir` with the `solc` on PATH.
fn compile_dir(dir: &Path, extra_allow: &[PathBuf]) -> Result<HashMap<String, (Abi, Vec<u8>)>> {
    let mut files = Vec::new();
    let mut stack = vec![dir.to_path_buf()];
    while let Some(d) = stack.pop() {
        for e in std::fs::read_dir(&d)? {
            let p = e?.path();
            if p.is_dir() {
                stack.push(p);
            } else if p.extension().map(|x| x == "sol").unwrap_or(false) {
                files.push(p);
            }
        }
    }
    if files.is_empty() {
        return Err(eyre!("no .sol files under {}", dir.display()));
    }
    files.sort();
    let mut allow: Vec<String> = vec![dir.to_string_lossy().to_string()];
    allow.extend(extra_allow.iter().map(|p| p.to_string_lossy().to_string()));
    let out = Command::new("solc")
        .arg("--evm-version")
        .arg("london")
        .arg("--combined-json")
        .arg("abi,bin")
        .arg("--allow-paths")
        .arg(allow.join(","))
        .args(&files)
        .output()
        .map_err(|e| eyre!("failed to run solc: {e}"))?;
    if !out.status.success() {
        return Err(eyre!("solc failed: {}", String::from_utf8_lossy(&out.stderr)));
    }
    let v: Value = serde_json::from_slice(&out.stdout)?;
    let mut res = HashMap::new();
    for (k, blob) in v["contracts"].as_object().ok_or_else(|| eyre!("solc: no contracts"))? {
        let short = k.rsplit(':').next().unwrap_or(k).to_string();
        let bin = blob["bin"].as_str().unwrap_or("");
        if bin.is_empty() {
            continue;
        }
        let abi_val = match &blob["abi"] {
            Value::String(s) => serde_json::from_str::<Value>(s)?,
            other => other.clone(),
        };
        let abi: Abi = serde_json::from_value(abi_val)?;
        res.insert(short, (abi, hex::decode(bin)?));
    }
    Ok(res)
}

impl World {
    fn build(ctx: &RuntimeContext, spec: &OfficialSpec, bench_dir: &Path, variant: &str) -> Result<Self> {
        let rel = spec
            .variants
            .get(variant)
            .ok_or_else(|| eyre!("spec has no `{variant}` variant"))?;
        let dir = bench_dir.join(rel);
        let shared = bench_dir.join("..").join("_shared");
        let common = bench_dir.join("..").join("_official_common");
        let compiled = compile_dir(&dir, &[shared, common])?;

        let mut dual = crate::fuzz_loop::init_dual_evm(ctx)
            .ok_or_else(|| eyre!("official mode requires a dual-EVM (set --source-rpc/--dest-rpc/--*-block)"))?;
        dual.reset_benchmark_deployer();
        let big = U256::from(10u8).pow(U256::from(30u8));
        let mut funded = vec![attacker(), relayer(), deployer()];
        let victims: Vec<Address> = spec.victims.iter().filter_map(|s| addr_from_hex(s)).collect();
        funded.extend(victims.iter().copied());
        for a in &funded {
            dual.fund_source(*a, big);
            dual.fund_dest(*a, big);
        }

        let mut w = World {
            dual,
            contracts: Vec::new(),
            base: None,
            excluded: HashSet::new(),
            asset_of: HashMap::new(),
            deploy_log: Vec::new(),
        };

        for step in &spec.deploy {
            let side = Side::parse(&step.side)?;
            let (abi, bin) = compiled
                .get(&step.contract)
                .ok_or_else(|| eyre!("contract `{}` not compiled from {}", step.contract, dir.display()))?
                .clone();
            let mut init = bin.clone();
            if let Some(ctor) = abi.constructor() {
                let kinds: Vec<ParamType> = ctor.inputs.iter().map(|p| p.kind.clone()).collect();
                let toks = w.resolve_args(&kinds, &step.args, None)?;
                init = ctor
                    .encode_input(bin, &toks)
                    .map_err(|e| eyre!("ctor encode {}: {e}", step.name))?;
            }
            let addr = match side {
                Side::Source => w.dual.deploy_mock_on_source(&init),
                Side::Dest => w.dual.deploy_mock_on_dest(&init),
            }
            .map_err(|e| eyre!("deploy {}: {e}", step.name))?;
            w.deploy_log.push(format!("{}={}@{} ({})", step.name, addr, side.as_str(), step.contract));
            w.contracts.push(Deployed {
                name: step.name.clone(),
                contract: step.contract.clone(),
                side,
                addr,
                abi,
            });
        }

        for c in &w.contracts {
            w.excluded.insert(c.addr);
        }
        w.excluded.insert(deployer());
        w.excluded.insert(relayer());
        w.excluded.insert(Address::ZERO);
        for v in &victims {
            w.excluded.insert(*v);
        }
        for (gi, group) in spec.asset_pairs.iter().enumerate() {
            let label = format!("asset{gi}:{}", group.join("+"));
            for name in group {
                if let Some(c) = w.contract(name) {
                    w.asset_of.insert((c.side, c.addr), label.clone());
                }
            }
        }

        // Pre-incident setup is executed by the declared actor and relayed
        // faithfully, exactly like attack traffic.
        let mut cov = CoverageTracker::default();
        for st in &spec.setup {
            let from = w.role_address(&st.from)?;
            let idx = w
                .contract_index(&st.to)
                .ok_or_else(|| eyre!("setup: unknown contract `{}`", st.to))?;
            let (func, toks) = w.function_call(idx, &st.function, &st.args, None)?;
            let rec = w.execute_call(spec, idx, &func, &toks, from, &mut cov, Kind::Setup)?;
            if rec.iter().any(|r| !r.success) {
                return Err(eyre!(
                    "setup call {}.{} reverted: {}",
                    st.to,
                    st.function,
                    rec.iter().map(|r| r.status.clone()).collect::<Vec<_>>().join(" | ")
                ));
            }
        }
        w.base = Some(w.dual.capture_snapshot());
        Ok(w)
    }

    fn contract(&self, name: &str) -> Option<&Deployed> {
        let n = name.trim_start_matches('$');
        self.contracts.iter().find(|c| c.name == n)
    }
    fn contract_index(&self, name: &str) -> Option<usize> {
        let n = name.trim_start_matches('$');
        self.contracts.iter().position(|c| c.name == n)
    }

    fn role_address(&self, role: &str) -> Result<Address> {
        match role {
            "deployer" => Ok(deployer()),
            "relayer" => Ok(relayer()),
            "attacker" => Ok(attacker()),
            s if s.starts_with('$') => self
                .contract(s)
                .map(|c| c.addr)
                .ok_or_else(|| eyre!("unknown contract ref {s}")),
            s => addr_from_hex(s).ok_or_else(|| eyre!("bad actor `{s}`")),
        }
    }

    fn is_attacker(&self, a: Address) -> bool {
        !self.excluded.contains(&a)
    }

    fn function_call(
        &self,
        idx: usize,
        name: &str,
        args: &[Value],
        ev: Option<&HashMap<String, Token>>,
    ) -> Result<(Function, Vec<Token>)> {
        let c = &self.contracts[idx];
        let funcs = c
            .abi
            .functions_by_name(name)
            .map_err(|_| eyre!("{} has no function {name}", c.name))?;
        let f = funcs
            .iter()
            .find(|f| f.inputs.len() == args.len())
            .or_else(|| funcs.first())
            .ok_or_else(|| eyre!("{} has no function {name}", c.name))?
            .clone();
        let kinds: Vec<ParamType> = f.inputs.iter().map(|p| p.kind.clone()).collect();
        let toks = self.resolve_args(&kinds, args, ev)?;
        Ok((f, toks))
    }

    fn resolve_args(&self, kinds: &[ParamType], args: &[Value], ev: Option<&HashMap<String, Token>>) -> Result<Vec<Token>> {
        if kinds.len() != args.len() {
            return Err(eyre!("arity mismatch: expected {}, got {}", kinds.len(), args.len()));
        }
        kinds
            .iter()
            .zip(args)
            .map(|(k, v)| self.resolve_value(k, v, ev))
            .collect()
    }

    fn resolve_value(&self, kind: &ParamType, v: &Value, ev: Option<&HashMap<String, Token>>) -> Result<Token> {
        if let Value::String(s) = v {
            if let Some(name) = s.strip_prefix("ev:") {
                return ev
                    .and_then(|m| m.get(name).cloned())
                    .ok_or_else(|| eyre!("relay: event has no field `{name}`"));
            }
            if s.starts_with('$') || matches!(s.as_str(), "deployer" | "relayer" | "attacker") {
                if matches!(kind, ParamType::Address) {
                    return Ok(Token::Address(to_h160(self.role_address(s)?)));
                }
            }
        }
        if let (ParamType::Tuple(parts), Value::Array(items)) = (kind, v) {
            let toks = parts
                .iter()
                .zip(items)
                .map(|(k, x)| self.resolve_value(k, x, ev))
                .collect::<Result<Vec<_>>>()?;
            return Ok(Token::Tuple(toks));
        }
        literal_token(kind, v).ok_or_else(|| eyre!("cannot encode {v} as {kind:?}"))
    }

    /// Execute one top-level call plus any faithful relay deliveries it
    /// triggers. Returns one record per executed transaction.
    fn execute_call(
        &mut self,
        spec: &OfficialSpec,
        idx: usize,
        func: &Function,
        toks: &[Token],
        from: Address,
        cov: &mut CoverageTracker,
        kind: Kind,
    ) -> Result<Vec<TxRecord>> {
        let data = func.encode_input(toks).map_err(|e| eyre!("encode {}: {e}", func.name))?;
        let c = self.contracts[idx].clone();
        let mut out = vec![self.raw_exec(c.side, from, c.addr, &data, cov, kind, &c.name, &func.name)];
        if c.side == Side::Source && out[0].success {
            let logs = out[0].logs.clone();
            for log in logs {
                for rule in &spec.relay {
                    let Some(em) = self.contract(&rule.emitter) else { continue };
                    if em.addr != log.address || em.side != Side::Source {
                        continue;
                    }
                    let Ok(event) = em.abi.event(&rule.event) else { continue };
                    if log.topics().first().map(|t| t.0) != Some(event.signature().0) {
                        continue;
                    }
                    let raw = RawLog {
                        topics: log.topics().iter().map(|t| H256::from_slice(t.as_slice())).collect(),
                        data: log.data.data.to_vec(),
                    };
                    let Ok(parsed) = event.parse_log(raw) else { continue };
                    let fields: HashMap<String, Token> =
                        parsed.params.into_iter().map(|p| (p.name, p.value)).collect();
                    let Some(didx) = self.contract_index(&rule.to) else { continue };
                    let Ok((dfunc, dtoks)) = self.function_call(didx, &rule.function, &rule.args, Some(&fields)) else {
                        continue;
                    };
                    let Ok(ddata) = dfunc.encode_input(&dtoks) else { continue };
                    let d = self.contracts[didx].clone();
                    let rk = if kind == Kind::Setup { Kind::Setup } else { Kind::Relay };
                    out.push(self.raw_exec(d.side, relayer(), d.addr, &ddata, cov, rk, &d.name, &dfunc.name));
                }
            }
        }
        Ok(out)
    }

    #[allow(clippy::too_many_arguments)]
    fn raw_exec(
        &mut self,
        side: Side,
        from: Address,
        to: Address,
        data: &[u8],
        cov: &mut CoverageTracker,
        kind: Kind,
        cname: &str,
        fname: &str,
    ) -> TxRecord {
        let payload = crate::fuzz_loop::build_payload(from, to, data);
        let mut iter_cov = CoverageTracker::default();
        let res: Result<TxOutcome, String> = match side {
            Side::Source => self.dual.execute_on_source_with_inspector_full(&payload, &mut iter_cov),
            Side::Dest => self.dual.execute_on_dest_with_inspector_full(&payload, &mut iter_cov),
        };
        let fixture_pcs = iter_cov
            .touched
            .iter()
            .filter(|(a, _)| self.excluded.contains(a) && *a != Address::ZERO)
            .count();
        cov.merge(&iter_cov);
        match res {
            Ok(o) => TxRecord {
                side,
                kind,
                entry: format!("{cname}.{fname}"),
                success: o.success,
                status: o.status.clone(),
                logs: if o.success { o.logs } else { vec![] },
                fixture_pcs,
            },
            Err(e) => TxRecord {
                side,
                kind,
                entry: format!("{cname}.{fname}"),
                success: false,
                status: e,
                logs: vec![],
                fixture_pcs,
            },
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Kind {
    Setup,
    Attack,
    Relay,
}

#[derive(Clone)]
struct TxRecord {
    side: Side,
    kind: Kind,
    entry: String,
    success: bool,
    status: String,
    logs: Vec<revm::primitives::Log>,
    fixture_pcs: usize,
}

// ---------------------------------------------------------------------------
// Literal encoding (spec values and LLM scenario parameters)
// ---------------------------------------------------------------------------

fn parse_uint(s: &str) -> Option<EU256> {
    let t = s.trim().replace('_', "").replace(',', "");
    if let Some(h) = t.strip_prefix("0x") {
        return EU256::from_str_radix(h, 16).ok();
    }
    if let Some((m, e)) = t.split_once(['e', 'E']) {
        let exp: u32 = e.parse().ok()?;
        let (int, frac) = m.split_once('.').unwrap_or((m, ""));
        if frac.len() as u32 > exp {
            return None;
        }
        let digits = format!("{int}{frac}");
        let base = EU256::from_dec_str(&digits).ok()?;
        return base.checked_mul(EU256::from(10u8).pow(EU256::from(exp - frac.len() as u32)));
    }
    EU256::from_dec_str(&t).ok()
}

fn literal_token(kind: &ParamType, v: &Value) -> Option<Token> {
    match kind {
        ParamType::Address => match v {
            Value::String(s) => H160::from_str(s.trim()).ok().map(Token::Address),
            _ => None,
        },
        ParamType::Uint(_) => match v {
            Value::Number(n) => n.as_u64().map(|x| Token::Uint(EU256::from(x))),
            Value::String(s) => parse_uint(s).map(Token::Uint),
            Value::Bool(b) => Some(Token::Uint(EU256::from(*b as u8))),
            _ => None,
        },
        ParamType::Int(_) => match v {
            Value::Number(n) => n.as_u64().map(|x| Token::Int(EU256::from(x))),
            Value::String(s) => parse_uint(s).map(Token::Int),
            _ => None,
        },
        ParamType::Bool => match v {
            Value::Bool(b) => Some(Token::Bool(*b)),
            Value::String(s) => match s.to_ascii_lowercase().as_str() {
                "true" => Some(Token::Bool(true)),
                "false" => Some(Token::Bool(false)),
                _ => None,
            },
            _ => None,
        },
        ParamType::FixedBytes(n) => match v {
            Value::String(s) if s.starts_with("0x") => {
                let mut b = hex::decode(&s[2..]).ok()?;
                if b.len() > *n {
                    return None;
                }
                // left-pad numbers like 0x00 / 0x01 to bytes32 semantics
                let mut out = vec![0u8; *n - b.len()];
                out.append(&mut b);
                Some(Token::FixedBytes(out))
            }
            _ => None,
        },
        ParamType::Bytes => match v {
            Value::String(s) if s.starts_with("0x") => hex::decode(&s[2..]).ok().map(Token::Bytes),
            _ => None,
        },
        ParamType::String => match v {
            Value::String(s) => Some(Token::String(s.clone())),
            _ => None,
        },
        ParamType::Array(inner) => match v {
            Value::Array(xs) => xs.iter().map(|x| literal_token(inner, x)).collect::<Option<Vec<_>>>().map(Token::Array),
            _ => None,
        },
        ParamType::FixedArray(inner, n) => match v {
            Value::Array(xs) if xs.len() == *n => {
                xs.iter().map(|x| literal_token(inner, x)).collect::<Option<Vec<_>>>().map(Token::FixedArray)
            }
            _ => None,
        },
        ParamType::Tuple(parts) => match v {
            Value::Array(xs) if xs.len() == parts.len() => parts
                .iter()
                .zip(xs)
                .map(|(k, x)| literal_token(k, x))
                .collect::<Option<Vec<_>>>()
                .map(Token::Tuple),
            _ => None,
        },
    }
}

fn default_token(kind: &ParamType) -> Token {
    match kind {
        ParamType::Address => Token::Address(to_h160(attacker())),
        ParamType::Uint(n) if *n < 128 => Token::Uint(EU256::one()),
        ParamType::Uint(_) => Token::Uint(EU256::exp10(21)),
        ParamType::Int(_) => Token::Int(EU256::one()),
        ParamType::Bool => Token::Bool(true),
        ParamType::FixedBytes(n) => Token::FixedBytes(vec![0u8; *n]),
        ParamType::Bytes => Token::Bytes(vec![]),
        ParamType::String => Token::String(String::new()),
        ParamType::Array(_) => Token::Array(vec![]),
        ParamType::FixedArray(inner, n) => Token::FixedArray((0..*n).map(|_| default_token(inner)).collect()),
        ParamType::Tuple(parts) => Token::Tuple(parts.iter().map(default_token).collect()),
    }
}

fn norm(s: &str) -> String {
    s.chars().filter(|c| c.is_ascii_alphanumeric()).collect::<String>().to_ascii_lowercase()
}

// ---------------------------------------------------------------------------
// Attack sequences, seeds and mutation
// ---------------------------------------------------------------------------

#[derive(Clone)]
struct AttackCall {
    idx: usize,
    func: Function,
    args: Vec<Token>,
}

type Seq = Vec<AttackCall>;

fn callable(f: &Function) -> bool {
    !matches!(f.state_mutability, StateMutability::View | StateMutability::Pure)
}

struct SeedStats {
    scenarios_total: usize,
    scenarios_with_calls: usize,
    actions_total: usize,
    actions_resolved: usize,
}

fn llm_seeds(world: &World, ctx: &RuntimeContext) -> (Vec<Seq>, SeedStats) {
    let mut seeds = Vec::new();
    let mut st = SeedStats { scenarios_total: 0, scenarios_with_calls: 0, actions_total: 0, actions_resolved: 0 };
    for sc in &ctx.hypotheses.scenarios {
        st.scenarios_total += 1;
        let mut seq = Vec::new();
        for a in &sc.actions {
            if a.chain.eq_ignore_ascii_case("relay") {
                continue; // relay is never attacker-controlled in the official harness
            }
            st.actions_total += 1;
            let Some(cname) = a.contract.as_deref() else { continue };
            let Some(fname_raw) = a.function.as_deref() else { continue };
            let cn = norm(cname);
            let idx = world
                .contracts
                .iter()
                .position(|c| norm(&c.name) == cn || norm(&c.contract) == cn)
                .or_else(|| {
                    world.contracts.iter().position(|c| {
                        let a = norm(&c.contract);
                        !a.is_empty() && (cn.contains(&a) || a.contains(&cn))
                    })
                });
            let Some(idx) = idx else { continue };
            let fname = fname_raw.split('(').next().unwrap_or("").rsplit('.').next().unwrap_or("");
            let fnorm = norm(fname);
            let Some(func) = world.contracts[idx]
                .abi
                .functions()
                .find(|f| callable(f) && norm(&f.name) == fnorm)
                .cloned()
            else {
                continue;
            };
            let args = func
                .inputs
                .iter()
                .map(|p| {
                    let pn = norm(&p.name);
                    let val = a.params.iter().find(|(k, _)| norm(k) == pn).map(|(_, v)| v);
                    val.and_then(|v| llm_value_token(world, &p.kind, v))
                        .unwrap_or_else(|| default_token(&p.kind))
                })
                .collect();
            st.actions_resolved += 1;
            seq.push(AttackCall { idx, func, args });
        }
        if !seq.is_empty() {
            st.scenarios_with_calls += 1;
            seeds.push(seq);
        }
    }
    (seeds, st)
}

fn llm_value_token(world: &World, kind: &ParamType, v: &Value) -> Option<Token> {
    if let (ParamType::Address, Value::String(s)) = (kind, v) {
        let l = s.to_ascii_lowercase();
        if l.contains("attacker") || l.contains("exploiter") || l.contains("recipient") {
            return Some(Token::Address(to_h160(attacker())));
        }
        let n = norm(s);
        if let Some(c) = world.contracts.iter().find(|c| !n.is_empty() && (norm(&c.name) == n || norm(&c.contract) == n)) {
            return Some(Token::Address(to_h160(c.addr)));
        }
    }
    literal_token(kind, v)
}

fn random_call(world: &World, rng: &mut StdRng) -> Option<AttackCall> {
    let all: Vec<(usize, Function)> = world
        .contracts
        .iter()
        .enumerate()
        .flat_map(|(i, c)| c.abi.functions().filter(|f| callable(f)).map(move |f| (i, f.clone())))
        .collect();
    if all.is_empty() {
        return None;
    }
    let (idx, func) = all[rng.gen_range(0..all.len())].clone();
    let args = func.inputs.iter().map(|p| default_token(&p.kind)).collect();
    Some(AttackCall { idx, func, args })
}

fn random_seeds(world: &World, rng: &mut StdRng, n: usize) -> Vec<Seq> {
    (0..n)
        .filter_map(|_| {
            let len = rng.gen_range(1..=4);
            let s: Seq = (0..len).filter_map(|_| random_call(world, rng)).collect();
            if s.is_empty() { None } else { Some(s) }
        })
        .collect()
}

struct Dict {
    words: Vec<[u8; 32]>,
    encodings: Vec<Vec<u8>>,
}

fn mask_width(v: EU256, kind: &ParamType) -> EU256 {
    match kind {
        ParamType::Uint(n) | ParamType::Int(n) if *n < 256 => v & ((EU256::one() << *n) - 1),
        _ => v,
    }
}

fn mutate_token(t: &Token, kind: &ParamType, world: &World, dict: &Dict, rng: &mut StdRng) -> Token {
    match mutate_token_raw(t, kind, world, dict, rng) {
        Token::Uint(v) => Token::Uint(mask_width(v, kind)),
        Token::Int(v) => Token::Int(mask_width(v, kind)),
        other => other,
    }
}

fn mutate_token_raw(t: &Token, kind: &ParamType, world: &World, dict: &Dict, rng: &mut StdRng) -> Token {
    match t {
        Token::Uint(x) => {
            let choices = [
                EU256::zero(),
                EU256::one(),
                EU256::exp10(18),
                EU256::exp10(21),
                EU256::exp10(24),
                EU256::from(u128::MAX),
                x.saturating_mul(EU256::from(2u8)),
                *x / 2,
                EU256::from(rng.gen::<u64>()),
            ];
            if !dict.words.is_empty() && rng.gen_bool(0.2) {
                return Token::Uint(EU256::from_big_endian(&dict.words[rng.gen_range(0..dict.words.len())]));
            }
            Token::Uint(choices[rng.gen_range(0..choices.len())])
        }
        Token::Int(_) => Token::Int(EU256::from(rng.gen::<u32>())),
        Token::Address(_) => {
            let mut opts = vec![to_h160(attacker()), H160::zero()];
            opts.extend(world.contracts.iter().map(|c| to_h160(c.addr)));
            Token::Address(opts[rng.gen_range(0..opts.len())])
        }
        Token::Bool(b) => Token::Bool(!b),
        Token::FixedBytes(b) => {
            let n = b.len();
            let pick = rng.gen_range(0..4);
            let mut out = vec![0u8; n];
            match pick {
                0 => {}
                1 => out[n - 1] = 1,
                2 if !dict.words.is_empty() => {
                    let w = dict.words[rng.gen_range(0..dict.words.len())];
                    out.copy_from_slice(&w[32 - n..]);
                }
                _ => rng.fill(&mut out[..]),
            }
            Token::FixedBytes(out)
        }
        Token::Bytes(_) => {
            if !dict.encodings.is_empty() && rng.gen_bool(0.6) {
                Token::Bytes(dict.encodings[rng.gen_range(0..dict.encodings.len())].clone())
            } else {
                let mut out = vec![0u8; 32 * rng.gen_range(0..4)];
                rng.fill(&mut out[..]);
                Token::Bytes(out)
            }
        }
        Token::Tuple(parts) if !parts.is_empty() => {
            let mut p = parts.clone();
            let i = rng.gen_range(0..p.len());
            let k = match kind {
                ParamType::Tuple(ks) if i < ks.len() => ks[i].clone(),
                _ => ParamType::Uint(256),
            };
            p[i] = mutate_token(&p[i], &k, world, dict, rng);
            Token::Tuple(p)
        }
        Token::Array(xs) => {
            let mut xs = xs.clone();
            if xs.is_empty() || rng.gen_bool(0.3) {
                xs.push(Token::Uint(EU256::one()));
            }
            Token::Array(xs)
        }
        other => other.clone(),
    }
}

fn mutate_seq(seq: &Seq, world: &World, dict: &Dict, rng: &mut StdRng) -> Seq {
    let mut s = seq.clone();
    for _ in 0..rng.gen_range(1..=3) {
        match rng.gen_range(0..10) {
            0 | 1 if s.len() < 8 => {
                if let Some(c) = random_call(world, rng) {
                    let pos = rng.gen_range(0..=s.len());
                    s.insert(pos, c);
                }
            }
            2 if s.len() > 1 => {
                let i = rng.gen_range(0..s.len());
                s.remove(i);
            }
            3 if !s.is_empty() && s.len() < 8 => {
                let i = rng.gen_range(0..s.len());
                let c = s[i].clone();
                s.insert(i, c);
            }
            _ if !s.is_empty() => {
                let i = rng.gen_range(0..s.len());
                if !s[i].args.is_empty() {
                    let j = rng.gen_range(0..s[i].args.len());
                    let k = s[i].func.inputs[j].kind.clone();
                    s[i].args[j] = mutate_token(&s[i].args[j], &k, world, dict, rng);
                }
            }
            _ => {}
        }
    }
    s
}

// ---------------------------------------------------------------------------
// Execution-derived oracle
// ---------------------------------------------------------------------------

struct TraceResult {
    records: Vec<TxRecord>,
    gains: BTreeMap<String, EU256>,
    gain_entries: Vec<(String, Side, Kind)>,
    fixture_pcs: usize,
}

fn transfer_topic() -> [u8; 32] {
    keccak256(b"Transfer(address,address,uint256)").0
}

fn run_trace(world: &mut World, spec: &OfficialSpec, seq: &Seq, cov: &mut CoverageTracker) -> TraceResult {
    world.dual.restore_snapshot(world.base.clone().expect("base snapshot"));
    let mut records = Vec::new();
    for call in seq {
        match world.execute_call(spec, call.idx, &call.func, &call.args, attacker(), cov, Kind::Attack) {
            Ok(r) => records.extend(r),
            Err(_) => continue,
        }
    }
    let topic = transfer_topic();
    let mut inflow: BTreeMap<String, EU256> = BTreeMap::new();
    let mut outflow: BTreeMap<String, EU256> = BTreeMap::new();
    let mut gain_entries = Vec::new();
    for r in &records {
        for log in &r.logs {
            let t = log.topics();
            if t.len() != 3 || t[0].0 != topic || log.data.data.len() < 32 {
                continue;
            }
            let from = Address::from_slice(&t[1].0[12..]);
            let to = Address::from_slice(&t[2].0[12..]);
            let val = EU256::from_big_endian(&log.data.data[..32]);
            let asset = world
                .asset_of
                .get(&(r.side, log.address))
                .cloned()
                .unwrap_or_else(|| format!("{}:{:#x}", r.side.as_str(), log.address));
            let fa = world.is_attacker(from);
            let ta = world.is_attacker(to);
            if ta && !fa {
                let e = inflow.entry(asset.clone()).or_default();
                *e = e.saturating_add(val);
                gain_entries.push((r.entry.clone(), r.side, r.kind));
            } else if fa && !ta {
                let e = outflow.entry(asset).or_default();
                *e = e.saturating_add(val);
            }
        }
    }
    let mut gains = BTreeMap::new();
    for (asset, inn) in &inflow {
        let out = outflow.get(asset).copied().unwrap_or_default();
        if *inn > out {
            gains.insert(asset.clone(), *inn - out);
        }
    }
    let fixture_pcs = records.iter().map(|r| r.fixture_pcs).sum();
    TraceResult { records, gains, gain_entries, fixture_pcs }
}

fn status(b: bool) -> ObservationStatus {
    if b { ObservationStatus::Pass } else { ObservationStatus::Fail }
}

fn seq_json(world: &World, seq: &Seq) -> Value {
    Value::Array(
        seq.iter()
            .map(|c| {
                let d = &world.contracts[c.idx];
                json!({
                    "side": d.side.as_str(),
                    "contract": d.name,
                    "function": c.func.signature(),
                    "calldata": format!("0x{}", hex::encode(c.func.encode_input(&c.args).unwrap_or_default())),
                })
            })
            .collect(),
    )
}

fn gains_json(g: &BTreeMap<String, EU256>) -> Value {
    Value::Object(g.iter().map(|(k, v)| (k.clone(), Value::String(v.to_string()))).collect())
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

pub fn run_official(ctx: &RuntimeContext) -> Result<Value> {
    let bench_dir = ctx
        .contract_plan
        .benchmark_dir
        .clone()
        .ok_or_else(|| eyre!("official mode: cannot locate benchmark directory from --atg path"))?;
    let spec_path = bench_dir.join("official").join("spec.json");
    let spec: OfficialSpec = serde_json::from_str(
        &std::fs::read_to_string(&spec_path).map_err(|e| eyre!("official mode needs {}: {e}", spec_path.display()))?,
    )?;
    let variant = std::env::var("BRIDGESENTRY_OFFICIAL_VARIANT").unwrap_or_else(|_| "vulnerable".into());
    let seed_mode = std::env::var("BRIDGESENTRY_OFFICIAL_SEEDS").unwrap_or_else(|_| "llm".into());
    let max_validate: usize = std::env::var("BRIDGESENTRY_OFFICIAL_MAX_VALIDATE")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(5);
    let seed = ctx.config.random_seed.unwrap_or(42);
    let mut rng = StdRng::seed_from_u64(seed);
    let budget = ctx.config.time_budget_s as f64;

    let t_setup = Instant::now();
    let mut world = World::build(ctx, &spec, &bench_dir, &variant)?;
    let setup_s = t_setup.elapsed().as_secs_f64();

    let (mut corpus, seed_stats) = match seed_mode.as_str() {
        "random" => {
            let s = random_seeds(&world, &mut rng, 20);
            let n = s.len();
            (s, SeedStats { scenarios_total: 0, scenarios_with_calls: n, actions_total: 0, actions_resolved: 0 })
        }
        _ => llm_seeds(&world, ctx),
    };
    if corpus.is_empty() {
        corpus = random_seeds(&world, &mut rng, 20);
    }
    let initial_corpus = corpus.len();

    let mut dict = Dict { words: Vec::new(), encodings: Vec::new() };
    for seq in &corpus {
        for c in seq {
            for a in &c.args {
                if let Token::Tuple(_) = a {
                    dict.encodings.push(ethers_core::abi::encode(&[a.clone()]));
                }
            }
        }
    }

    let mut cov = CoverageTracker::default();
    let mut candidates: Vec<(String, f64, Seq, TraceResult)> = Vec::new();
    let mut seen_keys = HashSet::new();
    let start = Instant::now();
    let mut iterations = 0u64;
    let mut seed_queue: Vec<Seq> = corpus.clone();

    while start.elapsed().as_secs_f64() < budget {
        let seq = if let Some(s) = seed_queue.pop() {
            s // execute every seed unmodified first
        } else {
            let base = if rng.gen_bool(0.5) && corpus.len() > initial_corpus {
                &corpus[rng.gen_range(initial_corpus..corpus.len())]
            } else {
                &corpus[rng.gen_range(0..corpus.len())]
            };
            mutate_seq(base, &world, &dict, &mut rng)
        };
        let before = cov.unique_pc_count();
        let res = run_trace(&mut world, &spec, &seq, &mut cov);
        iterations += 1;
        for r in &res.records {
            for log in &r.logs {
                for t in log.topics().iter().skip(1) {
                    if dict.words.len() < 4096 {
                        dict.words.push(t.0);
                    }
                }
            }
        }
        for c in &seq {
            for a in &c.args {
                if matches!(a, Token::Tuple(_)) && dict.encodings.len() < 1024 {
                    dict.encodings.push(ethers_core::abi::encode(&[a.clone()]));
                }
            }
        }
        if cov.unique_pc_count() > before && corpus.len() < 1024 {
            corpus.push(seq.clone());
        }
        if !res.gains.is_empty() {
            // One candidate per (assets gained, protocol entrypoints that paid out):
            // i.e. per distinct root-cause path, not per call sequence.
            let mut entries: Vec<String> = res.gain_entries.iter().map(|(e, sd, k)| format!("{e}@{}:{k:?}", sd.as_str())).collect();
            entries.sort();
            entries.dedup();
            let key = format!("{}|{}", res.gains.keys().cloned().collect::<Vec<_>>().join(","), entries.join("+"));
            if seen_keys.insert(key.clone()) {
                candidates.push((key, start.elapsed().as_secs_f64(), seq.clone(), res));
            }
        }
    }
    let fuzz_s = start.elapsed().as_secs_f64();

    // ---- validation ------------------------------------------------------
    let mut patched_world = if variant == "vulnerable" && spec.variants.contains_key("patched") {
        match World::build(ctx, &spec, &bench_dir, "patched") {
            Ok(w) => Some(w),
            Err(e) => {
                eprintln!("WARNING: patched variant could not be built: {e}");
                None
            }
        }
    } else {
        None
    };
    let addresses_match = patched_world.as_ref().map(|pw| {
        pw.contracts.len() == world.contracts.len()
            && pw.contracts.iter().zip(&world.contracts).all(|(a, b)| a.addr == b.addr && a.name == b.name)
    });

    let release: HashSet<&str> = spec.release_entrypoints.iter().map(|s| s.as_str()).collect();
    let mut cand_json = Vec::new();
    let mut first_valid: Option<f64> = None;
    let mut n_valid = 0usize;
    for (i, (key, t, seq, res)) in candidates.iter().enumerate() {
        let mut gates = ExploitEvidenceGates {
            target_bytecode_executed: status(res.fixture_pcs > 0),
            material_state_change: status(!res.gains.is_empty()),
            ..ExploitEvidenceGates::default()
        };
        let mut sup = SupplementalExploitEvidence::default();
        let via_protocol = res
            .gain_entries
            .iter()
            .any(|(entry, side, kind)| *kind == Kind::Relay || (release.contains(entry.as_str()) && (!spec.cross_chain || *side == Side::Dest)));
        sup.causal_path_valid = status(via_protocol);
        sup.capability_compliant = ObservationStatus::Pass; // faithful relay only, attacker never impersonates roles
        sup.impact_demonstrated = status(!res.gains.is_empty());
        let mut patched_note = Value::Null;
        if i < max_validate {
            let mut scratch = CoverageTracker::default();
            let replay = run_trace(&mut world, &spec, seq, &mut scratch);
            sup.replayable = status(replay.gains == res.gains);
            if let (Some(pw), Some(true)) = (patched_world.as_mut(), addresses_match) {
                let pr = run_trace(pw, &spec, seq, &mut scratch);
                sup.patched_rejected = status(pr.gains.is_empty());
                patched_note = json!({"patched_gain": gains_json(&pr.gains)});
            } else if patched_world.is_some() {
                patched_note = json!({"error": "patched deployment addresses differ from vulnerable deployment"});
            }
        }
        gates = finalize_exploit_evidence(gates, sup);
        let valid = gates.is_valid_exploit();
        if valid {
            n_valid += 1;
            first_valid = Some(first_valid.map_or(*t, |f: f64| f.min(*t)));
        }
        cand_json.push(json!({
            "key": key,
            "detected_at_s": t,
            "gain": gains_json(&res.gains),
            "gain_entrypoints": res.gain_entries.iter().map(|(e, s, k)| format!("{e}@{}:{k:?}", s.as_str())).collect::<Vec<_>>(),
            "trace": seq_json(&world, seq),
            "gates": serde_json::to_value(&gates)?,
            "valid_exploit": valid,
            "validated": i < max_validate,
            "patched_control": patched_note,
        }));
    }

    // CoverageTracker keys are (address, pc) without a chain id, and both
    // chains share the deployer nonce sequence, so report the combined count.
    let fixture_pcs = cov.touched.iter().filter(|(a, _)| world.contracts.iter().any(|c| c.addr == *a)).count();

    Ok(json!({
        "evaluation_mode": "official",
        "oracle": "execution_only_asset_conservation",
        "fixture_id": spec.fixture_id,
        "variant": variant,
        "seed_source": seed_mode,
        "seed": seed,
        "time_budget_s": budget,
        "setup_s": setup_s,
        "fuzz_s": fuzz_s,
        "iterations": iterations,
        "corpus_initial": initial_corpus,
        "corpus_final": corpus.len(),
        "coverage": {"fixture_unique_pcs": fixture_pcs},
        "semantic_resolution": {
            "scenarios_total": seed_stats.scenarios_total,
            "scenarios_with_calls": seed_stats.scenarios_with_calls,
            "actions_total": seed_stats.actions_total,
            "actions_resolved": seed_stats.actions_resolved,
        },
        "required_offchain_capability": spec.required_offchain_capability,
        "candidates_total": candidates.len(),
        "first_candidate_s": candidates.iter().map(|c| c.1).fold(None, |a: Option<f64>, x| Some(a.map_or(x, |y| y.min(x)))),
        "valid_exploits": n_valid,
        "first_valid_exploit_s": first_valid,
        "patched_addresses_match": addresses_match,
        "deploy_log": world.deploy_log,
        "candidates": cand_json,
    }))
}

// ---------------------------------------------------------------------------
// Deterministic fixture tests
//
// These tests prove each Option-A official fixture reproduces the documented
// root cause, independently of whether the fuzzer's random/LLM search happens
// to find it. For every fixture we build the `vulnerable` and `patched`
// worlds with the real `World::build`, replay the recorded attack sequence
// with the real `run_trace`, and assert:
//   * vulnerable -> the attacker-controlled set ends with a positive net
//     balance in a paired asset (execution-derived gain > 0);
//   * patched    -> no gain.
//
// The dual-EVM is backed by an in-process JSON-RPC stub that mirrors
// `scripts/official/empty_rpc.py` (empty chain state at any block), so the
// tests are hermetic: no network, no external process, no mainnet fork. They
// require `solc` on PATH (same tool the official runner needs); when solc is
// absent the test logs SKIP and returns so `cargo test` still passes in
// environments without the compiler.
// ---------------------------------------------------------------------------
#[cfg(test)]
mod fixture_tests {
    use super::*;
    use crate::config::{BaselineMode, RuntimeContext};
    use crate::contract_loader::ContractPlan;
    use serde_json::json;
    use std::io::{Read, Write};
    use std::net::{TcpListener, TcpStream};
    use std::sync::OnceLock;

    // ---- in-process empty JSON-RPC (mirror of empty_rpc.py) ---------------
    fn zero32() -> String {
        format!("0x{}", "00".repeat(32))
    }

    fn block_json(param: Option<&Value>) -> Value {
        let n = param
            .and_then(|p| p.as_str())
            .and_then(|s| u64::from_str_radix(s.trim_start_matches("0x"), 16).ok())
            .unwrap_or(30_000_000);
        json!({
            "number": format!("0x{n:x}"),
            "hash": format!("0x{n:064x}"),
            "parentHash": zero32(),
            "nonce": "0x0000000000000000",
            "sha3Uncles": zero32(),
            "logsBloom": format!("0x{}", "00".repeat(256)),
            "transactionsRoot": zero32(),
            "stateRoot": zero32(),
            "receiptsRoot": zero32(),
            "miner": format!("0x{}", "00".repeat(20)),
            "difficulty": "0x0",
            "totalDifficulty": "0x0",
            "extraData": "0x",
            "size": "0x0",
            "gasLimit": format!("0x{:x}", 30_000_000u64),
            "gasUsed": "0x0",
            "timestamp": format!("0x{:x}", 1_659_312_000u64),
            "transactions": [],
            "uncles": [],
            "baseFeePerGas": "0x1",
            "mixHash": zero32(),
        })
    }

    fn rpc_answer_one(method: &str, params: &Value) -> Value {
        match method {
            "eth_chainId" => json!("0x1"),
            "net_version" => json!("1"),
            "eth_blockNumber" => json!(format!("0x{:x}", 30_000_000u64)),
            "eth_getBalance" | "eth_getTransactionCount" => json!("0x0"),
            "eth_getCode" => json!("0x"),
            "eth_getStorageAt" => json!(zero32()),
            "eth_gasPrice" => json!("0x1"),
            "eth_getBlockByNumber" => block_json(params.get(0)),
            "eth_getBlockByHash" => block_json(None),
            _ => Value::Null,
        }
    }

    fn rpc_answer(body: &[u8]) -> Vec<u8> {
        let parsed: Value = serde_json::from_slice(body).unwrap_or(Value::Null);
        let one = |req: &Value| -> Value {
            let method = req.get("method").and_then(|m| m.as_str()).unwrap_or("");
            let params = req.get("params").cloned().unwrap_or(Value::Array(vec![]));
            json!({"jsonrpc": "2.0", "id": req.get("id").cloned().unwrap_or(Value::Null),
                   "result": rpc_answer_one(method, &params)})
        };
        let resp = match &parsed {
            Value::Array(reqs) => Value::Array(reqs.iter().map(one).collect()),
            other => one(other),
        };
        serde_json::to_vec(&resp).unwrap_or_default()
    }

    fn handle_conn(mut stream: TcpStream) {
        let mut buf = Vec::new();
        let mut tmp = [0u8; 4096];
        let header_end = loop {
            if let Some(p) = buf.windows(4).position(|w| w == b"\r\n\r\n") {
                break p + 4;
            }
            match stream.read(&mut tmp) {
                Ok(0) => return,
                Ok(n) => buf.extend_from_slice(&tmp[..n]),
                Err(_) => return,
            }
        };
        let headers = String::from_utf8_lossy(&buf[..header_end]).to_ascii_lowercase();
        let clen = headers
            .lines()
            .find_map(|l| l.strip_prefix("content-length:").and_then(|v| v.trim().parse::<usize>().ok()))
            .unwrap_or(0);
        while buf.len() < header_end + clen {
            match stream.read(&mut tmp) {
                Ok(0) => break,
                Ok(n) => buf.extend_from_slice(&tmp[..n]),
                Err(_) => break,
            }
        }
        let body = &buf[header_end..(header_end + clen).min(buf.len())];
        let data = rpc_answer(body);
        let head = format!(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
            data.len()
        );
        let _ = stream.write_all(head.as_bytes());
        let _ = stream.write_all(&data);
        let _ = stream.flush();
    }

    fn empty_rpc_url() -> String {
        static URL: OnceLock<String> = OnceLock::new();
        URL.get_or_init(|| {
            let listener = TcpListener::bind("127.0.0.1:0").expect("bind rpc stub");
            let addr = listener.local_addr().expect("local_addr");
            std::thread::spawn(move || {
                for stream in listener.incoming() {
                    if let Ok(s) = stream {
                        std::thread::spawn(move || handle_conn(s));
                    }
                }
            });
            format!("http://{addr}")
        })
        .clone()
    }

    // ---- fixture harness --------------------------------------------------
    fn repo_root() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .unwrap()
            .parent()
            .unwrap()
            .to_path_buf()
    }

    fn solc_available() -> bool {
        Command::new("solc").arg("--version").output().map(|o| o.status.success()).unwrap_or(false)
    }

    fn test_ctx() -> RuntimeContext {
        let rpc = empty_rpc_url();
        RuntimeContext {
            config: serde_json::from_value(json!({
                "atg_path": "", "scenarios_path": "", "output_path": "",
                "time_budget_s": 1,
                "source_rpc": rpc, "dest_rpc": rpc,
                "source_block": 30_000_000u64, "dest_block": 30_000_000u64,
                "random_seed": 42
            }))
            .unwrap(),
            atg: serde_json::from_value(json!({
                "bridge_name": "", "version": "1.0",
                "nodes": [], "edges": [], "invariants": []
            }))
            .unwrap(),
            hypotheses: serde_json::from_value(json!({"bridge_name": "", "scenarios": []})).unwrap(),
            verbose: false,
            address_overrides: vec![],
            address_aliases: vec![],
            auth_witness: None,
            replay_cache_dir: None,
            fork_spec_id: None,
            synthesize_unauth_lock: false,
            synthesize_unauth_unlock: false,
            baseline_mode: BaselineMode::Bridgesentry,
            contract_plan: ContractPlan::default(),
        }
    }

    fn load_spec(bench_dir: &Path) -> OfficialSpec {
        let p = bench_dir.join("official").join("spec.json");
        serde_json::from_str(&std::fs::read_to_string(&p).unwrap_or_else(|e| panic!("read {}: {e}", p.display())))
            .unwrap_or_else(|e| panic!("parse {}: {e}", p.display()))
    }

    fn ucall(w: &World, name: &str, func: &str, args: Vec<Token>) -> AttackCall {
        let idx = w.contract_index(name).unwrap_or_else(|| panic!("no contract `{name}` in world"));
        let c = &w.contracts[idx];
        let fs = c.abi.functions_by_name(func).unwrap_or_else(|_| panic!("{name} has no fn {func}"));
        let f = fs
            .iter()
            .find(|f| f.inputs.len() == args.len())
            .cloned()
            .unwrap_or_else(|| panic!("{name}.{func}: no overload with {} args", args.len()));
        AttackCall { idx, func: f, args }
    }

    fn addr_tok(a: Address) -> Token {
        Token::Address(to_h160(a))
    }
    fn contract_tok(w: &World, name: &str) -> Token {
        Token::Address(to_h160(w.contract(name).unwrap_or_else(|| panic!("no contract {name}")).addr))
    }
    fn u(s: &str) -> Token {
        Token::Uint(parse_uint(s).unwrap_or_else(|| panic!("bad uint {s}")))
    }

    /// Build vulnerable+patched worlds for `bench`, replay the sequence built
    /// by `make` (from the vulnerable world) on both, and return their gains.
    fn eval(
        bench: &str,
        make: impl Fn(&World) -> Seq,
    ) -> Option<(BTreeMap<String, EU256>, BTreeMap<String, EU256>)> {
        if !solc_available() {
            eprintln!("SKIP {bench}: solc not on PATH");
            return None;
        }
        let ctx = test_ctx();
        let bench_dir = repo_root().join("benchmarks").join(bench);
        let spec = load_spec(&bench_dir);
        let mut vw = World::build(&ctx, &spec, &bench_dir, "vulnerable").expect("build vulnerable");
        let mut pw = World::build(&ctx, &spec, &bench_dir, "patched").expect("build patched");
        // Deploy order is identical across variants, so contract indices match.
        assert!(
            vw.contracts.iter().zip(&pw.contracts).all(|(a, b)| a.addr == b.addr && a.name == b.name),
            "vulnerable/patched deployment addresses diverged"
        );
        let seq = make(&vw);
        let mut cov = CoverageTracker::default();
        let vr = run_trace(&mut vw, &spec, &seq, &mut cov);
        let mut cov2 = CoverageTracker::default();
        let pr = run_trace(&mut pw, &spec, &seq, &mut cov2);
        Some((vr.gains, pr.gains))
    }

    fn assert_exploit(bench: &str, vuln: &BTreeMap<String, EU256>, patched: &BTreeMap<String, EU256>) {
        assert!(
            !vuln.is_empty() && vuln.values().any(|v| *v > EU256::zero()),
            "{bench}: vulnerable variant must yield a positive attacker gain, got {vuln:?}"
        );
        assert!(
            patched.is_empty(),
            "{bench}: patched variant must yield no attacker gain, got {patched:?}"
        );
    }

    // ---- existing fixtures (regression) -----------------------------------
    #[test]
    fn qubit_official_exploit_and_patch() {
        let Some((vuln, patched)) = eval("qubit", |_w| {
            vec![ucall(
                _w,
                "QBridgeETH",
                "deposit",
                vec![addr_tok(Address::ZERO), u("500e18"), addr_tok(attacker())],
            )]
        }) else {
            return;
        };
        assert_exploit("qubit", &vuln, &patched);
    }

    // ---- new Group-A fixtures ---------------------------------------------
    #[test]
    fn feg_bridge_2024_official_exploit_and_patch() {
        // Faithful two-step FEG SmartBridge drain: the attacker publishes a
        // Wormhole message from their own address (sourceAddress = attacker)
        // whitelisting themselves, then publishes a RELEASE message draining
        // the reserve. The relayer delivers both faithfully.
        let Some((vuln, patched)) = eval("feg_bridge_2024", |w| {
            let set_trusted = Token::Bytes(ethers_core::abi::encode(&[
                Token::Uint(EU256::from(1u8)), // OP_SET_TRUSTED
                addr_tok(attacker()),          // whitelist the attacker as a trusted source
                Token::Uint(EU256::zero()),
            ]));
            let release = Token::Bytes(ethers_core::abi::encode(&[
                Token::Uint(EU256::from(2u8)), // OP_RELEASE
                addr_tok(attacker()),          // pay the attacker
                Token::Uint(parse_uint("500000e18").unwrap()),
            ]));
            vec![
                ucall(w, "WormholeCore", "publishMessage", vec![set_trusted]),
                ucall(w, "WormholeCore", "publishMessage", vec![release]),
            ]
        }) else {
            return;
        };
        assert_exploit("feg_bridge_2024", &vuln, &patched);
    }

    #[test]
    fn crosscurve_2026_official_exploit_and_patch() {
        // Attacker calls the express path directly on the destination with a
        // fabricated commandId the gateway never attested, and a payload paying
        // itself. Vulnerable: no gateway validation -> PortalV2 pays out.
        // Patched: expressExecute consults the gateway -> reverts.
        let Some((vuln, patched)) = eval("crosscurve", |w| {
            let mut cid = vec![0u8; 32];
            cid[31] = 1; // arbitrary commandId the gateway never attested
            let forged_command = Token::FixedBytes(cid);
            let payload = Token::Bytes(ethers_core::abi::encode(&[
                addr_tok(attacker()),
                Token::Uint(parse_uint("500000e18").unwrap()),
            ]));
            vec![ucall(w, "ReceiverAxelar", "expressExecute", vec![forged_command, payload])]
        }) else {
            return;
        };
        assert_exploit("crosscurve", &vuln, &patched);
    }

    #[test]
    fn ronin_2024_official_exploit_and_patch() {
        // Attacker withdraws from the mainchain gateway with an EMPTY operator
        // signer set. Vulnerable: totalOperatorWeight == 0 so minimumVoteWeight
        // is 0 and the empty set passes. Patched: initializeV4 ran initializeV3,
        // so the 70% threshold is enforced and the empty set is rejected.
        let Some((vuln, patched)) = eval("ronin_2024", |w| {
            vec![ucall(
                w,
                "RoninGatewayV3",
                "withdraw",
                vec![
                    addr_tok(attacker()),
                    Token::Uint(parse_uint("500000e18").unwrap()),
                    Token::Array(vec![]), // no operator signatures
                ],
            )]
        }) else {
            return;
        };
        assert_exploit("ronin_2024", &vuln, &patched);
    }

    #[test]
    fn polynetwork_2021_official_exploit_and_patch() {
        // Two steps. (1) via the faithful relay, a crossChain message targets
        // ECCD.putCurEpochConPubKeyBytes to replace the keeper with the attacker
        // (the relay reports the attacker's true source address, which ECCD's
        // owner-only setter ignores). (2) now the keeper, the attacker calls the
        // manager directly and forges fromContract = the registered source proxy
        // so LockProxy.unlock pays out. Patched: the message may not target ECCD,
        // the keeper is never replaced, and step 2 fails the keeper check.
        let Some((vuln, patched)) = eval("polynetwork", |w| {
            let set_keeper_args = Token::Bytes(ethers_core::abi::encode(&[addr_tok(attacker())]));
            let unlock_args = Token::Bytes(ethers_core::abi::encode(&[
                addr_tok(attacker()),
                Token::Uint(parse_uint("500000e18").unwrap()),
            ]));
            vec![
                // step 1: source crossChain -> faithful relay -> replace keeper
                ucall(
                    w,
                    "SourceCrossChain",
                    "crossChain",
                    vec![
                        contract_tok(w, "EthCrossChainData"),
                        Token::String("putCurEpochConPubKeyBytes(address,address)".into()),
                        set_keeper_args,
                    ],
                ),
                // step 2: direct manager call as the (now attacker-controlled) keeper
                ucall(
                    w,
                    "EthCrossChainManager",
                    "verifyHeaderAndExecuteTx",
                    vec![
                        contract_tok(w, "LockProxy"),
                        Token::String("unlock(address,uint256,address)".into()),
                        unlock_args,
                        contract_tok(w, "SrcDeposit"), // forged fromContract = registered proxy
                    ],
                ),
            ]
        }) else {
            return;
        };
        assert_exploit("polynetwork", &vuln, &patched);
    }

    #[test]
    fn verus_2026_official_exploit_and_patch() {
        // Attacker makes a small, honest export (1e18) on the Verus surrogate,
        // then over-claims a huge payout (500000e18) against that attested
        // export. Vulnerable: checkCCEValues doesn't reconcile payout vs the
        // committed source value -> pays out. Patched: reconciliation reverts.
        let Some((vuln, patched)) = eval("verus", |w| {
            let mut export_id = vec![0u8; 32];
            export_id[31] = 0x0a;
            let eid = Token::FixedBytes(export_id);
            vec![
                ucall(
                    w,
                    "VerusExportSurrogate",
                    "export",
                    vec![eid.clone(), addr_tok(attacker()), Token::Uint(parse_uint("1e18").unwrap())],
                ),
                ucall(
                    w,
                    "VerusBridge",
                    "submitImports",
                    vec![addr_tok(attacker()), Token::Uint(parse_uint("500000e18").unwrap()), eid],
                ),
            ]
        }) else {
            return;
        };
        assert_exploit("verus", &vuln, &patched);
    }

    #[test]
    fn nomad_official_exploit_and_patch() {
        let Some((vuln, patched)) = eval("nomad", |w| {
            // Attacker calls the destination release entrypoint directly with a
            // forged message body (recipient = attacker). The vulnerable Replica
            // accepts the unproven (zero-root) message; the patched one rejects it.
            let body = Token::Tuple(vec![
                Token::Uint(EU256::from(2000u64)), // originDomain
                Token::Uint(EU256::from(1000u64)), // destinationDomain
                Token::Uint(EU256::from(1u64)),    // nonce
                addr_tok(attacker()),              // sender
                addr_tok(attacker()),              // recipient
                contract_tok(w, "Representation"), // token
                parse_uint("500e18").map(Token::Uint).unwrap(),
            ]);
            vec![ucall(w, "NomadBridgeRouter", "processAndRelease", vec![body])]
        }) else {
            return;
        };
        assert_exploit("nomad", &vuln, &patched);
    }
}
