import React from 'react'
import { Link } from 'react-router-dom'
import { TrendingUp, Newspaper, Brain, LineChart } from 'lucide-react'

function HomePage({ stats }) {
  return (
    <div className="max-w-6xl mx-auto">
      {/* Hero Section */}
      <div className="text-center mb-16">
        <h1 className="font-fugaz text-6xl text-white mb-4 drop-shadow-lg">
          Linked Intelligent Analyst
        </h1>
        <p className="text-xl text-white/90 mb-8 max-w-2xl mx-auto">
          Dove notizie e mercati si incontrano. Un sistema AI che analizza eventi geopolitici 
          e li collega ai movimenti dei mercati finanziari.
        </p>
        <Link 
          to="/analysis"
          className="inline-block bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-bold px-8 py-4 rounded-lg text-lg transition transform hover:scale-105 shadow-xl"
        >
          Inizia Analisi →
        </Link>
      </div>

      {/* Features Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
        <FeatureCard 
          icon={<Newspaper size={40} />}
          title="Notizie Real-Time"
          description="RSS feeds e ricerca intelligente eventi storici"
        />
        <FeatureCard 
          icon={<LineChart size={40} />}
          title="Dati Mercato"
          description="5 indici principali con OHLCV e indicatori"
        />
        <FeatureCard 
          icon={<Brain size={40} />}
          title="AI Analysis"
          description="GPT-3.5 per nessi semantica-numerico"
        />
        <FeatureCard 
          icon={<TrendingUp size={40} />}
          title="Previsioni"
          description="Pattern storici e similarity analysis"
        />
      </div>

      {/* Quick Stats */}
      {stats && (
        <div className="bg-white/10 backdrop-blur-md rounded-xl p-8 border border-white/20">
          <h2 className="text-2xl font-bold text-white mb-6">Statistiche Sistema</h2>
          <div className="grid md:grid-cols-3 gap-6">
            <StatCard label="Articoli Totali" value={stats.total_articles} />
            <StatCard label="Date Analizzate" value={stats.total_dates} />
            <StatCard label="Analisi Complete" value={stats.analyzed_articles} />
          </div>
        </div>
      )}

      {/* About Section */}
      <div className="mt-12 bg-white/10 backdrop-blur-md rounded-xl p-8 border border-white/20">
        <h2 className="text-2xl font-bold text-white mb-4">Come Funziona</h2>
        <div className="text-white/90 space-y-4">
          <Step number="1" text="Inserisci una data di interesse (YYYY-MM-DD)" />
          <Step number="2" text="Il sistema cerca notizie da feed RSS o via GPT" />
          <Step number="3" text="Scarica dati di mercato per 5 indici principali" />
          <Step number="4" text="Calcola 14 indicatori tecnici (ATR, volatility, momentum, ecc.)" />
          <Step number="5" text="Analizza i nessi tra eventi e movimenti di mercato" />
          <Step number="6" text="Genera previsioni basate su pattern storici simili" />
        </div>
      </div>
    </div>
  )
}

function FeatureCard({ icon, title, description }) {
  return (
    <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20 card-hover text-center">
      <div className="text-yellow-300 mb-4 flex justify-center">{icon}</div>
      <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
      <p className="text-white/80 text-sm">{description}</p>
    </div>
  )
}

function StatCard({ label, value }) {
  return (
    <div className="text-center">
      <div className="text-4xl font-bold text-yellow-300 mb-2">{value}</div>
      <div className="text-white/80">{label}</div>
    </div>
  )
}

function Step({ number, text }) {
  return (
    <div className="flex items-start gap-4">
      <div className="bg-yellow-400 text-gray-900 rounded-full w-8 h-8 flex items-center justify-center font-bold flex-shrink-0">
        {number}
      </div>
      <p className="pt-1">{text}</p>
    </div>
  )
}

export default HomePage
