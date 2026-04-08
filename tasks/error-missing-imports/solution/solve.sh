#!/bin/bash
cd /project
# Reference solution — plain Tailwind badges (no broken imports)
cat > app/page.tsx << 'EOF'
export default function Home() {
  const tiers = [
    { name: "Starter", price: "$9", badge: null, features: ["1 project", "Basic support"] },
    { name: "Pro", price: "$29", badge: "Most Popular", features: ["10 projects", "Priority support", "Analytics"] },
    { name: "Enterprise", price: "$99", badge: "Best Value", features: ["Unlimited", "SLA", "Dedicated manager"] },
  ];
  return (
    <main className="min-h-screen bg-gray-50 py-16 px-4">
      <h1 className="text-4xl font-bold text-center mb-12">Pricing</h1>
      <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
        {tiers.map(t => (
          <div key={t.name} className="bg-white rounded-xl p-8 shadow">
            {t.badge && <span className="inline-block px-3 py-1 text-xs font-semibold bg-blue-100 text-blue-800 rounded-full mb-4">{t.badge}</span>}
            <h2 className="text-2xl font-bold">{t.name}</h2>
            <p className="text-4xl font-bold my-4">{t.price}<span className="text-base font-normal">/mo</span></p>
            <ul className="mb-6 space-y-2">{t.features.map(f => <li key={f}>✓ {f}</li>)}</ul>
            <button className="w-full py-3 bg-blue-600 text-white rounded-lg font-semibold">Get Started</button>
          </div>
        ))}
      </div>
    </main>
  );
}
EOF
npm run build
