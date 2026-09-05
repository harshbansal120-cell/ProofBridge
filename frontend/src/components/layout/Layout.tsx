import { Outlet } from "react-router-dom"
import { Navbar } from "./Navbar"

export function Layout() {
  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden">
      <div className="ambient-glow" />
      <Navbar />
      <main className="flex-1 flex flex-col container mx-auto px-4 py-8 z-10">
        <Outlet />
      </main>
    </div>
  )
}
