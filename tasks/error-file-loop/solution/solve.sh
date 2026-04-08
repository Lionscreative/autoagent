#!/bin/bash
cd /project
mkdir -p components
cat > components/Hero.tsx << 'EOF'
export default function Hero() {
  return (
    <section className="bg-blue-950 text-yellow-400 py-24 text-center">
      <h1 className="text-6xl font-bold">Bella Italia</h1>
      <p className="subtitle mt-4 text-xl text-yellow-200">Authentic flavors from the heart of Italy</p>
    </section>
  );
}
EOF
cat > components/Menu.tsx << 'EOF'
export default function Menu() {
  const dishes = ["Pasta Carbonara", "Margherita Pizza", "Risotto ai Funghi", "Tiramisu", "Bruschetta", "Lasagna"];
  return (
    <section className="bg-blue-900 text-yellow-300 py-16 px-4">
      <h2 className="text-4xl font-bold text-center mb-8">Menu</h2>
      <ul className="max-w-xl mx-auto space-y-2">{dishes.map(d => <li key={d}>{d}</li>)}</ul>
    </section>
  );
}
EOF
cat > components/About.tsx << 'EOF'
export default function About() {
  return <section className="bg-blue-950 text-yellow-200 py-16 px-4 text-center"><h2 className="text-4xl font-bold">About Bella Italia</h2><p>Family-owned since 1952</p></section>;
}
EOF
cat > components/Contact.tsx << 'EOF'
export default function Contact() {
  return <section className="bg-blue-900 text-yellow-300 py-16 px-4 text-center"><h2 className="text-4xl font-bold">Contact</h2><p>hello@bellaitalia.com</p></section>;
}
EOF
cat > app/page.tsx << 'EOF'
import Hero from "@/components/Hero";
import Menu from "@/components/Menu";
import About from "@/components/About";
import Contact from "@/components/Contact";
export default function Home() {
  return (
    <main>
      <nav className="bg-blue-950 text-yellow-400 p-4 flex gap-6 justify-center">
        <a href="#hero">Home</a><a href="#menu">Menu</a><a href="#about">About</a><a href="#contact">Contact</a>
      </nav>
      <Hero /><Menu /><About /><Contact />
    </main>
  );
}
EOF
npm run build
