#!/bin/bash
# Reference solution for the portfolio task
cd /project

# Create homepage
cat > app/page.tsx << 'EOF'
export default function Home() {
  return (
    <main className="min-h-screen bg-gray-950 text-white">
      <section className="flex flex-col items-center justify-center min-h-[60vh] px-4">
        <h1 className="text-5xl font-bold mb-4">Sarah Chen</h1>
        <p className="text-xl text-amber-400">Capturing moments that matter</p>
      </section>
      <section className="max-w-6xl mx-auto px-4 py-16">
        <h2 className="text-3xl font-bold mb-8 text-center">Gallery</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[1,2,3,4,5,6].map(i => (
            <div key={i} className="aspect-square bg-gray-800 rounded-lg" />
          ))}
        </div>
      </section>
      <section className="max-w-3xl mx-auto px-4 py-16 text-center">
        <h2 className="text-3xl font-bold mb-4">About</h2>
        <p className="text-gray-300">Professional photographer specializing in capturing life&apos;s beautiful moments.</p>
      </section>
    </main>
  );
}
EOF

# Create about page
mkdir -p app/about
cat > app/about/page.tsx << 'EOF'
export default function About() {
  return (
    <main className="min-h-screen bg-gray-950 text-white py-16 px-4">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-4xl font-bold mb-8">About Sarah</h1>
        <p className="text-gray-300 mb-8">With over 10 years of experience, Sarah Chen captures the essence of every moment.</p>
        <h2 className="text-2xl font-bold mb-4 text-amber-400">Services</h2>
        <ul className="space-y-2 text-gray-300">
          <li>Wedding Photography</li>
          <li>Portrait Sessions</li>
          <li>Event Coverage</li>
          <li>Product Photography</li>
        </ul>
        <p className="mt-8 text-gray-400">Contact: sarah@example.com</p>
      </div>
    </main>
  );
}
EOF

# Create contact page
mkdir -p app/contact
cat > app/contact/page.tsx << 'EOF'
export default function Contact() {
  return (
    <main className="min-h-screen bg-gray-950 text-white py-16 px-4">
      <div className="max-w-xl mx-auto">
        <h1 className="text-4xl font-bold mb-8">Contact</h1>
        <form className="space-y-4">
          <input type="text" placeholder="Name" className="w-full p-3 bg-gray-800 rounded-lg border border-gray-700" />
          <input type="email" placeholder="Email" className="w-full p-3 bg-gray-800 rounded-lg border border-gray-700" />
          <textarea placeholder="Message" rows={5} className="w-full p-3 bg-gray-800 rounded-lg border border-gray-700" />
          <button type="submit" className="w-full p-3 bg-amber-500 text-black font-bold rounded-lg">Send Message</button>
        </form>
      </div>
    </main>
  );
}
EOF

npm run build
