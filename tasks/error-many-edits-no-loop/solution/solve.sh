#!/bin/bash
cd /project
cat > app/page.tsx << 'EOF'
export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 flex">
      <aside className="sidebar w-64 bg-slate-900 text-white p-6 hidden md:block">
        <h2 className="text-xl font-bold mb-6">Dashboard</h2>
        <nav className="space-y-2"><a href="#stats">Stats</a><br/><a href="#activity">Activity</a><br/><a href="#chart">Chart</a><br/><a href="#actions">Actions</a></nav>
      </aside>
      <div className="flex-1 p-4 md:p-8 space-y-8">
        <section id="stats" className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {["Users", "Revenue", "Orders"].map(s => (
            <div key={s} className="bg-white p-6 rounded-xl shadow hover:shadow-lg transition">
              <svg className="icon w-6 h-6 text-blue-600" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="10"/></svg>
              <p className="text-sm text-gray-500">{s}</p>
              <p className="text-3xl font-bold">1,234</p>
            </div>
          ))}
        </section>
        <section id="activity" className="bg-white p-6 rounded-xl shadow">
          <h3 className="font-bold mb-4">Recent activity</h3>
          <ul className="space-y-2"><li>User signed up</li><li>Order placed</li><li>Payment received</li></ul>
        </section>
        <section id="chart" className="bg-white p-6 rounded-xl shadow h-64 flex items-center justify-center">
          <p className="text-gray-400">Chart placeholder</p>
        </section>
        <section id="actions" className="bg-white p-6 rounded-xl shadow">
          <h3 className="font-bold mb-4">Quick actions</h3>
          <div className="flex gap-2 flex-wrap"><button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">New</button><button className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300">Export</button></div>
        </section>
      </div>
    </main>
  );
}
EOF
npm run build
