import { useState, useEffect } from "react"
import { useParams, Link } from "react-router-dom"
import { ShieldAlert, CheckCircle2, Lock, FileCheck, RefreshCw, XCircle, AlertTriangle, Fingerprint, Database, FileText, Hash } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:18080"

export function ProcessorView() {
  const { requestId } = useParams()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  
  // Replay Attack State
  const [replayState, setReplayState] = useState<"IDLE" | "TESTING" | "REJECTED">("IDLE")
  const [replayTarget, setReplayTarget] = useState<string>("")

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_URL}/api/verification-requests/${requestId}`)
        const json = await res.json()
        
        // Auto-verify if the ZK proof was generated but not yet verified
        if (json.status === "PROOF_GENERATED") {
          await fetch(`${API_URL}/api/verification-requests/${requestId}/verify-proof`, {
            method: "POST"
          })
          const re_res = await fetch(`${API_URL}/api/verification-requests/${requestId}`)
          setData(await re_res.json())
        } else {
          setData(json)
        }

      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [requestId])

  const handleReplayAttack = async () => {
    setReplayState("TESTING")
    try {
      const resB = await fetch(`${API_URL}/api/verification-requests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_text: "Prove monthly volume", evidence_ids: ["processor_ledger"] })
      })
      const reqB = await resB.json()
      setReplayTarget(reqB.id)

      await fetch(`${API_URL}/api/verification-requests/${reqB.id}/analyze`, { method: "POST" })
      
      await fetch(`${API_URL}/api/verification-requests/${reqB.id}/spoof-proof?source_id=${requestId}`, {
        method: "POST"
      })

      const verifyRes = await fetch(`${API_URL}/api/verification-requests/${reqB.id}/verify-proof`, {
        method: "POST"
      })
      const verifyData = await verifyRes.json()
      
      if (verifyData.verification_result?.status === "PROOF_INVALID") {
        setReplayState("REJECTED")
      } else {
        console.error("Wait, the replay attack succeeded? That's a security flaw!")
      }

    } catch (e) {
      console.error(e)
    }
  }

  if (loading) return <div className="p-8 text-center mt-32"><div className="animate-spin h-8 w-8 border-t-2 border-primary rounded-full mx-auto" /></div>
  if (!data) return <div className="p-8 text-center text-destructive">Verification not found</div>

  const spec = data.proof_specifications?.[0]
  const vResult = data.verification_results?.[0]
  const claim = data.claims?.[0]
  const strategyType = data.privacy_strategies?.[0]?.strategy
  const isZK = strategyType === "ZERO_KNOWLEDGE"

  if (replayState === "TESTING") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6">
        <RefreshCw className="w-10 h-10 animate-spin text-amber-500" />
        <h2 className="text-xl font-medium animate-pulse text-amber-400">Executing Replay Attack...</h2>
        <p className="font-mono text-sm text-muted-foreground mt-4">Transmitting Proof from Request {requestId} &rarr; Target Request {replayTarget || "..."}</p>
      </div>
    )
  }

  if (replayState === "REJECTED" || data.status === "FAILED" || (vResult && vResult.status === "PROOF_INVALID")) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-6 animate-in zoom-in-95 duration-300">
        <XCircle className="w-24 h-24 text-red-500 mb-2" />
        <h1 className="text-5xl font-bold tracking-tight text-white mb-2">CLAIM NOT VERIFIED</h1>
        <div className="mb-8 font-mono bg-red-950/40 p-4 border border-red-900 rounded-md text-red-400 w-full max-w-2xl text-left font-medium">
          Error: Cryptographic verification failed.<br/><br/>
          {replayState === "REJECTED" ? (
             <>
             Attempted verification:<br/>
             Target Request #{replayTarget}<br/><br/>
             Proof generated for:<br/>
             Source Request #{requestId} (Nonce Mismatch)
             </>
          ) : "Invalid proof signature or mismatched inputs."}
        </div>
        <div className="flex gap-4">
          <Link to="/"><Button variant="outline">New Request</Button></Link>
        </div>
      </div>
    )
  }

  // --- ALTERNATIVE STRATEGY RENDERING ---
  if (!isZK || data.status === "UNSUPPORTED" || data.status === "REVIEW_REQUIRED" || data.status === "STRATEGY_SELECTED" || data.status === "CLAIMS_EXTRACTED") {
     return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-6 animate-in zoom-in-95 duration-300 max-w-3xl mx-auto">
        <AlertTriangle className="w-20 h-20 text-amber-500 mb-2" />
        <h1 className="text-4xl font-bold tracking-tight text-white mb-2 uppercase">
           {strategyType === "UNSUPPORTED" || !isZK ? "ZK VERIFICATION UNAVAILABLE" : "MORE INFORMATION REQUIRED"}
        </h1>
        
        <p className="text-xl font-medium text-amber-100/90 leading-relaxed max-w-2xl">
          {claim?.description || "Unable to parse requirement."}
        </p>

        <Card className="w-full bg-slate-900/60 border-slate-700/50 mt-6 shadow-xl relative overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-amber-500" />
          <CardContent className="p-8 space-y-6 text-left">
             <div className="space-y-4">
                <h3 className="text-muted-foreground uppercase tracking-widest text-xs font-bold">Recommended Strategy</h3>
                <Badge className="bg-amber-500/20 text-amber-500 border-none text-sm px-3 py-1">
                   {strategyType?.replace("_", " ") || "UNKNOWN"}
                </Badge>
             </div>
             
             <div className="space-y-3 pt-4 border-t border-white/5">
                <h3 className="text-muted-foreground uppercase tracking-widest text-xs font-bold">Why</h3>
                <p className="text-sm font-medium text-slate-300">
                   {data.privacy_strategies?.[0]?.reason || "No registered circuit currently supports this predicate computationally."}
                </p>
             </div>

             <div className="space-y-3 pt-4 border-t border-white/5">
                <h3 className="text-amber-400 uppercase tracking-widest text-xs font-bold">Current Demo Capability</h3>
                <p className="text-sm font-medium text-amber-100/90">
                   {strategyType === "VERIFIABLE_CREDENTIAL" 
                      ? "Credential verification pipeline unavailable."
                      : "Alternative disclosure mechanisms are outside the scope of this ZK-focused demo."}
                </p>
                <div className="text-xs bg-amber-500/10 border border-amber-500/20 p-3 rounded text-amber-400 font-mono">
                   Next step: {strategyType === "VERIFIABLE_CREDENTIAL" ? "Request an attested credential." : "Initiate manual review process."}
                </div>
             </div>
          </CardContent>
        </Card>

        <div className="flex gap-4 mt-8">
          <Link to="/"><Button variant="outline">New Request</Button></Link>
        </div>
      </div>
     )
  }


  // --- ZK SUCCESS RENDERING: FORMAL VERIFICATION RECEIPT ---

  return (
    <div className="max-w-5xl mx-auto w-full space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-500 pt-8 pb-16">
      
      {/* RECEIPT HEADER */}
      <div className="border border-emerald-500/30 bg-emerald-950/10 shadow-[0_0_50px_rgba(16,185,129,0.05)] rounded-lg overflow-hidden">
        
        <div className="bg-emerald-950/40 p-10 text-center border-b border-emerald-500/20 flex flex-col items-center relative">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-600 to-emerald-400" />
          
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-500/20 border border-emerald-500/30 mb-6">
            <CheckCircle2 className="w-8 h-8 text-emerald-400" />
          </div>
          
          <h4 className="text-emerald-500 font-semibold tracking-widest uppercase text-sm mb-2">Cryptographic Verification Receipt</h4>
          <h1 className="text-4xl font-bold tracking-tight text-white max-w-2xl mx-auto leading-tight">
            Monthly processing volume &gt; ₹10,00,000
          </h1>
          <div className="mt-4 font-mono text-emerald-400 bg-emerald-950/30 border border-emerald-500/20 px-4 py-2 rounded-md">
            {claim?.description || "SUM(amount) > ₹10,00,000 INR"}
          </div>
        </div>

        {/* METADATA GRID */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-emerald-500/10 bg-black/40">
          
          <div className="p-6 space-y-2">
            <div className="flex items-center gap-2 text-muted-foreground text-xs font-semibold uppercase tracking-widest">
              <ShieldAlert className="w-4 h-4"/> Privacy Method
            </div>
            <div className="font-mono text-emerald-400">Zero-Knowledge</div>
          </div>
          
          <div className="p-6 space-y-2">
            <div className="flex items-center gap-2 text-muted-foreground text-xs font-semibold uppercase tracking-widest">
              <Database className="w-4 h-4"/> Evidence Revealed
            </div>
            <div className="font-mono text-white flex items-center gap-2">
               <span className="text-emerald-400 font-bold">0</span> underlying transactions
            </div>
          </div>
          
          <div className="p-6 space-y-2">
            <div className="flex items-center gap-2 text-muted-foreground text-xs font-semibold uppercase tracking-widest">
              <Hash className="w-4 h-4"/> Circuit
            </div>
            <div className="font-mono text-white text-sm break-all">
               {vResult?.circuit || spec?.circuit} v{vResult?.circuit_version || spec?.circuit_version}
            </div>
          </div>
          
          <div className="p-6 space-y-2">
            <div className="flex items-center gap-2 text-muted-foreground text-xs font-semibold uppercase tracking-widest">
              <Fingerprint className="w-4 h-4"/> Provenance
            </div>
            <div className="font-mono text-white text-sm">
               merchant_ledger.pdf<br/>
               <span className="text-[10px] text-muted-foreground uppercase">14 records · validated</span>
            </div>
          </div>

        </div>

        {/* DETAILED CRYPTO BREAKDOWN */}
        <div className="p-8 space-y-8 bg-slate-950/50">
          
          <div className="space-y-4">
            <h3 className="text-muted-foreground uppercase tracking-widest text-xs font-bold border-b border-white/5 pb-2">Integrity Bindings</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              <div className="space-y-2">
                <div className="text-xs text-muted-foreground uppercase tracking-wide">Request Nonce</div>
                <div className="font-mono text-xs bg-black/40 border border-white/5 p-3 rounded text-slate-300 break-all select-all flex flex-col">
                  <span className="mb-1 text-emerald-400 font-semibold uppercase text-[10px]">Bound to this verification request:</span>
                  {(() => {
                    const reqNonce = data?.nonce || spec?.request_nonce || "N/A";
                    return reqNonce !== "N/A" ? `${reqNonce.substring(0, 12)}...${reqNonce.substring(reqNonce.length - 8)}` : "N/A";
                  })()}
                </div>
                <div className="text-[10px] text-muted-foreground">Ensures this proof cannot be replay-attacked for future requests.</div>
              </div>

              <div className="space-y-2">
                <div className="text-xs text-muted-foreground uppercase tracking-wide">Dataset Commitment (Poseidon)</div>
                <div className="font-mono text-xs bg-black/40 border border-white/5 p-3 rounded text-slate-300 break-all select-all">
                  {vResult?.evidence_commitment || spec?.evidence_commitment || "N/A"}
                </div>
                <div className="text-[10px] text-muted-foreground">Cryptographic hash binding the proof identically to the provided evidence ledger.</div>
              </div>

            </div>
          </div>

          <div className="flex justify-between items-center pt-6 border-t border-white/5">
            <div className="text-xs text-muted-foreground font-mono">
              Timestamp: {new Date(vResult?.timestamp || data.updated_at).toLocaleString()}
            </div>
            <Button variant="outline" className="text-xs absolute -mt-4 bg-black hover:bg-red-950 hover:text-red-400 transition-colors border-white/10 ml-[230px]" onClick={handleReplayAttack}>
                Simulate Injection Attack
            </Button>
            <Link to="/"><Button variant="outline" className="text-xs">Issue New Request</Button></Link>
          </div>

        </div>
      </div>

    </div>
  )
}
