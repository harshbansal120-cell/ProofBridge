import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Shield, Sparkles, Box, CheckCircle } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

export function Dashboard() {
  const navigate = useNavigate()
  // In a real app we'd fetch these from the backend
  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Processor Dashboard</h1>
          <p className="text-muted-foreground mt-1">Review verified claims and cryptographic proofs.</p>
        </div>
        <Button onClick={() => navigate('/new')}>New Verification Request</Button>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Placeholder entry */}
        <Card className="hover:border-primary/50 transition-colors cursor-pointer" onClick={() => navigate('/processor/VR-demo')}>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <Badge variant="success">PROOF_VALID</Badge>
              <span className="text-xs text-muted-foreground">Just now</span>
            </div>
            <CardTitle className="text-xl mt-4">Merchant Volume Check</CardTitle>
            <CardDescription>Demo Merchant Pvt Ltd</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="bg-white/5 rounded-md p-3 font-mono text-sm border border-white/10 mb-4">
              SUM(transactions.amount) &gt; 10,00,000 INR
            </div>
            <div className="flex items-center text-sm text-emerald-400">
              <Shield className="h-4 w-4 mr-2" />
              Verified via ZERO_KNOWLEDGE
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
