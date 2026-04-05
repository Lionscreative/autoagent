#!/bin/bash
cd /project
# Minimal reference solution
cat > app/page.tsx << 'EOF'
import Link from "next/link";
export default function Home() {
  return (
    <main className="min-h-screen bg-amber-50 text-gray-900">
      <section className="flex flex-col items-center justify-center min-h-[50vh] bg-red-900 text-white px-4">
        <h1 className="text-5xl font-bold mb-2">La Dolce Vita</h1>
        <p className="text-xl">Authentic Italian cuisine in the heart of Paris</p>
        <Link href="/menu" className="mt-8 px-8 py-3 bg-amber-400 text-black font-bold rounded-lg">Reserve a Table</Link>
      </section>
      <section className="max-w-2xl mx-auto py-12 px-4 text-center">
        <h2 className="text-2xl font-bold mb-4">Hours</h2>
        <p>Tue-Sun: 12:00-14:30 &amp; 19:00-23:00</p>
        <p>Closed Monday</p>
        <p className="mt-4">42 Rue de Rivoli, 75004 Paris</p>
      </section>
    </main>
  );
}
EOF
mkdir -p app/menu
cat > app/menu/page.tsx << 'EOF'
export default function Menu() {
  return (
    <main className="min-h-screen bg-amber-50 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-4xl font-bold mb-8 text-center">Menu</h1>
        <h2 className="text-2xl font-bold text-red-800 mb-4">Antipasti</h2>
        <div className="mb-2 flex justify-between"><span>Bruschetta</span><span>8€</span></div>
        <div className="mb-6 flex justify-between"><span>Carpaccio</span><span>14€</span></div>
        <h2 className="text-2xl font-bold text-red-800 mb-4">Pasta</h2>
        <div className="mb-2 flex justify-between"><span>Carbonara</span><span>16€</span></div>
        <div className="mb-6 flex justify-between"><span>Truffle Tagliatelle</span><span>22€</span></div>
        <h2 className="text-2xl font-bold text-red-800 mb-4">Desserts</h2>
        <div className="mb-2 flex justify-between"><span>Tiramisu</span><span>9€</span></div>
        <div className="mb-6 flex justify-between"><span>Panna Cotta</span><span>8€</span></div>
      </div>
    </main>
  );
}
EOF
npm run build
