import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Bot, LineChart, Users, Shield, ChevronRight, Activity, Cpu } from 'lucide-react';
import ParticleSwarm from './ParticleSwarm';

const FadeIn = ({ children, delay = 0, className = "" }: { children: React.ReactNode, delay?: number, className?: string }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true, margin: "-50px" }}
    transition={{ duration: 0.6, delay }}
    className={className}
  >
    {children}
  </motion.div>
);

const GlassCard = ({ children, className = "" }: { children: React.ReactNode, className?: string }) => (
  <div className={`glass-card rounded-2xl p-6 relative overflow-hidden group hover:border-cyan-500/30 transition-colors duration-500 ${className}`}>
    <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
    <div className="relative z-10">{children}</div>
  </div>
);

export default function App() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className="min-h-screen relative font-sans selection:bg-cyan-500/30">
      {/* Background Elements */}
      <div className="fixed inset-0 z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-600/20 blur-[120px] rounded-full mix-blend-screen" />
        <div className="absolute top-[20%] right-[-10%] w-[30%] h-[50%] bg-cyan-600/20 blur-[120px] rounded-full mix-blend-screen" />
        <div className="absolute bottom-[-10%] left-[20%] w-[50%] h-[40%] bg-blue-600/20 blur-[120px] rounded-full mix-blend-screen" />
        <div className="absolute inset-0 bg-[#020617]/80 z-0" />
      </div>

      <ParticleSwarm />

      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass-card rounded-none border-x-0 border-t-0 border-b-white/10 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center space-x-2 cursor-pointer">
            <Bot className="w-8 h-8 text-cyan-400" />
            <span className="font-serif text-3xl tracking-wide text-white">未来 Mirai</span>
          </div>
          <div className="hidden md:flex space-x-8 text-sm font-medium text-slate-300">
            <a href="#features" className="hover:text-cyan-400 transition-colors">Features</a>
            <a href="#pipeline" className="hover:text-cyan-400 transition-colors">The Engine</a>
            <a href="#stats" className="hover:text-cyan-400 transition-colors">Validation</a>
          </div>
          <button className="px-6 py-2.5 rounded-full bg-cyan-500/10 border border-cyan-500/50 text-cyan-400 font-medium hover:bg-cyan-500 hover:text-white transition-all duration-300 shadow-[0_0_20px_rgba(6,182,212,0.3)]">
            Launch Dashboard
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <main className="relative z-10 pt-32 pb-20">
        
        {/* Hero Section */}
        <section className="min-h-[85vh] flex items-center max-w-7xl mx-auto px-6 pt-10">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div className="space-y-8">
              <motion.div
                initial={{ opacity: 0, x: -30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.8 }}
              >
                <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full glass-card border-cyan-500/30 mb-6">
                  <span className="flex h-2 w-2 rounded-full bg-cyan-500 animate-pulse"></span>
                  <span className="text-xs font-medium text-cyan-400 uppercase tracking-wider">v0.9.0 Multi-Model Engine</span>
                </div>
                <h1 className="text-6xl md:text-7xl font-serif text-white leading-tight">
                  Predict Startup Success with <span className="text-gradient">10-Model Precision</span>
                </h1>
                <p className="mt-6 text-xl text-slate-400 leading-relaxed max-w-xl font-light">
                  PitchBook-quality due diligence reports powered by an 88.5B+ persona swarm, 
                  10-model council deliberation, and real-time market simulation.
                </p>
              </motion.div>
              
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.2 }}
                className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4"
              >
                <button className="px-8 py-4 rounded-xl bg-gradient-to-r from-cyan-500 to-purple-600 text-white font-medium hover:shadow-[0_0_30px_rgba(6,182,212,0.5)] transition-all flex items-center justify-center space-x-2 group">
                  <span>View Sample Report</span>
                  <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </button>
                <button className="px-8 py-4 rounded-xl glass-card text-white font-medium hover:bg-white/5 transition-all flex items-center justify-center">
                  View Architecture
                </button>
              </motion.div>
            </div>

            {/* Hero Visual */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1, delay: 0.3 }}
              className="relative lg:h-[600px] flex items-center justify-center"
            >
              <GlassCard className="w-full max-w-md backdrop-blur-2xl border-white/20 shadow-2xl shadow-cyan-900/20 transform rotate-[-2deg] hover:rotate-0 transition-transform duration-700">
                <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-4">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-400 to-purple-500 flex items-center justify-center">
                      <LineChart className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h3 className="font-medium text-white">Quantum Metrics</h3>
                      <p className="text-xs text-slate-400">Series A · B2B SaaS</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-serif text-cyan-400">8.4</div>
                    <div className="text-xs text-cyan-500/80">Strong Hit</div>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-400">Market Traction</span>
                      <span className="text-white">9.2</span>
                    </div>
                    <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-cyan-400 w-[92%]" />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-400">Defensibility</span>
                      <span className="text-white">7.8</span>
                    </div>
                    <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-purple-400 w-[78%]" />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-400">Team Execution</span>
                      <span className="text-white">8.5</span>
                    </div>
                    <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-400 w-[85%]" />
                    </div>
                  </div>
                </div>

                <div className="mt-6 p-4 rounded-xl bg-white/5 border border-white/5">
                  <p className="text-sm text-slate-300 italic font-serif">
                    "The swarm highly converged on team execution. 10/10 market analysts predict massive upside."
                  </p>
                </div>
              </GlassCard>
            </motion.div>
          </div>
        </section>

        {/* Features Grid */}
        <section id="features" className="max-w-7xl mx-auto px-6 py-32">
          <FadeIn>
            <div className="text-center mb-16">
              <h2 className="text-4xl md:text-5xl font-serif text-white mb-4">The Tri-Core Prediction Engine</h2>
              <p className="text-slate-400 max-w-2xl mx-auto">Evaluating viability through council review, crowd simulation, and market forecasting.</p>
            </div>
          </FadeIn>

          <div className="grid md:grid-cols-3 gap-8">
            <FadeIn delay={0.1}>
              <GlassCard className="h-full">
                <div className="w-12 h-12 rounded-lg bg-cyan-500/10 flex items-center justify-center mb-6 border border-cyan-500/30">
                  <Cpu className="w-6 h-6 text-cyan-400" />
                </div>
                <h3 className="text-xl font-medium text-white mb-3">10-Model Council</h3>
                <p className="text-slate-400 text-sm leading-relaxed">
                  Karpathy-style peer review. 10 elite LLMs across 8 families score dimensions independently, cross-evaluate anonymously, and reconcile under a Chairman model.
                </p>
              </GlassCard>
            </FadeIn>
            <FadeIn delay={0.2}>
              <GlassCard className="h-full">
                <div className="w-12 h-12 rounded-lg bg-purple-500/10 flex items-center justify-center mb-6 border border-purple-500/30">
                  <Users className="w-6 h-6 text-purple-400" />
                </div>
                <h3 className="text-xl font-medium text-white mb-3">88.5B+ Persona Swarm</h3>
                <p className="text-slate-400 text-sm leading-relaxed">
                  50-100 unique persona agents generated from 16 trait dimensions evaluate from their perspective. The most bullish and bearish agents engage in simulated debate.
                </p>
              </GlassCard>
            </FadeIn>
            <FadeIn delay={0.3}>
              <GlassCard className="h-full">
                <div className="w-12 h-12 rounded-lg bg-blue-500/10 flex items-center justify-center mb-6 border border-blue-500/30">
                  <Activity className="w-6 h-6 text-blue-400" />
                </div>
                <h3 className="text-xl font-medium text-white mb-3">OASIS Simulation</h3>
                <p className="text-slate-400 text-sm leading-relaxed">
                  6-month multi-round market trajectory forecasting reacting to real news events. Watch how the startup survives against competitors and market shocks.
                </p>
              </GlassCard>
            </FadeIn>
          </div>
        </section>

        {/* Pipeline Section */}
        <section id="pipeline" className="py-32 relative">
          <div className="max-w-7xl mx-auto px-6">
            <FadeIn>
              <h2 className="text-4xl md:text-5xl font-serif text-white mb-16 text-center">The Assessment Pipeline</h2>
            </FadeIn>
            
            <div className="space-y-6 max-w-4xl mx-auto">
              {[
                { phase: '01', title: 'Deep Web Research', desc: 'OpenClaw agent conducts 10-step deep research across premium domains and live web sources.' },
                { phase: '02', title: 'Council Scoring', desc: '10 distinct models independently score 10 dimensions, with stage 2 peer reviews to check work.' },
                { phase: '03', title: 'Swarm Deliberation', desc: 'Contextually generated personas simulate the crowd reaction and argue divergent viewpoints.' },
                { phase: '04', title: 'Market Simulation', desc: 'The startup is subjected to a 6-month simulated timeline using live news events.' },
                { phase: '05', title: 'PitchBook-Quality Report', desc: 'An autonomous ReACT agent compiles findings, generates SVG charts, and builds a professional HTML/PDF report.' },
              ].map((step, idx) => (
                <FadeIn key={step.phase} delay={idx * 0.1}>
                  <GlassCard className="flex items-start md:items-center space-x-6 p-6 md:p-8">
                    <div className="flex-shrink-0 text-3xl font-serif text-cyan-500/30 font-bold">{step.phase}</div>
                    <div>
                      <h4 className="text-xl font-medium text-white mb-2">{step.title}</h4>
                      <p className="text-slate-400 text-sm md:text-base">{step.desc}</p>
                    </div>
                  </GlassCard>
                </FadeIn>
              ))}
            </div>
          </div>
        </section>

        {/* Validation Stats */}
        <section id="stats" className="py-32">
          <div className="max-w-7xl mx-auto px-6">
            <GlassCard className="border-cyan-500/20 bg-cyan-900/10 p-12 text-center relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500 to-transparent opacity-50" />
              <FadeIn>
                <div className="flex justify-center mb-6">
                  <Shield className="w-16 h-16 text-cyan-400" />
                </div>
                <h2 className="text-5xl font-serif text-white mb-6">Empirically Validated</h2>
                <div className="grid md:grid-cols-3 gap-8 mt-12 border-t border-white/10 pt-12">
                  <div>
                    <div className="text-4xl font-serif text-cyan-400 mb-2">22,818</div>
                    <div className="text-slate-400 text-sm uppercase tracking-wider font-medium">Companies Backtested</div>
                  </div>
                  <div>
                    <div className="text-4xl font-serif text-purple-400 mb-2">1.6M+</div>
                    <div className="text-slate-400 text-sm uppercase tracking-wider font-medium">Persona Combinations</div>
                  </div>
                  <div>
                    <div className="text-4xl font-serif text-blue-400 mb-2">Zero</div>
                    <div className="text-slate-400 text-sm uppercase tracking-wider font-medium">Marginal Cost Swarm</div>
                  </div>
                </div>
              </FadeIn>
            </GlassCard>
          </div>
        </section>

      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/10 bg-[#020617]/80 backdrop-blur-xl pt-16 pb-8">
        <div className="max-w-7xl mx-auto px-6 text-center md:text-left flex flex-col md:flex-row justify-between items-center">
          <div className="mb-6 md:mb-0">
            <div className="flex items-center justify-center md:justify-start space-x-2 mb-2">
              <Bot className="w-6 h-6 text-cyan-400" />
              <span className="font-serif text-2xl text-white">未来 Mirai</span>
            </div>
            <p className="text-slate-500 text-sm">Created by Aditya Goyal | vclabs.org</p>
          </div>
          <div className="flex space-x-6 text-sm text-slate-400">
            <a href="#" className="hover:text-cyan-400 transition-colors">GitHub Repository</a>
            <a href="#" className="hover:text-cyan-400 transition-colors">Documentation</a>
            <a href="#" className="hover:text-cyan-400 transition-colors">License</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
