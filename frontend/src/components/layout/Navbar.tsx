import { Link, useLocation } from "react-router-dom"
import { Shield } from "lucide-react"
import { motion } from "framer-motion"

export function Navbar() {
  const location = useLocation()
  
  return (
    <nav className="sticky top-0 z-50 w-full border-b border-white/5 bg-background/60 backdrop-blur-xl supports-[backdrop-filter]:bg-background/40 transition-all duration-300">
      <div className="container mx-auto flex h-16 items-center px-4 md:px-8">
        <Link to="/" className="flex items-center space-x-3 mr-auto group">
          <Shield className="h-7 w-7 text-blue-500 group-hover:text-blue-400 transition-colors" />
          <div className="flex flex-col">
            <span className="font-bold text-lg leading-tight tracking-wide text-white group-hover:text-gray-200 transition-colors">ProofBridge</span>
            <span className="text-[10px] tracking-[0.2em] font-medium text-slate-400 uppercase">Evidence Firewall</span>
          </div>
        </Link>
        <div className="flex items-center space-x-6">
          <div className="hidden md:flex items-center mr-4 space-x-2 bg-white/5 border border-white/10 rounded-full px-3 py-1">
             <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
             <span className="text-[11px] font-mono tracking-wider text-slate-300 uppercase">System Ready</span>
          </div>
          <Link 
            to="/new" 
            className={`relative text-sm font-medium transition-colors hover:text-white pb-1 ${location.pathname === '/new' ? 'text-white' : 'text-slate-400'}`}
          >
            New Verification
            {location.pathname === '/new' && (
              <motion.div layoutId="nav-indicator" className="absolute bottom-0 left-0 w-full h-[2px] bg-blue-500 rounded-full" />
            )}
          </Link>
          <Link 
            to="/dash" 
            className={`relative text-sm font-medium transition-colors hover:text-white pb-1 ${location.pathname === '/dash' || location.pathname.startsWith('/processor') ? 'text-white' : 'text-slate-400'}`}
          >
            Processor Console
            {(location.pathname === '/dash' || location.pathname.startsWith('/processor')) && (
              <motion.div layoutId="nav-indicator" className="absolute bottom-0 left-0 w-full h-[2px] bg-blue-500 rounded-full" />
            )}
          </Link>
        </div>
      </div>
    </nav>
  )
}
