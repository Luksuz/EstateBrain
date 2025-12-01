"use client";

import Link from "next/link";

const faqs = [
  {
    question: "How do I scrape new listings?",
    answer: "Go to the Scraper page in the admin section. You can either paste a search page URL to automatically extract all listing URLs, or paste individual listing URLs directly. The system will deduplicate and process them in the background."
  },
  {
    question: "What is the AI room analysis?",
    answer: "Our AI analyzes images from each listing to identify different rooms (bedrooms, bathrooms, kitchen, etc.) and assess their condition. Click the info icon on any room to see the AI's reasoning."
  },
  {
    question: "Why are some listings skipped?",
    answer: "By default, the system skips URLs that have already been scraped to avoid duplicates. You can enable 'Re-scrape existing' when creating a job to force re-processing of existing listings."
  },
  {
    question: "What do the condition badges mean?",
    answer: "Condition badges indicate the state of a room: NEW (brand new), EXCELLENT (like new), GOOD (well maintained), FAIR (some wear), NEEDS_WORK (requires renovation), or ROH_BAU (unfinished construction)."
  },
  {
    question: "How accurate is the price per m² calculation?",
    answer: "The price per m² is calculated using the living area from the listing. If there's an area conflict (metadata and description differ), a warning badge is shown."
  },
];

const shortcuts = [
  { keys: ["G", "D"], description: "Go to Dashboard" },
  { keys: ["G", "L"], description: "Go to Listings" },
  { keys: ["G", "S"], description: "Go to Scraper" },
  { keys: ["G", "A"], description: "Go to Analytics" },
  { keys: ["/"], description: "Focus search" },
  { keys: ["?"], description: "Show help" },
];

export default function HelpPage() {
  return (
    <div className="relative p-4 lg:p-8 max-w-4xl">
      {/* Header */}
      <header className="mb-8 animate-fade-in">
        <h1 className="text-3xl lg:text-4xl font-bold text-white mb-2">
          Help & Support
        </h1>
        <p className="text-slate-400">
          Learn how to use Real Estater effectively
        </p>
      </header>

      {/* Quick Start */}
      <section className="glass rounded-2xl p-6 mb-6 animate-fade-in stagger-1" style={{ opacity: 0 }}>
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 border border-emerald-500/20 flex items-center justify-center">
            <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Quick Start</h2>
            <p className="text-sm text-slate-500">Get up and running in minutes</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex gap-4">
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-sm font-medium text-emerald-400 flex-shrink-0">
              1
            </div>
            <div>
              <h3 className="font-medium text-white mb-1">Navigate to Scraper</h3>
              <p className="text-sm text-slate-400">
                Click on "Scraper" in the sidebar to access the admin scraping controls.
              </p>
            </div>
          </div>
          
          <div className="flex gap-4">
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-sm font-medium text-emerald-400 flex-shrink-0">
              2
            </div>
            <div>
              <h3 className="font-medium text-white mb-1">Add Listing URLs</h3>
              <p className="text-sm text-slate-400">
                Paste a njuskalo.hr search page URL or individual listing URLs. The system will extract and process them.
              </p>
            </div>
          </div>
          
          <div className="flex gap-4">
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-sm font-medium text-emerald-400 flex-shrink-0">
              3
            </div>
            <div>
              <h3 className="font-medium text-white mb-1">Wait for Processing</h3>
              <p className="text-sm text-slate-400">
                Jobs run in the background. You can close the page and return later—progress is tracked automatically.
              </p>
            </div>
          </div>
          
          <div className="flex gap-4">
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-sm font-medium text-emerald-400 flex-shrink-0">
              4
            </div>
            <div>
              <h3 className="font-medium text-white mb-1">Browse Listings</h3>
              <p className="text-sm text-slate-400">
                View your scraped listings on the Dashboard or Listings page. Use filters to find specific properties.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* FAQs */}
      <section className="glass rounded-2xl p-6 mb-6 animate-fade-in stagger-2" style={{ opacity: 0 }}>
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500/20 to-purple-500/20 border border-violet-500/20 flex items-center justify-center">
            <svg className="w-5 h-5 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Frequently Asked Questions</h2>
            <p className="text-sm text-slate-500">Common questions and answers</p>
          </div>
        </div>

        <div className="space-y-4">
          {faqs.map((faq, i) => (
            <details key={i} className="group">
              <summary className="flex items-center justify-between p-4 bg-slate-800/30 rounded-xl cursor-pointer hover:bg-slate-800/50 transition-colors">
                <span className="font-medium text-white">{faq.question}</span>
                <svg className="w-5 h-5 text-slate-400 group-open:rotate-180 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </summary>
              <div className="px-4 pb-4 pt-2 text-sm text-slate-400">
                {faq.answer}
              </div>
            </details>
          ))}
        </div>
      </section>

      {/* Contact */}
      <section className="glass rounded-2xl p-6 animate-fade-in stagger-3" style={{ opacity: 0 }}>
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/20 flex items-center justify-center">
            <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Need More Help?</h2>
            <p className="text-sm text-slate-500">We're here to assist you</p>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <a 
            href="https://github.com" 
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-4 p-4 bg-slate-800/30 rounded-xl hover:bg-slate-800/50 transition-colors"
          >
            <div className="w-12 h-12 rounded-xl bg-slate-700/50 flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.604-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.464-1.11-1.464-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-white">GitHub Repository</p>
              <p className="text-sm text-slate-400">View source code & report issues</p>
            </div>
          </a>
          
          <a 
            href="mailto:support@realestater.com"
            className="flex items-center gap-4 p-4 bg-slate-800/30 rounded-xl hover:bg-slate-800/50 transition-colors"
          >
            <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center">
              <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-white">Email Support</p>
              <p className="text-sm text-slate-400">Get help via email</p>
            </div>
          </a>
        </div>
      </section>

      {/* Version Info */}
      <div className="mt-8 text-center text-sm text-slate-500 animate-fade-in stagger-4" style={{ opacity: 0 }}>
        <p>Real Estater v1.0.0 · Built with Next.js + FastAPI</p>
      </div>
    </div>
  );
}

