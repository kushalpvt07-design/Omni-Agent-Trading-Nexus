import { Dashboard } from '@/components/Dashboard';
import { SwarmChat } from '@/components/SwarmChat';

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 p-8">
      <div className="max-w-6xl mx-auto">
        <header className="mb-8 pl-6">
          <h1 className="text-3xl font-bold tracking-tight text-slate-100">Omni-Agent Trading Nexus</h1>
          <p className="text-slate-400 mt-2">Live Swarm Consensus & Risk Analytics</p>
        </header>
        
        <Dashboard />
        
        <SwarmChat />
      </div>
    </main>
  );
}
