#!/bin/bash
cd /project
cat > app/page.tsx << 'EOF'
export default function Home() {
  return (
    <main className="min-h-screen bg-white text-gray-900">
      {/* Hero */}
      <section className="min-h-screen flex flex-col items-center justify-center px-4 bg-gradient-to-b from-indigo-50 to-white">
        <h1 className="text-4xl md:text-6xl font-bold text-center">Sync your files everywhere, instantly</h1>
        <p className="mt-4 text-lg md:text-xl text-gray-600 text-center max-w-2xl">CloudSync keeps your team&apos;s files in perfect harmony across all devices</p>
        <div className="mt-8 flex flex-col sm:flex-row gap-4">
          <button className="px-8 py-3 bg-indigo-600 text-white rounded-lg font-bold">Start Free Trial</button>
          <button className="px-8 py-3 border-2 border-indigo-600 text-indigo-600 rounded-lg font-bold">Watch Demo</button>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="p-6 rounded-xl bg-indigo-50">
            <h3 className="text-xl font-bold mb-2">Real-time Sync</h3>
            <p className="text-gray-600">Files update across devices in milliseconds.</p>
          </div>
          <div className="p-6 rounded-xl bg-indigo-50">
            <h3 className="text-xl font-bold mb-2">End-to-end Encryption</h3>
            <p className="text-gray-600">Your data is always secure.</p>
          </div>
          <div className="p-6 rounded-xl bg-indigo-50">
            <h3 className="text-xl font-bold mb-2">Team Collaboration</h3>
            <p className="text-gray-600">Share and edit files together seamlessly.</p>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-20 px-4 bg-gray-50">
        <h2 className="text-3xl font-bold text-center mb-12">Pricing</h2>
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="p-8 bg-white rounded-xl border">
            <h3 className="text-xl font-bold">Free</h3>
            <p className="text-3xl font-bold mt-4">$0<span className="text-lg text-gray-500">/mo</span></p>
            <ul className="mt-6 space-y-2 text-gray-600">
              <li>5GB storage</li><li>1 user</li>
            </ul>
          </div>
          <div className="p-8 bg-indigo-600 text-white rounded-xl border-2 border-indigo-600 relative">
            <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-amber-400 text-black text-sm font-bold px-3 py-1 rounded-full">Most Popular</span>
            <h3 className="text-xl font-bold">Pro</h3>
            <p className="text-3xl font-bold mt-4">$12<span className="text-lg opacity-75">/mo</span></p>
            <ul className="mt-6 space-y-2 opacity-90">
              <li>100GB storage</li><li>5 users</li><li>Priority support</li>
            </ul>
          </div>
          <div className="p-8 bg-white rounded-xl border">
            <h3 className="text-xl font-bold">Enterprise</h3>
            <p className="text-3xl font-bold mt-4">$49<span className="text-lg text-gray-500">/mo</span></p>
            <ul className="mt-6 space-y-2 text-gray-600">
              <li>Unlimited storage</li><li>Unlimited users</li><li>Dedicated support</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-4 border-t text-center text-gray-500">
        <p className="font-bold text-gray-900">CloudSync</p>
        <p className="mt-2">&copy; 2026 CloudSync. All rights reserved.</p>
        <div className="mt-2 flex justify-center gap-4">
          <a href="#">Privacy</a><a href="#">Terms</a><a href="#">Contact</a>
        </div>
      </footer>
    </main>
  );
}
EOF
npm run build
