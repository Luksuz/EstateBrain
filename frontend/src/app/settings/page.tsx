"use client";

import { useState } from "react";

export default function SettingsPage() {
  const [apiUrl, setApiUrl] = useState("http://localhost:8000");
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    // In a real app, this would save to localStorage or backend
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="relative p-4 lg:p-8 max-w-4xl">
      {/* Header */}
      <header className="mb-8 animate-fade-in">
        <h1 className="text-3xl lg:text-4xl font-bold text-white mb-2">
          Settings
        </h1>
        <p className="text-slate-400">
          Configure your application preferences
        </p>
      </header>

      <div className="space-y-6">
        {/* Profile Section */}
        <section className="glass rounded-2xl p-6 animate-fade-in stagger-1" style={{ opacity: 0 }}>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500/20 to-purple-500/20 border border-violet-500/20 flex items-center justify-center">
              <svg className="w-5 h-5 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Profile</h2>
              <p className="text-sm text-slate-500">Your account information</p>
            </div>
          </div>

          <div className="flex items-center gap-6 mb-6">
            <div className="relative">
              <div className="w-20 h-20 bg-gradient-to-br from-violet-500 to-purple-600 rounded-2xl flex items-center justify-center text-white font-bold text-2xl shadow-lg shadow-violet-500/20">
                AD
              </div>
              <button className="absolute -bottom-2 -right-2 w-8 h-8 bg-slate-800 border border-slate-700 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-700 transition-all">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
              </button>
            </div>
            <div className="flex-1">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm text-slate-400 mb-1.5">Display Name</label>
                  <input
                    type="text"
                    defaultValue="Admin User"
                    className="input-field w-full"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1.5">Email</label>
                  <input
                    type="email"
                    defaultValue="admin@realestater.com"
                    className="input-field w-full"
                  />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* API Configuration */}
        <section className="glass rounded-2xl p-6 animate-fade-in stagger-2" style={{ opacity: 0 }}>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 border border-emerald-500/20 flex items-center justify-center">
              <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">API Configuration</h2>
              <p className="text-sm text-slate-500">Backend connection settings</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1.5">API Base URL</label>
              <input
                type="url"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                className="input-field w-full"
                placeholder="http://localhost:8000"
              />
              <p className="text-xs text-slate-500 mt-1.5">The base URL for your FastAPI backend</p>
            </div>

            <div className="flex items-center gap-3 p-4 bg-slate-800/30 rounded-xl border border-slate-700/30">
              <div className="w-3 h-3 bg-emerald-500 rounded-full animate-pulse-glow" />
              <span className="text-sm text-emerald-400">Connected to backend</span>
            </div>
          </div>
        </section>

        {/* Scraping Settings */}
        <section className="glass rounded-2xl p-6 animate-fade-in stagger-3" style={{ opacity: 0 }}>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-cyan-500/20 flex items-center justify-center">
              <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Scraping Settings</h2>
              <p className="text-sm text-slate-500">Configure scraper behavior</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-slate-800/30 rounded-xl">
              <div>
                <p className="text-sm font-medium text-white">Auto-skip existing listings</p>
                <p className="text-xs text-slate-500">Skip URLs that are already in the database</p>
              </div>
              <button className="relative w-12 h-6 bg-emerald-500 rounded-full transition-colors">
                <span className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full shadow-sm transition-transform" />
              </button>
            </div>

            <div className="flex items-center justify-between p-4 bg-slate-800/30 rounded-xl">
              <div>
                <p className="text-sm font-medium text-white">Enable image analysis</p>
                <p className="text-xs text-slate-500">Use AI to analyze room images</p>
              </div>
              <button className="relative w-12 h-6 bg-emerald-500 rounded-full transition-colors">
                <span className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full shadow-sm transition-transform" />
              </button>
            </div>

            <div>
              <label className="block text-sm text-slate-400 mb-1.5">Max concurrent requests</label>
              <select className="input-field w-full">
                <option value="3">3 (Conservative)</option>
                <option value="5" selected>5 (Balanced)</option>
                <option value="10">10 (Fast)</option>
              </select>
            </div>
          </div>
        </section>

        {/* Appearance */}
        <section className="glass rounded-2xl p-6 animate-fade-in stagger-4" style={{ opacity: 0 }}>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/20 flex items-center justify-center">
              <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Appearance</h2>
              <p className="text-sm text-slate-500">Customize the interface</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm text-slate-400 mb-3">Theme</label>
              <div className="grid grid-cols-3 gap-3">
                <button className="p-3 bg-slate-800/50 border-2 border-emerald-500 rounded-xl text-center transition-all">
                  <div className="w-8 h-8 mx-auto mb-2 bg-gradient-to-br from-slate-800 to-slate-900 rounded-lg border border-slate-700" />
                  <span className="text-xs text-white">Dark</span>
                </button>
                <button className="p-3 bg-slate-800/50 border border-slate-700 rounded-xl text-center opacity-50 cursor-not-allowed">
                  <div className="w-8 h-8 mx-auto mb-2 bg-gradient-to-br from-slate-100 to-white rounded-lg border border-slate-200" />
                  <span className="text-xs text-slate-400">Light</span>
                </button>
                <button className="p-3 bg-slate-800/50 border border-slate-700 rounded-xl text-center opacity-50 cursor-not-allowed">
                  <div className="w-8 h-8 mx-auto mb-2 bg-gradient-to-br from-slate-500 to-slate-700 rounded-lg border border-slate-600" />
                  <span className="text-xs text-slate-400">System</span>
                </button>
              </div>
              <p className="text-xs text-slate-500 mt-2">Light and system themes coming soon</p>
            </div>

            <div className="flex items-center justify-between p-4 bg-slate-800/30 rounded-xl">
              <div>
                <p className="text-sm font-medium text-white">Compact mode</p>
                <p className="text-xs text-slate-500">Show more listings per page</p>
              </div>
              <button className="relative w-12 h-6 bg-slate-700 rounded-full transition-colors">
                <span className="absolute left-1 top-1 w-4 h-4 bg-slate-400 rounded-full shadow-sm transition-transform" />
              </button>
            </div>
          </div>
        </section>

        {/* Save Button */}
        <div className="flex justify-end gap-3 animate-fade-in stagger-5" style={{ opacity: 0 }}>
          <button className="btn-secondary">Reset to defaults</button>
          <button onClick={handleSave} className="btn-primary flex items-center gap-2">
            {saved ? (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Saved!
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Save Changes
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

