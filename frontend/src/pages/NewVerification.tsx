import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Shield, Loader2, CheckCircle2, Lock, ArrowRight, UploadCloud, AlertTriangle, FileText, CheckCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { motion, AnimatePresence } from "framer-motion"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:18080"

export function NewVerification() {
  const navigate = useNavigate()
  const [requestText, setRequestText] = useState("")
  const [file, setFile] = useState<File | null>(null)
  
  // 0: request, 1: understanding, 2: claim compiled, 3: proof generation, 4: verified
  const [step, setStep] = useState(0) 
  const [pipelineState, setPipelineState] = useState<number>(0)
  const [reqId, setReqId] = useState("")
  const [analysis, setAnalysis] = useState<any>(null)
  const [uploadError, setUploadError] = useState("")
  const [proofError, setProofError] = useState("")

  const [genSteps, setGenSteps] = useState<number>(0)
  
  const handleAnalyze = async () => {
    if (!requestText.trim()) {
        setUploadError("Please enter a request.")
        return
    }
    
    setStep(1)
    let currentPipe = 0
    const pipeInterval = setInterval(() => {
        currentPipe++
        setPipelineState(currentPipe)
        if (currentPipe >= 4) clearInterval(pipeInterval)
    }, 1000)

    try {
        let evidenceIdStr = ""

        if (file) {
            // Unused in new demo flow, fallback
            const formData = new FormData()
            formData.append("file", file)
            const uploadRes = await fetch(`${API_URL}/api/evidence-sources/upload`, {
                method: "POST",
                body: formData
            })
            if (!uploadRes.ok) throw new Error((await uploadRes.json()).detail || "Failed to extract pdf")
            evidenceIdStr = (await uploadRes.json()).evidence_id
        } else {
            // 1. Fetch Demo Processor Ledger
            const procRes = await fetch(`${API_URL}/api/demo/processor/issue-attestation/MERCHANT-42`)
            const procPayload = await procRes.json()
            
            // 2. Upload Attested Ledger
            const uploadRes = await fetch(`${API_URL}/api/evidence-sources/upload-attested`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(procPayload)
            })
            if (!uploadRes.ok) throw new Error((await uploadRes.json()).detail || "Failed to submit attested ledger")
            evidenceIdStr = (await uploadRes.json()).id
        }
        
        const res = await fetch(`${API_URL}/api/verification-requests`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ request_text: requestText, evidence_ids: [evidenceIdStr] }) 
        })
        const data = await res.json()
        setReqId(data.id)
        
        const analyzeRes = await fetch(`${API_URL}/api/verification-requests/${data.id}/analyze`, { method: "POST" })
        const analyzeData = await analyzeRes.json()
        
        if (!analyzeRes.ok) throw new Error(analyzeData.detail || "Analysis failed")
        
        setAnalysis(analyzeData)
        
        setTimeout(() => {
            setStep(2)
        }, 1200)

    } catch (e: any) {
        setUploadError(e.message || "An error occurred")
        setStep(0)
    }
  }

  const handleGenerateProof = async () => {
    setStep(3)
    setProofError("")
    
    let currentStep = 0
    const interval = setInterval(() => {
      currentStep++
      // don't go past 4 while waiting for backend
      if (currentStep <= 4) setGenSteps(currentStep)
    }, 800)

    try {
      const res = await fetch(`${API_URL}/api/verification-requests/${reqId}/generate-proof`, {
        method: "POST"
      })
      
      clearInterval(interval)
      
      let data = null
      try {
          data = await res.json()
      } catch (e) {
          throw new Error("Received malformed JSON from server")
      }
      
      if (!res.ok) {
        throw new Error(data?.detail || data?.error || "Proof generation request failed")
      }
      
      // Inspect proof status and throw if failed
      if (
        data.status === "PROOF_INVALID" || 
        data.status === "PROOF_GENERATION_FAILED" || 
        data.status === "PROOF_VERIFICATION_FAILED" ||
        data.status === "ERROR"
      ) {
         throw new Error(data.error || `Proof generation failed with status: ${data.status}`)
      }
      
      // Complete remaining steps visually
      setGenSteps(5)
      setTimeout(() => {
        setGenSteps(6) 
        setTimeout(() => navigate(`/processor/${reqId}`), 1500)
      }, 500)
      
    } catch (e: any) {
      clearInterval(interval)
      setProofError(e.message || "An error occurred during proof generation")
      setStep(2) // go back to decision panel visually
    }
  }

  const claim = analysis?.claims?.[0]
  const strategy = analysis?.privacy_strategies?.[0]
  const isZK = strategy?.strategy === "ZERO_KNOWLEDGE"
  const isCircuitAvailable = strategy?.feasibility_breakdown?.circuit_available ?? false

  return (
    <div className="max-w-4xl mx-auto w-full pb-20 pt-8">
      
      {/* SCREEN 1: THE REQUEST COMPOSER */}
      {step === 0 && (
        <motion.div 
            initial={{ opacity: 0, y: 20 }} 
            animate={{ opacity: 1, y: 0 }} 
            className="space-y-6 max-w-2xl mx-auto"
        >
          <div className="text-center space-y-4 mb-12">
            <h3 className="text-sm tracking-widest uppercase font-bold text-slate-400">Step 01 / 03</h3>
            <h1 className="text-[40px] font-bold tracking-tight">What does the processor need to verify?</h1>
          </div>
          
          <div className="glass-panel overflow-hidden rounded-2xl relative">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-transparent opacity-50"></div>
            <div className="p-8 space-y-6">
              <textarea 
                className="w-full bg-transparent border-0 border-b border-white/10 rounded-none p-2 text-2xl md:text-3xl font-medium focus:ring-0 focus:border-blue-500 resize-none placeholder:text-slate-600 leading-relaxed min-h-[140px] outline-none text-white"
                placeholder="E.g., Prove that our total processing volume over the last 6 months exceeded ₹10,00,000 without revealing transactions."
                value={requestText}
                onChange={e => setRequestText(e.target.value)}
              />

              <div>
                <label className="text-xs font-bold uppercase tracking-widest text-slate-400 block mb-4">DEMO PROCESSOR — SIMULATED TRUSTED ISSUER</label>
                <div 
                  className="flex items-center gap-4 p-4 border border-blue-500/50 bg-blue-900/10 rounded-xl hover:bg-blue-900/20 transition-colors" 
                >
                  <div className="w-12 h-12 rounded-lg bg-blue-500/20 flex items-center justify-center shrink-0">
                    <Lock className="w-6 h-6 text-blue-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                     <div className="font-semibold text-white truncate">Acme Payments (Simulated Processor)</div>
                     <div className="text-sm text-blue-400">Ledger automatically retrieved & cryptographically signed via API</div>
                  </div>
                  <CheckCircle className="w-5 h-5 text-emerald-500 shrink-0" />
                </div>
              </div>
              
              {uploadError && (
                 <div className="text-red-400 text-sm font-medium bg-red-500/10 p-3 rounded-lg border border-red-500/20 flex gap-2 items-center">
                     <AlertTriangle className="w-4 h-4"/>
                     {uploadError}
                 </div>
              )}
            </div>
          </div>
          
          <div className="flex justify-center pt-6">
            <Button size="lg" disabled={!requestText.trim()} className="h-[60px] px-10 text-lg w-full max-w-sm rounded-[24px] gap-3 bg-white hover:bg-gray-100 text-black shadow-lg hover:shadow-xl transition-all font-semibold" onClick={handleAnalyze}>
              Analyze Requirement <ArrowRight className="h-5 w-5" />
            </Button>
          </div>
        </motion.div>
      )}

      {/* SCREEN 2: PIPELINE STATE (AI Understanding) */}
      {step === 1 && (
        <motion.div 
            initial={{ opacity: 0, scale: 0.95 }} 
            animate={{ opacity: 1, scale: 1 }} 
            className="pt-20 flex flex-col items-center max-w-lg mx-auto"
        >
          <div className="text-sm tracking-widest text-blue-400 font-bold uppercase mb-8">AI PLANNING PIPELINE</div>
          <div className="w-full space-y-4">
             <PipelineRow active={pipelineState >= 0} text="Reading requirement" />
             <PipelineRow active={pipelineState >= 1} text="Identifying claim" />
             <PipelineRow active={pipelineState >= 2} text="Mapping evidence" />
             <PipelineRow active={pipelineState >= 3} text="Selecting privacy strategy" />
             <PipelineRow active={pipelineState >= 4} text="Checking proof capability" />
          </div>
        </motion.div>
      )}

      {/* SCREEN 3: DECISION PANEL */}
      {step === 2 && analysis && claim && strategy && (
        <motion.div 
            initial={{ opacity: 0, y: 20 }} 
            animate={{ opacity: 1, y: 0 }} 
            className="space-y-12 max-w-4xl mx-auto"
        >
          <div className="text-center space-y-2 mb-12">
            <h3 className="text-sm tracking-widest uppercase font-bold text-slate-400 mb-4">CLAIM COMPILED</h3>
            <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-white mb-2 leading-tight">
              {claim.description}
            </h1>
            <div className="inline-flex items-center justify-center bg-black/50 border border-slate-800 px-4 py-2 rounded-lg font-mono text-sm text-slate-400">
               {claim.operation}({claim.field}) {claim.operator} {claim.threshold} {claim.unit}
            </div>
            
            {claim.ambiguity && (
              <div className="mt-8 p-4 border border-red-500/30 bg-red-500/5 text-red-400 rounded-xl max-w-lg mx-auto flex gap-3 text-left items-start">
                <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                <div className="text-sm">
                  <span className="font-bold block mb-1">Needs Clarification</span>
                  {claim.ambiguity}
                </div>
              </div>
            )}
          </div>

          <div className="glass-panel overflow-hidden rounded-[32px] relative border border-slate-800">
            <div className="p-8 md:p-12">
              <div className="text-center mb-10">
                <div className="text-sm font-bold tracking-widest uppercase text-slate-400 mb-2">PRIVACY STRATEGY</div>
                <div className={`text-2xl font-bold tracking-wider ${isZK ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {strategy.strategy.replace("_", " ")}
                </div>
                {!isCircuitAvailable && isZK && (
                  <div className="text-amber-400 font-medium text-sm mt-4 border border-amber-500/30 bg-amber-500/5 py-2 px-4 rounded-md inline-block">
                    No registered active circuit supports this predicate.
                  </div>
                )}
              </div>

              {isZK && isCircuitAvailable && (
                <div className="grid md:grid-cols-2 gap-8 items-center border-t border-slate-800 pt-10">
                  <div className="space-y-4 pr-6 border-r border-slate-800">
                     <h4 className="text-slate-400 font-bold tracking-widest text-xs uppercase mb-6">Why this strategy?</h4>
                     <p className="text-lg leading-relaxed text-slate-300">
                       The processor only needs to know whether the threshold was satisfied—not the transactions that produced it.
                     </p>
                  </div>
                  
                  <div className="pl-4">
                     <div className="flex flex-col space-y-6">
                        <div className="flex items-center justify-between opacity-50">
                          <span className="text-sm font-bold uppercase tracking-wider">CONVENTIONAL</span>
                          <span className="text-sm text-slate-400">Ledger disclosed</span>
                        </div>
                        
                        <div className="flex items-center justify-between border-l-2 border-emerald-500 pl-4">
                          <div className="space-y-1">
                             <span className="text-sm font-bold uppercase tracking-wider text-emerald-400">PROOFBRIDGE</span>
                             <div className="text-3xl font-extrabold text-white">0</div>
                             <div className="text-xs text-slate-400 uppercase tracking-widest font-bold">Transactions Disclosed</div>
                          </div>
                          <Lock className="w-8 h-8 text-emerald-400" />
                        </div>
                     </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-col items-center pt-4 space-y-4">
            {strategy.strategy !== "UNSUPPORTED" && strategy.strategy !== "HUMAN_REVIEW" && !claim.ambiguity && (!isZK || isCircuitAvailable) ? (
              <Button size="lg" className="h-[60px] px-10 text-lg rounded-[24px] w-full max-w-sm gap-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold shadow-[0_0_20px_rgba(37,99,235,0.3)] transition-all" onClick={handleGenerateProof}>
                Generate Verification Package <ArrowRight className="w-5 h-5" />
              </Button>
            ) : (
              <Button size="lg" disabled variant="outline" className="h-[60px] px-10 text-lg rounded-[24px] w-full max-w-sm gap-2 opacity-50">
                Alternative Pipeline Required
              </Button>
            )}
            
            {proofError && (
              <div className="text-red-400 max-w-md w-full font-medium bg-red-500/10 p-4 rounded-lg flex items-start text-left gap-3 border border-red-500/20">
                <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                <span className="text-sm">
                  <span className="font-bold block mb-1">Proof Generation Failed</span>
                  {proofError}
                </span>
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* SCREEN 4: PROOF GENERATION */}
      {step === 3 && (
        <motion.div 
            initial={{ opacity: 0, scale: 0.95 }} 
            animate={{ opacity: 1, scale: 1 }} 
            className="max-w-xl mx-auto pt-16"
        >
          <div className="glass-panel border border-slate-800 rounded-3xl p-10 space-y-8 relative overflow-hidden">
            {genSteps < 6 ? (
              <>
                <h3 className="text-xl font-bold tracking-wider mb-8 text-white flex items-center justify-between">
                  <span>COMPILING VERIFICATION</span>
                  <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
                </h3>
                <div className="space-y-5">
                  <AnimatedCheck active={genSteps >= 1} loading={genSteps === 0} text="Claim validated" />
                  <AnimatedCheck active={genSteps >= 2} loading={genSteps === 1} text="Evidence validated" />
                  <AnimatedCheck active={genSteps >= 3} loading={genSteps === 2} text="Dataset committed" />
                  {isZK && <AnimatedCheck active={genSteps >= 4} loading={genSteps === 3} text="Circuit authorized" />}
                  {isZK && <AnimatedCheck active={genSteps >= 5} loading={genSteps === 4} text="Generating Groth16 proof" />}
                  <AnimatedCheck active={false} loading={genSteps === 5} text="Verifying proof" />
                </div>
              </>
            ) : (
              <motion.div 
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                className="py-10 flex flex-col items-center justify-center"
              >
                <div className="w-20 h-20 bg-emerald-500/20 rounded-full flex items-center justify-center mb-6 shadow-[0_0_50px_rgba(16,185,129,0.3)]">
                  <CheckCircle className="w-10 h-10 text-emerald-400" />
                </div>
                <h1 className="text-3xl font-bold tracking-tight text-white mb-2">PROOF VERIFIED</h1>
                <p className="text-emerald-400 font-medium">Transitioning to Processor Console...</p>
              </motion.div>
            )}
          </div>
        </motion.div>
      )}
    </div>
  )
}

function PipelineRow({ active, text }: { active: boolean, text: string }) {
  return (
    <div className={`flex items-center gap-4 transition-all duration-300 p-3 rounded-lg ${active ? 'bg-blue-500/10 text-white' : 'text-slate-500'}`}>
      {active ? <CheckCircle2 className="w-5 h-5 text-blue-500" /> : <div className="w-5 h-5 rounded-full border-2 border-slate-700" />}
      <span className="font-semibold">{text}</span>
    </div>
  )
}

function AnimatedCheck({ active, loading, text }: { active: boolean, loading: boolean, text: string }) {
  return (
    <div className={`flex items-center gap-4 transition-all duration-300 font-mono text-sm ${active ? 'text-white' : loading ? 'text-blue-400' : 'text-slate-600'}`}>
      <div className="w-5 h-5 flex items-center justify-center shrink-0">
         {active ? <span className="text-emerald-400 font-bold text-lg">✓</span> : (loading ? <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"/> : <span>[ ]</span>)}
      </div>
      <span>{text}</span>
    </div>
  )
}
