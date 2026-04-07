#!/bin/bash
# Reference solution — photography portfolio with Unsplash images
cd /project

# Patch next.config.mjs to allow Unsplash remote images
cat > next.config.mjs << 'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "images.unsplash.com" },
    ],
  },
};
export default nextConfig;
EOF

cat > app/page.tsx << 'EOF'
import Image from "next/image";

const projects = [
  { id: 1, title: "Golden Hour", src: "https://images.unsplash.com/photo-1504198266287-1659872e6590?w=800" },
  { id: 2, title: "Urban Portrait", src: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=800" },
  { id: 3, title: "Wilderness", src: "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800" },
  { id: 4, title: "City Lights", src: "https://images.unsplash.com/photo-1519501025264-65ba15a82390?w=800" },
  { id: 5, title: "Ocean Breeze", src: "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800" },
  { id: 6, title: "Desert Bloom", src: "https://images.unsplash.com/photo-1509316785289-025f5b846b35?w=800" },
  { id: 7, title: "Winter Tale", src: "https://images.unsplash.com/photo-1483728642387-6c3bdd6c93e5?w=800" },
  { id: 8, title: "Studio Light", src: "https://images.unsplash.com/photo-1554080353-a576cf803bda?w=800" },
  { id: 9, title: "Quiet Moments", src: "https://images.unsplash.com/photo-1502082553048-f009c37129b9?w=800" },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-neutral-950 text-white">
      <section className="max-w-6xl mx-auto px-6 py-24 text-center">
        <h1 className="text-6xl font-bold mb-4">Maya Chen</h1>
        <p className="text-xl text-neutral-400">Photography portfolio</p>
      </section>
      <section className="max-w-7xl mx-auto px-6 pb-24">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {projects.map((p) => (
            <div key={p.id} className="group relative overflow-hidden rounded-lg aspect-square">
              <Image src={p.src} alt={p.title} fill className="object-cover transition-transform group-hover:scale-105" />
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/60 transition-colors flex items-center justify-center">
                <span className="text-white opacity-0 group-hover:opacity-100 font-bold text-xl">{p.title}</span>
              </div>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
EOF

mkdir -p app/about app/contact
cat > app/about/page.tsx << 'EOF'
export default function About() {
  return (
    <main className="min-h-screen bg-neutral-950 text-white py-24 px-6">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-5xl font-bold mb-8">About Maya</h1>
        <p className="text-neutral-300">Maya Chen is a photographer based in Brooklyn.</p>
      </div>
    </main>
  );
}
EOF

cat > app/contact/page.tsx << 'EOF'
export default function Contact() {
  return (
    <main className="min-h-screen bg-neutral-950 text-white py-24 px-6">
      <div className="max-w-xl mx-auto">
        <h1 className="text-5xl font-bold mb-8">Contact</h1>
        <p className="text-neutral-300">hello@mayachen.com</p>
      </div>
    </main>
  );
}
EOF

npm run build
