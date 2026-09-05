import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Shield, Lock, EyeOff, FileDigit, BrainCircuit, ActivitySquare } from "lucide-react"
import { motion } from "framer-motion"

export function Landing() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[90vh] text-center space-y-16 pb-20 pt-10">
      
      <div className="space-y-6 max-w-4xl px-4 z-10">
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-block border border-blue-500/20 bg-blue-500/5 text-blue-400 text-[11px] font-bold uppercase tracking-[0.3em] px-4 py-1.5 rounded-full mb-4"
        >
          AI-Powered Evidence Firewall
        </motion.div>
        <motion.h1 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-5xl md:text-[76px] leading-[1.1] font-extrabold tracking-tight"
        >
          Prove what matters. <br/>
          <span className="text-white">Reveal nothing more.</span>
        </motion.h1>
        <motion.p 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-xl md:text-2xl text-slate-400 max-w-2xl mx-auto"
        >
          Turn natural-language verification requests into minimum-disclosure cryptographic proofs.
        </motion.p>
      </div>

      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4, duration: 1 }}
        className="w-full max-w-5xl py-12 relative z-10"
      >
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 md:gap-0 relative">
          {/* Animated Background Line */}
          <div className="hidden md:block absolute top-1/2 left-0 w-full h-[2px] bg-slate-800 -z-10 translate-y-[-50%]">
             <motion.div 
               initial={{ width: "0%" }}
               animate={{ width: "100%" }}
               transition={{ duration: 1.5, ease: "easeOut", delay: 0.6 }}
               className="h-full bg-gradient-to-r from-blue-500 via-emerald-400 to-emerald-500"
             />
          </div>
          
          <FlowNode icon={<FileDigit className="w-5 h-5"/>} label="REQUEST" delay={0.6} />
          <FlowNode icon={<BrainCircuit className="w-5 h-5 text-blue-400"/>} label="AI PLANNER" delay={0.9} color="border-blue-500/30 text-blue-400 bg-black" />
          <FlowNode icon={<Shield className="w-5 h-5 text-slate-300"/>} label="EVIDENCE" delay={1.2} />
          <FlowNode icon={<Lock className="w-5 h-5 text-indigo-400"/>} label="ZERO-KNOWLEDGE" delay={1.5} color="border-indigo-500/30 text-indigo-400 bg-black" />
          <FlowNode icon={<ActivitySquare className="w-5 h-5 text-emerald-400"/>} label="VERIFIED" delay={1.8} color="border-emerald-500/50 text-emerald-400 bg-black shadow-[0_0_30px_rgba(16,185,129,0.3)]" />
        </div>
      </motion.div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 2.1 }}
        className="flex flex-col sm:flex-row gap-6 z-10"
      >
        <Link to="/new">
          <Button size="lg" className="w-full md:w-64 text-base font-semibold px-8 py-7 bg-blue-600 hover:bg-blue-500 text-white rounded-xl shadow-[0_0_30px_rgba(37,99,235,0.2)]">
            Start a Verification
          </Button>
        </Link>
        <Link to="/dash">
          <Button variant="outline" size="lg" className="w-full md:w-64 text-base font-semibold px-8 py-7 border-slate-700 hover:bg-slate-800 text-slate-300 rounded-xl">
            View Processor Console
          </Button>
        </Link>
      </motion.div>

      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2.3 }}
        className="pt-10 pb-4 z-10"
      >
        <h3 className="text-sm md:text-base font-semibold tracking-widest text-slate-300 uppercase space-x-2 md:space-x-4">
          <span className="text-blue-400">AI plans</span>
          <span className="text-slate-600">·</span>
          <span className="text-slate-300">Deterministic systems validate</span>
          <span className="text-slate-600">·</span>
          <span className="text-emerald-400">Cryptography proves</span>
          <span className="text-slate-600">·</span>
          <span className="text-white">Humans decide</span>
        </h3>
      </motion.div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 2.5 }}
        className="grid md:grid-cols-3 gap-6 mt-16 max-w-5xl z-10 w-full px-4"
      >
        <FeatureCard 
          title="MINIMUM DISCLOSURE"
          description="Only the claim is revealed. Underlying evidence remains private."
        />
        <FeatureCard 
          title="CRYPTOGRAPHICALLY BOUND"
          description="Groth16 proof + Poseidon commitment + request nonce."
        />
        <FeatureCard 
          title="DETERMINISTIC SAFETY"
          description="AI cannot execute arbitrary cryptography or declare verification."
        />
      </motion.div>
      
    </div>
  )
}

function FlowNode({ icon, label, delay, color = "border-slate-700 bg-black text-slate-300" }: { icon: React.ReactNode, label: string, delay: number, color?: string }) {
  return (
    <motion.div 
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ delay, type: "spring", stiffness: 200, damping: 15 }}
      className={`flex items-center gap-3 px-5 py-3 rounded-full border-2 ${color} z-10 transform hover:scale-105 transition-transform cursor-default`}
    >
      {icon}
      <span className="text-sm font-bold tracking-widest">{label}</span>
    </motion.div>
  )
}

function FeatureCard({ title, description }: { title: string, description: string }) {
  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 text-left hover:-translate-y-1 transition-transform duration-300 hover:border-slate-700">
      <h3 className="text-sm tracking-widest font-bold text-white mb-3">{title}</h3>
      <p className="text-slate-400 text-sm leading-relaxed">{description}</p>
    </div>
  )
}
